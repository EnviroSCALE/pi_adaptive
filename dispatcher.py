# !/usr/bin/env python
from __future__ import print_function
#import gps.gpsdaemon
import traceback
import Queue
import paho.mqtt.client as mqttc
import paho.mqtt.publish as pub
from socket import *
from circuits import Component, Debugger, handler, Event, Worker, task, Timer
import time
from functions import *
import datetime

# self-written library
import sensors

from bitstruct import *
import json

starttimes = [0]

# Read from config
# ------------------
'''
# size : how many bits
# id : index of event in json
# s : signed int
# u : unsigned int
# f : float
'''
d = {
    "event":
        [
            {"name": "temperature",
             "size": 10,
             "dtype": 's',
             "sensor": "dht11"
             },

            {"name": "humidity",
             "size": 8,
             "dtype": 'u',
             "sensor": "dht11"
             },

            {"name": "methane",
             "size": 10,
             "dtype": 'u',
             "sensor": "mq4"
             },

            {"name": "lpg",
             "size": 10,
             "dtype": 'u',
             "sensor": "mq6"

             },

            {"name": "co2",
             "size": 10,
             "dtype": 'u',
             "sensor": "mq135"
             },

            {"name": "dust",
             "size": 10,
             "dtype": 'u',
             "sensor": "dust"
             }
        ],
    "sensor": [
        {
            "name": "dht11",
            "size": 10,
            "readlatency": 0.6,
            "period": 8.0,
            "weight": 10,
            "pin": 1
        },
        {
            "name": "mq4",
            "size": 10,
            "readlatency": 0.6,
            "period": 4.0,
            "pin": 6,
            "weight": 3,
            "calib": 2
        },
        {
            "name": "mq6",
            "size": 10,
            "readlatency": 0.6,
            "period": 4.0,
            "pin": 7,
            "weight": 3,
            "calib": 3
        },
        {
            "name": "mq135",
            "size": 10,
            "readlatency": 0.6,
            "period": 4.0,
            "pin": 8,
            "weight": 3,
            "calib": 4
        },
        {
            "name": "dust",
            "size": 10,
            "readlatency": 0.6,
            "period": 10.0,
            "weight": 10,
            "pin": [5, 18]
        }
    ],
    "params": {
        "alpha": 800,
        "beta": 1,
        "lambda": 0.005,
        "D": 10000
    },
    "interval": {
        "period_update": 6,
        "rate_update": 100,
        "M": 40,
        "upload": 6
    },
   "upload":{
       "max_rate": 1000    
   },
  "overhead": 10,  
  "tx_medium": "wlan0",
  "mqtt_broker_host": "iot.eclipse.org"
}

sensor_conf = json.dumps(d)
c = json.loads(sensor_conf)

map_event_to_id = {}
for i in range(len(c["event"])):
    map_event_to_id[c["event"][i]["name"]] = i
# print (map_event_to_id)

TX_MEDIUM = c['tx_medium']
MQTT_BROKER_HOSTNAME = c["mqtt_broker_host"]
HOST_ECLIPSE = "iot.eclipse.org"
HOST_IQUEUE = "iqueue.ics.uci.edu"
TIMEOUT_MQTT_RETRY = 10


# Setup Logging
# ---------------
#~ setup_logging()
#~ log = logging.getLogger("<Dispatcher>")
#~ #logging.disable(logging.CRITICAL)  # uncomment this to disable all logging
#~ logging.disable(logging.INFO)



# Queue Related
# --------------
def queue_print(q):
    print("Printing start.")
    queue_copy = []
    while True:
        try:
            elem = q.get(block=False)
        except:
            break
        else:
            queue_copy.append(elem)
    for elem in queue_copy:
        q.put(elem)
    for elem in queue_copy:
        print(elem)
    print
    "Printing end."


#need to be updated to decode geotag
def decode_bitstruct(packed_bytes, c):

    fmt_decode = "=u8"    # how many readings ahead 8 bits unsigned, initial timestamp 32 bits float
    N = unpack(fmt_decode, packed_bytes)[0]
    print("IDDD", N)
    fmt_decode += "u32"
    # initial_time = unpack(fmt_decode, packed_bytes)[1]

    # each id is 4 bits
    for i in range(N):
        fmt_decode += "u4"

    unpacked2 = unpack(fmt_decode, packed_bytes)

    list_of_sensor_ids = unpacked2[2:(2+N+1)]
    #list_of_offsets = unpacked2[(2+N):]

    for i in list_of_sensor_ids:
        fmt_decode += str(c["event"][i]["dtype"]) + str(c["event"][i]["size"])
    for i in range(N):
        fmt_decode += "u16"

    unpacked3 = unpack(fmt_decode, packed_bytes)
    return unpacked3


def extract_queue_and_encode(q):
    # Part 1: Extracting all elements from queue to "queue_copy"
    if q.empty():
        return None
    lprint(EventReport("Info", "Size to be uploaded: "+str(q.qsize())))
    queue_copy = []
    i = 0
    while True:
        try:
            elem = q.get(block=False)
        except:
            break
        else:
            queue_copy.append(elem)
            print(elem)
        i = i + 1
        # to put a boundary on how many elements to pop
        # if i == 8:
        #    break

    # Part 2: Encoding elements in "queue_copy" and return a python "struct" object
    N = len(queue_copy)
    data = []

    fmt_string = "=u8"  # number of readings bundled together is assumed to be in range 0-255, hence 8 bits
    data.append(N)

    fmt_string += "u32"  # initial timestamp
    data.append(queue_copy[0][2])

    # append the event ids
    for queue_elem in queue_copy:
        fmt_string += "u4"  # we have provision for maximum 16 sensors, hence 4 bits
        event_id = queue_elem[0]
        data.append(event_id)

    # append the sensor values
    for queue_elem in queue_copy:
        id = queue_elem[0]
        fmt_string += str(c["event"][id]["dtype"]) + str(c["event"][id]["size"])
        data.append(queue_elem[1])

    # append the timestamp offsets
    for queue_elem in queue_copy:
        id = queue_elem[0]
        time_actual = queue_elem[2]
        time_offset = int((time_actual - queue_copy[0][2]))
        # print(time_actual - queue_copy[0][2])
        # print(time_offset)
        fmt_string += "u16"
        data.append(time_offset)
    
    for queue_elem in queue_copy:
        fmt_string += "f32f32f32"
        data.append(queue_elem[3])
        data.append(queue_elem[4])
        data.append(queue_elem[5])    
    packed = pack(fmt_string, *data)
    #unpacked = decode_bitstruct(packed, c)
    #print("PACCCCCCCCCCC", unpacked)
    return packed


# Uploading Functions
# ---------------------

def upload_a_bundle(readings_queue):
    try:
        packed = extract_queue_and_encode(readings_queue)
        
        print ("extract successful")
        if packed==None:
            lprint(EventReport("Error", "Bundle not ready yet"), 40)
            return

        if (publish_packet_raw(bytearray(packed)) == False):
            traceback.print_exc()
            newFileBytes = bytearray(packed)
            # make file
            with open('missing.bin', 'a') as newFile:
                newFile.write(newFileBytes)
                newFile.write("\n")
            lprint(EventReport("Missing", "publish failure recorded."), 40)
    except:
        traceback.print_exc()
        lprint(EventReport("Error", "upload_a_bundle failed."), 40)


def publish_packet_raw(message):
    print (message)
    try:
        #topic = "paho/test/iotBUET/bulk/"
        topic = "enviroscale/encoded/74da382afd91/"
        pub.single(topic, payload=message, hostname=MQTT_BROKER_HOSTNAME, port=1883)
        return True
        #pub.single(topic+"plotly" , payload=msg, hostname=hostname, port=1883 )
    except gaierror:
        lprint(EventReport("Error", "MQTT publish failed."), 40)
        return False



# Classes
# -------

class EventReport:
    def __init__(self, name, msg):
        self.name = name
        self.time = (time.time())
        self.msg = msg
        
    def __repr__(self):
        return ('%s \t %-14s \t %s') % (round(self.time - starttimes[0],5), self.name, self.msg)
        #return ('%s \t %-14s \t %s') % (self.get_time_str(self.time - starttime), self.name, self.msg)

    def get_time_str(self, a_time):
        return datetime.datetime.fromtimestamp(a_time).strftime('%H:%M:%S')

class Sensor:
    def __init__(self, index, name, readlatency, period, pin, weight, size):
        self.id = index
        self.name = name
        self.readlatency = readlatency
        self.period = period
        self.pin = pin
        self.weight = weight
        self.size = size

    def __repr__(self):
        return 'Sensor::%s' % self.name


class Reading:
    def __init__(self, event_id, value, time):
        self.time = time
        self.value = value
        self.event_id = event_id

    def __repr__(self):
        return 'Reading (%s, Time::%s, Value:: %f)' % (
             c["event"][self.event_id]["name"], str(get_time_as_string(self.time)), self.value)

        #return str(self.event_id)
    def tuple(self):
        #lat, lon, alt = gps.gpsdaemon.read()
        lat, lon, alt = (0,0,0)
        return (self.event_id, self.value, int(self.time), lat, lon, alt)



# Event Handlers
# ---------------

class ReadHandler(Component):
    def read_and_queue(self, sensor, readings_queue):
        sensor_name = c["sensor"][sensor.id]["name"]
        value = sensors.read(sensor_name, sensor.pin)
        print (value)
        time_of_read = (time.time())

        if sensor_name == "dht11":
            reading = Reading(map_event_to_id["temperature"], value[0], time_of_read)
            readings_queue.put(reading.tuple())
            reading = Reading(map_event_to_id["humidity"], value[1], time_of_read)
            readings_queue.put(reading.tuple())
        else:
            sensor_to_event = {"mq4": "methane", "mq6": "lpg", "mq135": "co2", "dust": "dust"}
            reading = Reading(map_event_to_id[sensor_to_event[sensor_name]], value[0], time_of_read)
            readings_queue.put(reading.tuple())
            if sensor_name == "dust":
                print ("DUSTTTT", reading)
                print (reading)
        print ("From read handler")
        lprint(EventReport("QueueSize", readings_queue.qsize()))

    @handler("ReadEvent", priority=10)
    def read_event(self, *args, **kwargs): 
        yield self.read_and_queue(args[0], args[1])
        s1 = args[0]
        q = args[1]
        lprint(EventReport(s1.name, "read complete."))
        CircuitsApp.timers["sense"] = Timer(s1.period, ReadEvent(s1, q), persist=False).register(self)



class UploadHandler(Component):      
    @handler("UploadEvent", priority=50)
    def upload_event(self, *args, **kwargs):
        ## args[0] is the reading queue    
        "hello, I got an event"
        print(EventReport("UploadEvent", (str(args) + ", " + str(kwargs))))
        ustart = get_time_as_string(time.time())
        lprint(EventReport("UploadEvent", "started"))
        queue = args[0]
        yield self.call(task(upload_a_bundle(queue)))
        print ("Upload successful.")
        lprint(EventReport("UploadEvent", "ENDED"))
        CircuitsApp.timers["upload"] = Timer(c["interval"]["upload"], UploadEvent(args[0]), persist=False).register(self)
        #yield self.fire(ReadEvent(args[0], args[1]))
        CircuitsApp.last_uploaded = getSentByte() - CircuitsApp.startbyte
        lprint(EventReport("Uploaded", str(convert_size(CircuitsApp.last_uploaded))), 45) 
        M = c["interval"]["M"]
        t = time.time() - CircuitsApp.starttime
        if (M == t):
            return
        rate = CircuitsApp.upload_rate
        u = CircuitsApp.last_uploaded
        CircuitsApp.upload_rate = min((c["params"]["D"] - u) * 1.0 / (M - t), c["upload"]["max_rate"])
       


class PeriodUpdateHandler(Component):
    @handler("PeriodUpdateEvent", priority=20)
    def update(self, *args, **kwargs):        
        print(EventReport("PeriodUpdateEvent", "started"))
        CircuitsApp.timers["period_update"] = Timer(c["interval"]["period_update"], PeriodUpdateEvent(), persist=False).register(self)
        choice = 1
        # loss function = ln (f)        
        if choice == 1:
            k = len(CircuitsApp.sensors)            
            alpha = c["params"]["alpha"]
            beta = c["params"]["beta"]
            rate = CircuitsApp.upload_rate
            T = c["interval"]["upload"]
            if rate*T == alpha:
                return
            for i in range(0, k):
                #ART
                pi = max(0, 1.0 * (1/CircuitsApp.sensors[i].weight) * (CircuitsApp.sensors[i].size + c["overhead"]) * beta * T / (rate * T - alpha))
                CircuitsApp.sensors[i].period = pi        
    
class EndHandler(Component):
    @handler("EndEvent", priority=40)
    def end_event(self, *args, **kwargs):
        lprint(EventReport("EndEvent", "started"))
        CircuitsApp.h1.unregister()
        CircuitsApp.h2.unregister()
        CircuitsApp.h3.unregister()
        lprint("Utilization\t" + str(CircuitsApp.last_uploaded*100.0/c["params"]["D"]) )
        CircuitsApp.unregister()
        


class ReadEvent(Event):
    """read"""
class UploadEvent(Event):
    """upload: args[0]: self.readings_queue"""
class PeriodUpdateEvent(Event):
    """upload"""
class EndEvent(Event):
    """end"""


class App(Component):
    h1 = UploadHandler()
    h2 = ReadHandler()
    h3 = PeriodUpdateHandler()
    h4 = EndHandler()
    #~ h4 = RateUpdateHandler()

    isEnd = False
    readings_queue = Queue.Queue()
    bought_data = c["params"]["D"]
    end_time = c["interval"]["M"]
    upload_rate = 1.0 * bought_data / end_time
    sensors = []
    last_uploaded = 0.0
    startbyte = getSentByte()
    startrbyte = getRcvdByte()
    starttime = time.time()
    lprint(EventReport("Info", "Start Time is: " + get_time_as_string(starttime)))

    endtime = 0
    timers = {}

    def init_scene(self):		
        self.starttime = time.time()
        starttimes[0] =  self.starttime
        lprint(EventReport("Info", "Init Scene"))
        self.sensors = []
        num_sensors = len(c["sensor"])
        sum_weight = 0.0
        for i in range(0, num_sensors):
            s1 = Sensor(i, c["sensor"][i]["name"], c["sensor"][i]["readlatency"], c["sensor"][i]["period"],
                        c["sensor"][i]["pin"], c["sensor"][i]["weight"], c["sensor"][i]["size"])
            sum_weight = sum_weight + c["sensor"][i]["weight"]
            self.sensors.append(s1)
        for i in range(0, num_sensors):
            s1 = self.sensors[i]
            s1.weight = (s1.weight * 1.0) / sum_weight
        self.endtime = (c["interval"]["M"])
        self.bought_data = c["params"]["D"]

        print(self.sensors)

        for i in range(0, num_sensors):
            s1 = self.sensors[i]
            CircuitsApp.timers["sense"] = Timer(s1.period, ReadEvent(s1, self.readings_queue), persist=False).register(self)

        CircuitsApp.timers["upload"] = Timer(c["interval"]["upload"], UploadEvent(self.readings_queue), persist=False, process=True).register(self)
        CircuitsApp.timers["period_update"] = Timer(c["interval"]["period_update"], PeriodUpdateEvent(), persist=False).register(self)
        CircuitsApp.timers["end"] = Timer(c["interval"]["M"], EndEvent(), persist=False).register(self)
        #CircuitsApp.timers["rate_update"] = Timer(c["update_interval"]["rate"], RateUpdateEvent(self.readings_queue), persist=False).register(self)

    def started(self, component):
        while True:
            break
            try:
                actuatorClient = mqttc.Client()
                actuatorClient.on_connect = on_connect
                actuatorClient.on_message = on_message
                actuatorClient.connect(MQTT_BROKER_HOSTNAME, 1883, 60)
                actuatorClient.loop_start()
                print(EventReport("Info", "Started."))
                print(EventReport("Tx", str(get_tx_bytes(TX_MEDIUM))))
                break
            except gaierror:
                print(EventReport("Error", "Failure connecting to MQTT controller"))
            time.sleep(TIMEOUT_MQTT_RETRY)
        self.init_scene()


def on_connect(client, userdata, flags, rc):
    print("PI is listening for controls from paho/test/iotBUET/piCONTROL/ with result code " + str(rc))
    client.subscribe("paho/test/iotBUET/piCONTROL/")


def on_message(client, userdata, msg):
    print("Received a control string")
    try:
        parsed_json = json.loads(msg.payload)
        if (parsed_json["power_off"] == "Y"):
            # do_power_off()
            print (EventReport("Control", "PAUSE EXECUTION received."))
            CircuitsApp.h1.unregister()
            CircuitsApp.h2.unregister()
            CircuitsApp.h3.unregister()
            CircuitsApp.unregister()
            print(EventReport("Info", "Execution paused."))

        if (parsed_json["camera"] == "Y"):
            print(EventReport("Control", "TAKE PICTURE received."))
            newstr = "image" + str(time.time()) + ".jpg"
            try:
                take_picture(newstr)
                print(EventReport("Info", "Picture taken."))
            except:
                print(EventReport("Error", "picture."))

        print(EventReport("Info", "Received a control string."))
        print(parsed_json)
    except:
        print("From topic: " + msg.topic + " INVALID DATA")


CircuitsApp = App()
CircuitsApp.run()
if __name__ == '__main__':
    (App()).run()
log.info("Keyboard Exit.")
