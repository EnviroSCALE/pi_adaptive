import serial, time
import csv
import sys
import traceback 
import os
from adc import readadc
import RPi.GPIO as GPIO
import spidev
import time

import dht11
import datetime


#pin[0] analog pin[1] digital
def setup(name, pin):
    if name == "dust":
        GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD
        GPIO.setup(pin[1], GPIO.OUT)  # set GPIO24 as an output $pinMode(iled, OUTPUT);
        GPIO.output(pin[1],0)  # to set port/pin to High, use => 1/GPIO.HIGH/True  #digitalWrite(iled, LOW); //iled default closed


def read(name, pin, verbose=True):
    if name == "mq135" or name == "mq4" or name == "mq6":
        val = readadc(pin)
        print (name + "read is " + str(val))
        return val, val
    if name == "dust":        
        samplingTime = .280 / 1000
        deltaTime = 40 / 1000000.0
        sleepTime = 9680 / 1000000.0
        GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD
        GPIO.setup(pin[1], GPIO.OUT)  # set GPIO24 as an output $pinMode(iled, OUTPUT);
        GPIO.output(pin[1],0)  # to set port/pin to High, use => 1/GPIO.HIGH/True  #digitalWrite(iled, LOW); //iled default closed
        time.sleep(0.1)
        GPIO.output(pin[1], 1)
        time.sleep(samplingTime)
        adcvalue = readadc(pin[0])
        GPIO.output(pin[1], 0)
        return adcvalue, adcvalue
        
    if name=="dht11":
        GPIO.setmode(GPIO.BCM)
        instance = dht11.DHT11(pin=pin)
        lastknown = (23, 35)
        result1, result2 = lastknown
        try:
            result = instance.read()
            if (result.is_valid):
                result1 = result.temperature
                result2 = result.humidity
                if(result2==0):
                    result1, result2 = lastknown
                if(verbose):
                    print "<{}> :: Temperature ::".format(name), result1
                    print "<{}> :: Humidity    ::".format(name), result2
            else:
                result1, result2 = lastknown
                if (verbose):
                    print "<{}> :: Temperature :: NOT VALID".format(name)
                    print "<{}> :: Humidity    :: NOT VALID".format(name)
            lastknown = result1, result2
	    return result1, result2
        except:
            print("ERROR in READ...read_temp")
            
