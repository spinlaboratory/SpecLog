from pyB12LOG import *
log = pyB12LOG()
debugLogger = log.initDebugLog()
while(1):
    try:
        log.log()
    except Exception as err:
        debugLogger.info(err)
        log = pyB12LOG()