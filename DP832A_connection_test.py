import pyvisa

# Initialisation de la ressource manager VISA
rm = pyvisa.ResourceManager('@py')

# Liste des ressources disponibles
print(rm.list_resources())

# Connexion à l'oscilloscope (remplacez 'USB::0x1AB1::0x0588::DS1ZA194712345::INSTR' par votre adresse spécifique)
oscilloscope = rm.open_resource('USB::0x1AB1::0x0588::DS1ZA194712345::INSTR')

# Configuration de l'oscilloscope (exemple : identification de l'instrument)
print(oscilloscope.query('*IDN?'))

# Exemple de commande SCPI pour configurer et lire des données de l'oscilloscope
oscilloscope.write('AUTOSCALE')
waveform_data = oscilloscope.query('WAV:DATA?')

# Affichage des données
print(waveform_data)

# Fermer la connexion
oscilloscope.close()
