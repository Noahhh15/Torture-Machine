# Procedure:
# - Home the machine in UGS. Then unlock (by pressing 'soft reset' then 'unlock') then  and jog -Z a few millimeters
# - Place your sample between the clamps
# - Jog in the -Z direction until the sample is straight but under minimal tension
# - record the Z value in the [offset] variable below. (don't include the negative sign)
# - change [desired_stretch], [cycles], and [feed_rate] to the desired values
# - in the same directory as this program, navigate to 'gcode.txt' and copy its contents
# - press "Machine" -> "Edit Macros" and paste into a new macro and name accordingly

#VARIABLES
offset = 17 #mm
desired_stretch = 20 #percent
cycles = 45000
feed_rate = 3000 #mm/min

#DO NOT TOUCH BELOW
min_length = 135 #mm
max_length = 236 #mm
original_length = min_length + offset - 2

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

f = open("gcode.txt", 'w')
f.write("G90;\n")

offset = original_length - min_length
target = original_length * desired_stretch / 100 + offset

if target > max_length:
    print(f"{bcolors.FAIL}desired stretch would exceed physical bounds. no gcode written{bcolors.ENDC}")
    print(f"""{bcolors.WARNING}NOTE: the data (if any) in output.txt is NOT the desired output.
    Please reduce the desired stretch or reduce the original length of the sample and try again.{bcolors.ENDC}""")
else:
    for i in range(cycles):
        instance = f"G0Z{-(offset + 3)}F{feed_rate};\nG0Z{-(offset + 2)}F500;\nG0Z-{target}F{feed_rate};\n"
        f.write(instance)
    else:
        f.write(f"G0Z{-(offset + 3)}F{feed_rate};\nG0Z{-(offset + 2)}F500;")
        f.close()
        print(f"{bcolors.HEADER}{original_length}mm sample at {desired_stretch}% elongation for {cycles} cycles.{bcolors.ENDC}")
        print(f"{bcolors.OKGREEN}gcode saved in 'gcode.txt'{bcolors.ENDC}")

        length_travelled = (target - (offset + 3)) * cycles
        direction_change_delay = 1/60 #min
        estimated_time = length_travelled / feed_rate + cycles * 1 / 500 + direction_change_delay * cycles
       
        #change to hours if too long
        if estimated_time > 100:
            estimated_time /= 60
            #change to days if too long
            if estimated_time > 50:
                estimated_time /=24
                print(f"{bcolors.OKCYAN}estimated job duration: {estimated_time:.2f} days{bcolors.ENDC}")
            else:
                print(f"{bcolors.OKCYAN}estimated job duration: {estimated_time:.2f} hours{bcolors.ENDC}")
        else:
            print(f"{bcolors.OKCYAN}estimated job duration: {estimated_time:.2f} minutes{bcolors.ENDC}")