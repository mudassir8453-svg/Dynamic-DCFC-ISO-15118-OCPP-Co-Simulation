import asyncio
import datetime
import json
import socket
import struct
import uuid
import websockets

# Server & Network Configuration
STEVE_WS_URL = "ws://localhost:8180/steve/websocket/CentralSystemService/FERN_DCFAST_CHARGER"
SIMULINK_IP = "127.0.0.1"
UDP_RECV_PORT = 5000        # Simulink -> Python
UDP_SEND_PORT_AUTH = 5001   # Python -> Simulink (Auth Flag: '1'/'0')
UDP_SEND_PORT_LIMIT = 5002  # Python -> Simulink (Binary Double: 8 bytes)

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind((SIMULINK_IP, UDP_RECV_PORT))
udp_sock.setblocking(False)

# State Latches & Default Powertrain Configuration
active_transaction_id = 1
boot_requested = False
auth_requested = False
transaction_active = False
current_grid_limit = 500.0  # Default unthrottled grid current limit

def get_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

async def send_grid_limit(limit_val):
    """Helper to pack and push the current limit double to Simulink over Port 5002"""
    global current_grid_limit
    current_grid_limit = float(limit_val)
    limit_bytes = struct.pack('<d', current_grid_limit)
    udp_sock.sendto(limit_bytes, (SIMULINK_IP, UDP_SEND_PORT_LIMIT))
    print(f"==> Transmitted Grid Current Limit to Simulink: {current_grid_limit}A")

async def handle_simulink_traffic(ws):
    global active_transaction_id, boot_requested, auth_requested, transaction_active
    loop = asyncio.get_running_loop()

    while True:
        try:
            data, _ = await loop.sock_recvfrom(udp_sock, 1024)
            
            cleaned_data = data.rstrip(b'\x00').strip()
            if not cleaned_data:
                await asyncio.sleep(0.01)
                continue
                
            msg_text = cleaned_data.decode("utf-8")
            if not msg_text or not msg_text[0].isdigit():
                await asyncio.sleep(0.01)
                continue
                
            tokens = msg_text.split(",")
            msg_type = int(tokens[0])

            # 1 = BootNotification
            if msg_type == 1:
                if not boot_requested:
                    call_msg = [
                        2, str(uuid.uuid4()), "BootNotification",
                        {"chargePointVendor": "FERN_Powertrain", "chargePointModel": "DCFast_800V"}
                    ]
                    await ws.send(json.dumps(call_msg))
                    print("-> [OCPP] Sent BootNotification")
                    boot_requested = True
                    
                    # Push default limit to Simulink right after boot connection
                    await send_grid_limit(current_grid_limit)

            # 2 = Authorize
            elif msg_type == 2:
                if not auth_requested:
                    tag_id = tokens[1] if len(tokens) > 1 else "UNKNOWN"
                    call_msg = [2, str(uuid.uuid4()), "Authorize", {"idTag": tag_id}]
                    await ws.send(json.dumps(call_msg))
                    print(f"-> [OCPP] Sent Authorize.req for {tag_id}")
                    auth_requested = True

            # 3 = StartTransaction
            elif msg_type == 3:
                if not transaction_active:
                    tag_id = tokens[1] if len(tokens) > 1 else "UNKNOWN"
                    meter_start = int(tokens[2]) if len(tokens) > 2 else 0
                    call_msg = [
                        2, str(uuid.uuid4()), "StartTransaction",
                        {"connectorId": 1, "idTag": tag_id, "meterStart": meter_start, "timestamp": get_timestamp()}
                    ]
                    await ws.send(json.dumps(call_msg))
                    print(f"-> [OCPP] Sent StartTransaction for {tag_id} (Start Meter: {meter_start} Wh)")
                    transaction_active = True

            # 4 = MeterValues (Live Telemetry stream)
            elif msg_type == 4:
                power_val = tokens[1] if len(tokens) > 1 else "0"
                call_msg = [
                    2, str(uuid.uuid4()), "MeterValues",
                    {
                        "connectorId": 1,
                        "transactionId": active_transaction_id,
                        "meterValue": [{
                            "timestamp": get_timestamp(),
                            "sampledValue": [{"value": power_val, "measurand": "Power.Active.Import", "unit": "W"}]
                        }]
                    }
                ]
                await ws.send(json.dumps(call_msg))

            # 5 = StopTransaction
            elif msg_type == 5:
                if transaction_active:
                    meter_stop = int(tokens[1]) if len(tokens) > 1 else 25000
                    call_msg = [
                        2, str(uuid.uuid4()), "StopTransaction",
                        {"transactionId": active_transaction_id, "meterStop": meter_stop, "timestamp": get_timestamp()}
                    ]
                    await ws.send(json.dumps(call_msg))
                    print(f"-> [OCPP] Sent StopTransaction (Stop Meter: {meter_stop} Wh)")
                    
                    transaction_active = False
                    auth_requested = False
                    
                    # Reset limit back to default on session close
                    await send_grid_limit(500.0)

        except BlockingIOError:
            pass
        except Exception:
            pass

        await asyncio.sleep(0.01)

async def handle_steve_responses(ws):
    global active_transaction_id
    while True:
        try:
            response_raw = await ws.recv()
            response = json.loads(response_raw)
            print(f"<- [SteVe] Received: {response}")

            if response[0] == 2:
                msg_id = response[1]
                action = response[2]
                payload = response[3]

                if action == "GetConfiguration":
                    conf_reply = [3, msg_id, {"configurationKey": [], "unknownKey": []}]
                    await ws.send(json.dumps(conf_reply))
                    print("-> [OCPP] Replied to GetConfiguration")
                
                elif action == "SetChargingProfile":
                    try:
                        limit = payload["csChargingProfiles"]["chargingSchedule"]["chargingSchedulePeriod"][0]["limit"]
                        print(f"==> Cloud Throttling Triggered! Overwriting Limit to: {limit}A")
                        
                        await send_grid_limit(limit)
                        await ws.send(json.dumps([3, msg_id, {"status": "Accepted"}]))
                    except (KeyError, IndexError, ValueError):
                        await ws.send(json.dumps([3, msg_id, {"status": "Rejected"}]))
                        print("==> Cloud Throttling REJECTED (Invalid Payload)")

                elif action == "ClearChargingProfile":
                    try:
                        print("==> ClearChargingProfile triggered! Resetting limit to default 500.0A")
                        await send_grid_limit(500.0)
                        await ws.send(json.dumps([3, msg_id, {"status": "Accepted"}]))
                    except Exception as e:
                        await ws.send(json.dumps([3, msg_id, {"status": "Unknown"}]))
                        print(f"==> ClearChargingProfile Error: {e}")

            elif response[0] == 3:
                payload = response[2]

                if "idTagInfo" in payload:
                    status = payload["idTagInfo"].get("status")
                    if status == "Accepted":
                        print("==> Authorization ACCEPTED! Unlocking Simulink...")
                        udp_sock.sendto(b"1", (SIMULINK_IP, UDP_SEND_PORT_AUTH))
                    else:
                        print(f"==> Authorization REJECTED ({status})!")
                        udp_sock.sendto(b"0", (SIMULINK_IP, UDP_SEND_PORT_AUTH))

                if "transactionId" in payload:
                    active_transaction_id = payload["transactionId"]
                    print(f"==> Transaction ID set to {active_transaction_id}")

        except websockets.ConnectionClosed:
            break
        except Exception as e:
            print(f"Error handling SteVe response: {e}")

async def main():
    print("Connecting to SteVe CSMS...")
    async with websockets.connect(STEVE_WS_URL, subprotocols=["ocpp1.6"]) as websocket:
        print(f"Connected to SteVe via WebSocket at {STEVE_WS_URL}")
        await asyncio.gather(handle_simulink_traffic(websocket), handle_steve_responses(websocket))

if __name__ == "__main__":
    asyncio.run(main())