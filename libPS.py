'''
Library for interfacing with the DP832A power supply.
'''

import pyvisa

class PowerSupply:
    @classmethod
    def current_safe(current):
        """Check if the current is within the safety limits."""
        if current > 1.2:
            return False
        return True
        

    def __init__(self, address = 'USB0::6833::3601::DP8B212300503::0::INSTR'):
        '''
        Connect to the power supply and return the opened resource.
        '''

        # Initialize VISA resource manager
        rm = pyvisa.ResourceManager('@py')

        # List available resources
        resources = rm.list_resources()
        print("Available Resources:", resources)
        
        if address not in resources:
            raise Exception(f"Device {address} not found in available resources")
        
        try:
            self.resource = rm.open_resource(address)
            print("Connected to:", self.resource.query('*IDN?'))

        except Exception as e:
            print(f"Failed to connect to device: {e}")
            raise e
        
    def close(self):
        '''
        Close the connection to the power supply.
        '''
        self.resource.close()
    
    def query_current(self, channel):
        '''
        Query the current of the specified channel.
        return: the current if it is within the safety limits, otherwise it turns off the output of the channel and returns None.
        '''
        command = f"MEAS:CURR? CH{channel}"
        current = self.resource.query(command)
        current = float(current.strip())
        if PowerSupply.current_safe(current):
            return current
        else:
            # turn off the output of the channel
            self.resource.write(f"OUTP CH{channel},OFF")
            print(f"Current exceeds safety limit. Turned off channel {channel}")
            return None
        
    def query_voltage(self, channel):
        '''
        Query the voltage of the specified channel.
        '''
        command = f"MEAS:VOLT? CH{channel}"
        return self.resource.query(command)
    
    def set_channel_voltage(self, channel, voltage, current, ocp= None):
        '''
        Configure the specified channel with voltage, current and ocp.
        '''
        self.resource.write(f"INST:NSEL {channel}")  # Select the channel
        self.resource.write(f"VOLT {voltage}")       # Set the voltage
        self.resource.write(f"CURR {current}")       # Set the current limit
        if ocp is not None:
            self.resource.write(f"CURR:PROT {ocp}")  # Set the over current protection
            self.resource.write("CURR:PROT:STAT ON") # Enable the over current protection

    def activate_channel(self, channel):
        '''
        Activate the output of the specified channel.
        '''
        self.resource.write(f"OUTP CH{channel},ON")

    def deactivate_channel(self, channel):
        '''
        Deactivate the output of the specified channel.
        '''
        self.resource.write(f"OUTP CH{channel},OFF")