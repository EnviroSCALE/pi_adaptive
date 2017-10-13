import time
import datetime

setup_logging()
log = logging.getLogger("<GPS>")

class GPS:
    def __init__(self):
        self.name = "GPS"

    def read(self):
        ret1 = -1
        ret2 = -1
        try:
            return 23.723493644, 90.39389374
        except:
            log.exception('ERROR in READ...gps.py')
        return ret1, ret2
        
