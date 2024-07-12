import pyvisa
import time
from libPS import PowerSupply

#DP832A_addr = 'USB0::0x1AB1::0x0E11::DP8B212300503::INSTR' # On Mac OS
DP832A_addr = 'USB0::6833::3601::DP8B212300503::0::INSTR' # On RPi

if __name__ == "__main__":
    DCps=PowerSupply()

    # Set channel 1 to 12V, 1A
    DCps.set_channel_voltage(DCps, 1, 12.0, 1.0,ocp=1.2)
    print("Channel 1 set to 12V, 1A and turned on")

    # Set channel 2 to 12V, 1A
    DCps.set_channel_voltage(DCps, 2, 12.0, 1.0,ocp=1.3)
    print("Channel 2 set to 12V, 1A and turned on")

    # Measure currents from channel 1 and 2 every second
    try:
        count = 0
        while True:
            current_ch1 = DCps.query_current(DCps, 1)
            current_ch2 = DCps.query_current(DCps, 2)
            print(f"Channel 1 Current: {current_ch1} A")
            print(f"Channel 2 Current: {current_ch2} A")
            time.sleep(0.5) # sleep for 0.5 seconds
            count += 1
            # after 10 measurements, stop the DC power supply and close the connection
            if count >= 10:
                DCps.resource.write('OUTP CH1,OFF')
                DCps.resource.write('OUTP CH2,OFF')
                break
    except KeyboardInterrupt:
        print("Measurement stopped by user.")
    finally:
        # Close the connection
        DCps.close()