#!/usr/bin/env python3
'''
Interface script to execute actuators successively, and samples & logs from ABC periodically. 
This script is intended to be used for testing ABCs (heaters + thermal, CO2 and humidty sensors).
The RPi connects to maximum 2 ABCs and one DC power supply.
'''
import sys
sys.path.append('brood_hostside/host')

from brood_hostside.host.libabc import ABCHandle
import brood_hostside.host.libui as libui
from pathlib import Path
import time
from libPS import PowerSupply

# Make a two element list that contains strings of the board_id of the two ABCs
ABC_ids = ['abc24'] # the ABCs connected to the RPi (max 2 because only two 12V sockets on the PS)

def verify_abc_cfg_file(cfg_path): 
    ''' Check if config file exists '''
    cfg_path = cfg_path.expanduser()
    if not cfg_path.is_file():
        raise FileNotFoundError(f"No config file found at '{cfg_path}'!")
    return True

def prep_point_influx(time, board_id, value, field, debug:bool=False) -> dict:
        point = {
            "time": ABCHandle.timestamp4db(time),
            "tags": {board_id: board_id},
            "measurement": "DCPS",
            "fields": {field: value},
        }
        if debug:
            print(f"DBG|{point}")

        return point

if __name__ == "__main__":
    # Check ABCs is correct
    if len(ABC_ids) > 2:
        raise ValueError("Only two ABCs can be connected to the RPi!")
    if len(ABC_ids) == 0:
        raise ValueError("At least one ABC must be connected to the RPi!")

    PS = PowerSupply()
    for i in range(len(ABC_ids)):
        PS.set_channel_voltage(i+1, 12.0, 1.5,ocp=1.5)
        PS.activate_channel(i+1)
    ABCs = []
    try:
        # infer cfg file from ABC board_id
        cfg_paths = [Path(f"./brood_hostside/host/cfg/inspection_cfgs/inspection_{ABC_id}.cfg") for ABC_id in ABC_ids] # The inspection config files to use
        print(cfg_paths)
        for cfg_path in cfg_paths:
            verify_abc_cfg_file(cfg_path)
        time.sleep(5) # Wait for the ABCs to boot up
        ABCs = [ABCHandle(cfg_path) for cfg_path in cfg_paths] # instantiate ABC objects

    except Exception as e:
        # Close the connection to the DC power supply after having deactivated the channels
        print("Problem detected with ABCs setup, shutting DCPS channels and connection")
        for i in range(len(ABC_ids)):
            PS.deactivate_channel(i+1)
        PS.close()
        raise e

    try:
        for ABC in ABCs:
            ABC.first_conn()
            # Prepare heaters to be activated...
            ABC.prepare_heaters(False)
            # ...and start any defined in cfgfile
        
        heaters_rosen = [None, None] # Heater currently being tested
        temp_target = 26 # Target temperature
        previous_currents = [float(PS.query_current(i+1)) for i in range(len(ABC_ids))]
        previous_voltages = [float(PS.query_voltage(i+1)) for i in range(len(ABC_ids))]
        last_second_time = time.time()
        points_queue = []

        while True:
            start_time = time.time()
            DCPS_currents = [float(PS.query_current(i+1)) for i in range(len(ABC_ids))]
            DCPS_voltages = [float(PS.query_voltage(i+1)) for i in range(len(ABC_ids))]

            # Every two seconds, log the DC PS data and ABC data
            if time.time() - last_second_time > 2:
                last_second_time = time.time() # Reset the time of the "last" log
                # Logging the DCPS data
                for i, ABC in enumerate(ABCs):
                    # Send the current and voltage data as data points to influxdb
                    Ipoints = prep_point_influx(time=time.time(),board_id= ABC_ids[i], value=DCPS_currents[i], field="current")
                    Vpoints = prep_point_influx(time.time(), ABC_ids[i], DCPS_voltages[i], field="voltage")
                    points_queue.extend([Ipoints, Vpoints])
                ABCs[0].db_handle.write_points(points_queue) # This takes some seconds
                points_queue = []

                # Now we log the ABC data
                for i,(ABC, heater_rosen) in enumerate(zip(ABCs, heaters_rosen)):
                    ABC.check_newday_and_roll_logfiles()
                    try:
                        ABC.loop(consume=False)
                        if ABC.i < 5:
                            continue # Skip the first 5 loops before starting the heaters

                        if heater_rosen is None:
                            heaters_rosen[i] = 0
                            ABC._activate_dict_of_heaters({heaters_rosen[i]:temp_target})
                        else:       
                            print(f"Last avg measure of heater{heater_rosen}: " + str(ABC.last_htr_data.h_avg_temp[heater_rosen]))             
                            if ABC.last_htr_data.h_avg_temp[heater_rosen] >= temp_target-1.1:
                                ABC.set_heater_active(heater_rosen, False)
                                ABC.set_heater_objective(heater_rosen, 0)
                                heaters_rosen[i] += 1
                                heaters_rosen[i] = heaters_rosen[i]%10
                                ABC._activate_dict_of_heaters({heaters_rosen[i]:temp_target})
                        if len(ABC_ids) > 1:
                            time.sleep(0.03)

                    except Exception as e:
                        # Try catching everything, so it can continue if not critical
                        is_bad_err = libui.handle_known_exceptions(e, logger=ABC.log)
                        libui.process_exception(is_bad_err, e, ABC)

            else:
                # Only keep a log the current if it has changed by more than 5%
                # Only keep a log the voltage if it has changed by more than 1%
                for i, ABC in enumerate(ABCs):
                    if abs(DCPS_currents[i] - previous_currents[i]) > 0.05*previous_currents[i]:
                        Ipoint = prep_point_influx(time=time.time(),board_id= ABC_ids[i], value=DCPS_currents[i], field="current")
                        points_queue.append(Ipoint)
                    if abs(DCPS_voltages[i] - previous_voltages[i]) > 0.01*previous_voltages[i]:
                        Vpoint = prep_point_influx(time=time.time(),board_id= ABC_ids[i], value=DCPS_voltages[i], field="voltage")
                        points_queue.append(Vpoint)

            previous_currents = DCPS_currents
            previous_voltages = DCPS_voltages

            # Ensure minimum 0.1s between each iteration
            if (0.1-(time.time()-start_time))>0: # Sometimes the time it takes is longer than 0.1s, i.e when we log the measurements
                time.sleep(0.1 - (time.time() - start_time))

    except KeyboardInterrupt:
        ABC.log("Stopping inspection - ctrl-c pressed.", level="INF")

    finally:
        # Deactivate heaters
        # NOTE: This causes more harm than good during an
        #       experiment, when e.g. the script fails due
        #       to the SD card becoming unwritable:
        #       The ABC will be unnecessarily deactivated!
        ABC.log("Deactivating all heaters before stop.")
        ABC.heaters_deactivate_all()
        # Disconnect from ABC gracefully
        ABC.stop(end_msg='Done.')
        # Close the connection to the DC power supply after having deactivated the channels
        for i in range(len(ABC_ids)):
            PS.deactivate_channel(i+1)
        PS.close()
