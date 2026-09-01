% DC Fast Charger For Electric Vehicle Battery - Master Parameter Script.

% --- 1. Rectifier - Front-End Converter Parameters ---
rectifier.ACVoltagePP = 415; % V % RMS value of Phase-phase voltage
rectifier.ACVoltagePN = rectifier.ACVoltagePP/sqrt(3); % V 
rectifier.ACVoltagePeak = rectifier.ACVoltagePN * sqrt(2); % V 
rectifier.DCCurrent = 700; % A
rectifier.DCVoltage = 800; % V

rectifier.SystemFrequency = 50; % Hz
rectifier.SwitchFrequency = 10e3; % Hz

rectifier.minVdcPossible = rectifier.ACVoltagePP*sqrt(2/3)/0.5; % V
rectifier.acCurrent = sqrt(2)*rectifier.DCCurrent*rectifier.DCVoltage/(sqrt(3)*rectifier.ACVoltagePP); % A

rectifier.maxLVal = 0.95*((rectifier.DCVoltage*0.5)-rectifier.ACVoltagePP*sqrt(2/3))/(2*pi*rectifier.SystemFrequency*rectifier.acCurrent); % H
rectifier.maxACcurrent = 100; % A
rectifier.minACcurrent = -100; % A
rectifier.maxACVoltage = 515; % V
rectifier.minACVoltage = -515; % V
rectifier.minDCVoltage = 0.5*rectifier.DCVoltage; % V

rectifier.lineInductance = 0.1e-3; % H
rectifier.lineResistance = 20e-3; % ohm
rectifier.lineT = rectifier.lineInductance/rectifier.lineResistance; % s 
rectifier.OutputCapacitance = 100e-3; % F
rectifier.a = 2; % constant

rectifier.VoltageSensorG = 1; % constant
rectifier.VoltageSensorT = 1/(10*rectifier.SwitchFrequency); % s
rectifier.CurrentSensorG = 1; % constant
rectifier.CurrentSensorT = 1/(10*rectifier.SwitchFrequency); % s
rectifier.G = rectifier.DCVoltage/2; % constant
rectifier.K = rectifier.ACVoltagePeak/rectifier.DCVoltage; % constant
rectifier.Td = 1/(2*rectifier.SwitchFrequency); % s
rectifier.Tphi = rectifier.Td + rectifier.CurrentSensorT; % s
rectifier.Tdel = (2*rectifier.Tphi) + rectifier.VoltageSensorT; % s

rectifier.controller.CurrentG = rectifier.lineInductance/...
    (2*rectifier.G*rectifier.CurrentSensorG*rectifier.Tphi); % constant
rectifier.controller.CurrentT = rectifier.lineT; % s
rectifier.controller.VoltageG = (rectifier.OutputCapacitance...
    *rectifier.CurrentSensorG)/...
    (rectifier.K*2*rectifier.VoltageSensorG*rectifier.Tdel); % constant
rectifier.controller.VoltageT = 4*rectifier.Tdel; % s
%%

% --- 2. DC-DC Converter Parameters ---
inverter.SwitchFrequency = 10e3; % Hz
inverter.controller.kp = 2; % constant
inverter.controller.ki = 1; % constant
inverter.inductance = 10e-6; % H
transformer.magnetizingL = 1; % H
transformer.windingFactor = 0.5; % constant
chopper.VoltageSensorG = 1; % constant
chopper.VoltageSensorT = 1/(10*inverter.SwitchFrequency); % s
chopper.CurrentSensorG = 1; % constant
chopper.CurrentSensorT = 1/(10*inverter.SwitchFrequency); % s
%%

% --- 3. Simulation Time & Variants ---
simulation.numberOfCycles = 10; % constant
simulation.simTime = simulation.numberOfCycles/rectifier.SystemFrequency; % s

powerCircuit = 0; % 0 = Average, 1 = Two Level, 2 = Three Level
average = Simulink.Variant(' powerCircuit == 0 ');
twoLevel = Simulink.Variant(' powerCircuit == 1 ');
threeLevel = Simulink.Variant(' powerCircuit == 2 ');

% --- 4. Vehicle Selection & Battery Database (Option 1 Scaling) ---
if ~exist('vehicleSelect', 'var')
    vehicleSelect = 1; % Default fallback
end

battery.initialSOC = 0.0; % constant
battery.AHRating = 2.9;   % Base Panasonic NCR18650PF Ah
battery.inductance = 5e-3; % H
battery.maxCellVoltage = 4.2; % V

switch vehicleSelect
    case 1
        % Nissan Leaf (24 kWh)
        battery.cellsInSeries = 101; 
        battery.batteryStringsInParallel = 23;
        battery.maxPackChargeCurrent = 125; 
        battery.idTag = 'TAG_LEAF_01';
    case {2, '2', 'Kia EV6'}
        % 2. Kia EV6 Long Range (77.4 kWh) - 800V Class
        battery.cellsInSeries = 192; % ~806V max
        battery.batteryStringsInParallel = 38;
        battery.maxPackChargeCurrent = 350; % Limits at ~239kW
        battery.idTag = 'TAG_EV6_02';
    case 3
        % Tesla Model 3 Long Range (85.3 kWh)
        battery.cellsInSeries = 97;
        battery.batteryStringsInParallel = 84;
        battery.maxPackChargeCurrent = 600; 
        battery.idTag = 'TAG_TESLA_03';
   case {4, '4', 'Rivian R1T'}
        % 4. Rivian R1T Large Pack (135 kWh) - 400V Class
        battery.cellsInSeries = 108; % ~453V max
        battery.batteryStringsInParallel = 115;
        battery.maxPackChargeCurrent = 500; % Pulls massive current to hit 220kW at 400 
        battery.idTag = 'TAG_RIVIAN_04';
    case 5
        % Chevrolet Bolt EV (65 kWh)
        battery.cellsInSeries = 97;
        battery.batteryStringsInParallel = 64;
        battery.maxPackChargeCurrent = 150; 
        battery.idTag = 'TAG_BOLT_05';
end
%%

% --- 5. ISO 15118 Dynamic Hardware Negotiation Limits --
EVSEMaximumCurrentLimit = rectifier.DCCurrent; 
EVSEMaximumVoltageLimit = rectifier.DCVoltage * transformer.windingFactor; 

EVMaximumVoltageLimit = battery.cellsInSeries * battery.maxCellVoltage; 
EVMaximumCurrentLimit = battery.maxPackChargeCurrent; 
EVMaximumPowerLimit = EVMaximumVoltageLimit * EVMaximumCurrentLimit;
%%


%[appendix]{"version":"1.0"}
%---
%[metadata:view]
%   data: {"layout":"onright"}
%---
