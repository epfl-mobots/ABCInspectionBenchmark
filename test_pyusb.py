import usb.core
import usb.util

# Find USB devices
dev = usb.core.find(find_all=True)

# Loop through devices, printing vendor and product ids
for cfg in dev:
    print('Vendor ID: {0}, Product ID: {1}'.format(hex(cfg.idVendor), hex(cfg.idProduct)))

