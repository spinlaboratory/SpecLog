from logger import pyB12LOG
            
log = pyB12LOG()
while(1):
    try:
        log.log()
    except Exception as err:
        print(err)
        log = pyB12LOG()


