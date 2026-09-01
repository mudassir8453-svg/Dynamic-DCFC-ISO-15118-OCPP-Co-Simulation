# OCPP-Integrated DC Fast Charger (800V Architecture)

## Overview
This project is a Software-in-the-Loop (SIL) simulation of an 800V DC Fast Charger for electric vehicles. It integrates a physical power electronics model with external cloud-based communication, demonstrating real-time dynamic power negotiation. The core powertrain is modeled in MATLAB/Simscape, while a custom Python bridge handles Open Charge Point Protocol (OCPP) communication with a local SteVe server via UDP.

This repository adapts a validated MathWorks baseline model, modifying the control architecture to support external telemetry and custom bounding logic.

## Core Features
*   **Software-in-the-Loop (SIL) Bridge:** A Python-based UDP server streams real-time state-of-charge (SOC) and current limits between the Simulink plant and an OCPP backend.
*   **Advanced Stateflow Control:** Custom C-syntax state machines handle CC-CV (Constant Current / Constant Voltage) charge tapering and dynamic power negotiation limits.
*   **Sub-Microsecond Resolution:** Optimized discrete solver configurations (`ode23t` at 1µs step size) to accurately resolve 10 kHz PWM switching without aliasing or quantization errors.

## Model Scope & Limitations
*   **Static Connection State:** The `PlugConnected` variable is implemented as a static dummy variable (set to `1`) to facilitate continuous SIL communication testing. It does not currently support dynamic plug-and-play connection sequences.
*   **Pre-Charge Bypassed:** Hardware-level pre-charge sequencing is not implemented. The model focuses on steady-state active charging behavior and communication loop stability rather than full physical startup transient mitigation.

## Tech Stack
*   **Power Electronics:** MATLAB, Simulink, Simscape Electrical
*   **Control Logic:** Stateflow (C-Action Language), PI Controllers
*   **Communications:** Python 3.x, UDP Sockets, Open Charge Point Protocol (OCPP)
*   **Backend:** SteVe (Spring Boot OCPP Server)

## Usage Instructions
1.  **Start the Backend:** Launch your SteVe OCPP server and ensure it is listening on the designated port.
2.  **Initialize the Bridge:** Run the Python UDP script to open the local socket.
    ```bash
    python ocpp_bridge.py
    ```
3.  **Load Parameters:** Open MATLAB and run the `params_all_evs.m` script to load the 10 kHz switching frequency, 800V bus targets, and PI gains into the workspace.
4.  **Run Simulation:** Open `DCFastCharger.slx` and start the simulation. The Python terminal will log the dynamic current limits being passed to the active Stateflow chart.

## Acknowledgements
The baseline electrical topology was adapted from the MathWorks "DC Fast Charger for Electric Vehicle" example. The control loops, Stateflow state machines, and Python OCPP integration were custom-engineered for this SIL implementation.
