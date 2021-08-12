# PROCEDURE
# - create a macro in UGS by following the procedure in 'gcode_maker.py'
# - load your sample in the machine
# - make sure the WinDaq is in CDC mode (when powered on, the 'active' light should flash yellow, not green)
# - connect the arduino to the limit switch and the computer
# - change the COM ports in the 'VARIABLES' section below to the respective ports of the Dataq and Arduino (this can be found in device manager)
# - start running this script BEFORE pressing the macro on UGS
# - if you want to change the upper resistance value before halting, change [BROKEN_BOUND] to the desired resistance, in ohms

import serial
import time
import os
import csv
import traceback
import logging

#VARIABLES
DATAQ_PORT = 'COM8'
ARDUINO_PORT = 'COM9'
BROKEN_BOUND = 30


DIR_CHANGE_TOL = 0.05
RECORD_RATE = 200 #data points per min
BROKEN_CONDUCTOR_TOL = 0.15 #ohms
CYCLE_TOL = 1

class Calibration:
    lower = []
    upper = []
    def __init__(self, a1, a2):
        self.lower = a1
        self.upper = a2

#calibration are defined as: [first_voltage, first_target], [second_voltage, second_target]
resistance_calibration = Calibration([-5.9985, 10.006],  [-9.6143, .964])
stretch_calibration = Calibration([0.793, 13.5],[1.126, 20])

def transfer_units(cal, v):
    target_diff = cal.upper[1]-cal.lower[1]
    base_diff =  cal.upper[0]-cal.lower[0]
    ratio = target_diff / base_diff
    return (v - cal.lower[0]) * ratio + cal.lower[1]

serDataq = serial.Serial(DATAQ_PORT)
serArduino = serial.Serial(
    port = ARDUINO_PORT,\
    baudrate = 115200,\
    parity = serial.PARITY_NONE,\
    stopbits = serial.STOPBITS_ONE,\
    bytesize = serial.EIGHTBITS,\
    timeout = 0)
serArduino.flushInput()

serDataq.write(b"stop\r")        #stop in case device was left scanning
serDataq.write(b"eol 1\r")
serDataq.write(b"encode 1\r")    #set up the device for ascii mode
serDataq.write(b"slist 0 0\r")   #scan list position 0 channel 0 thru channel 7
serDataq.write(b"slist 1 1\r")
serDataq.write(b"slist 2 2\r")
serDataq.write(b"slist 3 3\r")
serDataq.write(b"slist 4 4\r")
serDataq.write(b"slist 5 5\r")
serDataq.write(b"slist 6 6\r")
serDataq.write(b"slist 7 7\r")
serDataq.write(b"srate 6000\r")
serDataq.write(b"dec 500\r")
serDataq.write(b"deca 3\r")
time.sleep(1)  
serDataq.read_all()              #flush all command responses
serDataq.write(b"start\r")           #start scanning

print("Please enter the name of this test (this will be used to title the .csv output):")
FILENAME = input()

if os.path.exists(f"{FILENAME}.csv"):
    os.remove(f"{FILENAME}.csv")
   
with open(f"{FILENAME}.csv", "a") as f:
    writer = csv.writer(f, delimiter=",")
    writer.writerow(["Time (seconds)", "cycle #", "Resistance (ohms)", "length of sample (cm)"])
   

prev_direction = False #false represents downward motion. true represents upward motion
current_direction = False
previous_stretch = 0.
cycles = 0.

max_resistance = 0.
conductors_broken = 0
cycle_of_last_broken = 0
broken_info = {}

def print_info():
    print(f"Test ended. Conductor has exceeded {BROKEN_BOUND} ohms after {cycles} cycles.")
    for i in range(conductors_broken):
        print(f"Conductor {i+1} broke at {broken_info[i+1]['cycle']} cycles, reaching {broken_info[i+1]['resistance']} ohms.")
   
#polling a few times to get rid of strange datapoints
print("initializing...")
for i in range(6):
    j = serDataq.inWaiting()
    if j>0:
        serDataq.readline()
    print(str(int((float(i)/5)*100)) + "%")
    time.sleep(0.1)
   
start_time = time.time()
while True:
    try:
        i = serDataq.inWaiting()
        if i>0:
            line = serDataq.readline().decode("utf-8")
            resistance_voltage = line.split(",")[0]
            resistance = transfer_units(resistance_calibration, float(resistance_voltage))
            stretch_voltage = line.split(",")[1]
            stretch = transfer_units(stretch_calibration, float(stretch_voltage))
           
            #check if conductor has broken
            resistance_diff = resistance - max_resistance
            if resistance_diff > BROKEN_CONDUCTOR_TOL:
                if cycles > cycle_of_last_broken + CYCLE_TOL :
                    conductors_broken += 1
                    max_resistance = resistance
                    broken_info[conductors_broken] = {}
                    broken_info[conductors_broken]['resistance'] = max_resistance
                    broken_info[conductors_broken]['cycle'] = cycles
                    cycle_of_last_broken = cycles
                else:
                    max_resistance = resistance
                    broken_info[conductors_broken] = {}
                    broken_info[conductors_broken]['resistance'] = max_resistance
                    broken_info[conductors_broken]['cycle'] = cycles
                   
            print(f"resistance: {resistance:.3f} ohms\tstretch: {stretch:.3f} cm\tcycle #{cycles}\tconductors broken: {conductors_broken}")
           
            stretch_diff = float(stretch) - previous_stretch
            if stretch_diff < -DIR_CHANGE_TOL:
                current_direction = True
            elif stretch_diff > DIR_CHANGE_TOL:
                current_direction = False
            previous_stretch = float(stretch)
            if current_direction != prev_direction:
                cycles += 0.5
                prev_direction = current_direction
            if float(resistance) > BROKEN_BOUND:
               
                #send message to stop running
                serArduino.write(b"stop")
                time.sleep(0.1)
                serArduino.write(b"stop")
                time.sleep(0.1)
                #wait for confirmation
                while True:
                    if(serArduino.in_waiting > 0):
                        serialString = serArduino.readline()
                        if len(serialString) > 0:
                            print("Halted Stretch Tester")
                            serDataq.write(b"stop\r")
                            time.sleep(1)          
                            serDataq.close()
                            print_info()
                            break
                with open(f"{FILENAME}.csv", "a") as f:
                    f.write(f"Conductor broke after: {cycles} cycles.")
                break
            with open(f"{FILENAME}.csv", "a") as f:
                writer = csv.writer(f, delimiter = ",")
                writer.writerow([time.time() - start_time, cycles, resistance, stretch])
        pass
    except Exception as e:
        logging.error(traceback.format_exc())
        pass
    time.sleep(60/RECORD_RATE)