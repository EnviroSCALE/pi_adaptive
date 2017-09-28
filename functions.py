# I am adding python 3 codes here

from __future__ import print_function
import sys
import time
import datetime
import os
import json
import logging.config
import logging

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def lprint(msg, loglevel=21):
	log.log(loglevel, msg)
	print (msg)
	
def setup_logging(
        default_path='config/logging.json',
        default_level=logging.INFO,
        env_key='LOG_CFG'
):
    """Setup logging configuration
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)



setup_logging()
log = logging.getLogger("<Dispatcher>")


# OS Specific Functions
#----------------------
def get_tx_bytes(transmission_medium):
    try:
        astring = 'cat /sys/class/net/' + transmission_medium + '/statistics/tx_bytes'
        return long(os.popen(astring).read())
    except:
        return 0

# Time Related
#-------------

def get_time_as_string(atime):
    return datetime.datetime.fromtimestamp(atime).strftime('%Y-%m-%d %H:%M:%S')



def edit_calib_config(fieldname, value):
    with open('config/calibration.json', 'r') as f:
        config = json.load(f)
    # edit the data
    config[fieldname] = value
    # write it back to the file
    with open('config/calibration.json', 'w') as f:
        json.dump(config, f)


def read_calib_config(fieldname):
    with open('config/calibration.json', 'r') as f:
        config = json.load(f)
    return config[fieldname]


import psutil
import time
import math

def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 5)
   return "%s %s" % (s, size_name[i])
  
def getSentByte(nic = "wlan0"):
	io_counters = psutil.net_io_counters(pernic=True)
	if nic in io_counters:
		io = io_counters[nic]
		return io.bytes_sent
	return -1

def getRcvdByte(nic = "wlan0"):
	io_counters = psutil.net_io_counters(pernic=True)
	if nic in io_counters:
		io = io_counters[nic]
		return io.bytes_recv
	return -1


#~ start_byte = getSentByte()
#~ while True:
	#~ newbytes = getSentByte() - start_byte
	#~ print (convert_size(newbytes))
	#~ time.sleep(6)
'''
#COMMENT_IN_PC
import time
import picamera
def take_picture(pic_name='image.jpg', delay=0):
    #pic_location = '/home/pi/workshop/camera/'
    pic_location = 'pictures/'
    pic_location = pic_location + pic_name
    with picamera.PiCamera() as camera:
        camera.start_preview()
        time.sleep(delay)
        camera.capture(pic_location)
        camera.stop_preview()
#COMMENT_IN_PC
'''
def take_picture(pic_name='image.jpg', delay=0):
    ''''''

#pic_location = '/home/pi/workshop/camera/image.jpg'
#take_picture()
