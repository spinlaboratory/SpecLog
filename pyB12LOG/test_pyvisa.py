import pyvisa
import time
rm = pyvisa.ResourceManager()
devices_list = rm.list_resources()
last_devices_list = devices_list
while(1):
    devices_list = rm.list_resources()
    if devices_list != last_devices_list:
        print('device list updated!')
    for device in devices_list:
        try: 
            print(device)
            inst = rm.open_resource(device)
            print(inst.query("*IDN?"))
        except:
            pass
    last_devices_list = devices_list
        
    time.sleep(2)
            
