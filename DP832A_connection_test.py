import pyvisa

# Initialisation de la ressource manager VISA
rm = pyvisa.ResourceManager('@py')
print("Resource Manager:", rm)

# Liste des ressources disponibles
resources = rm.list_resources()
print("Available Resources:", resources)

DP832A_addr = 'USB0::0x1AB1::0x0E11::DP8B212300503::INSTR'

if DP832A_addr in resources:
    DCps = rm.open_resource(DP832A_addr) # Connection to the DC power supply
    
    # Configuration de la source DC (exemple : identification de l'instrument)
    print(DCps.query('*IDN?'))

    # Fermer la connexion
    DCps.close()
else:
    print("Device not found in available resources")