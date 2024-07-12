import pyvisa

# Initialisation de la ressource manager VISA
rm = pyvisa.ResourceManager('@py')

# Liste des ressources disponibles
print(rm.list_resources())

DP832A_addr = 'USB0::0x1AB1::0x0E11::DP8B212300503::INSTR'
DCps = rm.open_resource(DP832A_addr) # Connection to the DC power supply

# Configuration de la source DC (exemple : identification de l'instrument)
print(DCps.query('*IDN?'))

# Fermer la connexion
DCps.close()