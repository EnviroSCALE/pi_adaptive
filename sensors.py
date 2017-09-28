import serial, time
import csv
import sys
import traceback 
import os
import time

import datetime
import random



def read(name, pin, verbose=True):
	val = (int(random.random()*100), 0)
	print (str(name) + "read is " + str(val))
	return val
   
