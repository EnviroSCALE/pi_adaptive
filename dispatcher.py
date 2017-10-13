# !/usr/bin/env python
from __future__ import print_function
import traceback
import Queue
import paho.mqtt.client as mqttc
import paho.mqtt.publish as pub
from socket import *
from circuits import Component, Debugger, handler, Event, Worker, task, Timer
import time
import datetime
import csv
import sys
# import from other files in main folder
from functions import *
from trace_generator import *
from pdb import set_trace as BP

#uncomment in pi
import gps.gpsdaemon
import sensors
###


MM = sys.argv[1] #input filename
DD = sys.argv[2] #output filename	
UU = sys.argv[3]
#RUN =   sys.argv[4]
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
			"pin": 17,
			"trace": "data_humidity_taiwan.csv"
		},
		{
			"name": "dht11",
			"size": 10,
			"readlatency": 0.6,
			"period": 8.0,
			"weight": 10,
			"pin": 17,
			"trace": "data_temp_taiwan.csv"
		},
		{
			"name": "mq4",
			"size": 10,
			"readlatency": 0.6,
			"period": 4.0,
			"pin": 2,
			"weight": 3,
			"calib": 2,
			"trace": "1.csv"
		},
		{
			"name": "mq6",
			"size": 10,
			"readlatency": 0.6,
			"period": 4.0,
			"pin": 3,
			"weight": 3,
			"calib": 3,
			"trace": "1.csv"
		},
		{
			"name": "mq135",
			"size": 10,
			"readlatency": 0.6,
			"period": 4.0,
			"pin": 1,
			"weight": 3,
			"calib": 4,
			"trace": "1.csv"
		},
		{
			"name": "dust",
			"size": 10,
			"readlatency": 0.6,
			"period": 10.0,
			"weight": 10,
			"pin": [0, 17],
			"trace": "data_dust_taiwan.csv"
		}
	],
	"params": {
		"alpha": 4.0,
		"beta": 1.0,
		"lambda": 0.005,
		"D": 8000
	},
	"interval": {
		"period_update": 6,
		"rate_update": 100,
		"M": 30,
		"upload": 6
	},
   "upload":{
	   "max_rate": 1000    
   },
   "filename": "output.csv",
  "overhead": 10,  
  "choice":2,
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
	#lprint(EventReport("Info", "Size to be uploaded: "+str(q.qsize())))
	queue_copy = []
	i = 0
	
	###
	sum_bifi = 0.0
	maxlim = CircuitsApp.aComputer.A
	
	
	while True:
		try:
			elem = q.get(block=False)
		except:
			break
		else:
			if CircuitsApp.dataDrop == True:
				
				iid = elem[0]
				sum_bifi += CircuitsApp.sensors[iid].b  * CircuitsApp.sensors[iid].F 
				if sum_bifi < maxlim:
					queue_copy.append(elem)
					print(elem)
				else:
					q = Queue.Queue()
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
	if N == 0:
		return None
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
		
		lprint(EventReport("Sent\t"+CircuitsApp.sensors[id].name, str(queue_elem[1])))

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
		CircuitsApp.good_uploaded += len(packed)
	except:
		traceback.print_exc()
		lprint(EventReport("Error", "upload_a_bundle failed."), 40)


def publish_packet_raw(message):
	#print (message)
        print ("PUBLISHING...")
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
		return ('%s \t %s \t %s \t %s \t %-14s \t %s') % (MM, DD, UU, round(self.time - starttimes[0],5), self.name, self.msg)
		#return ('%s \t %-14s \t %s') % (self.get_time_str(self.time - starttime), self.name, self.msg)

	def get_time_str(self, a_time):
		return datetime.datetime.fromtimestamp(a_time).strftime('%H:%M:%S')

class Sensor:
	def __init__(self, index, name, readlatency, period, pin, weight, size, trace_filename):
		self.id = index
		self.name = name
		self.readlatency = readlatency
		self.period = period
		self.pin = pin
		self.weight = weight
		self.size = size
		self.b = size/8.0
		self.F = 1.0/period # actual frequency, keep this unchanged
		self.trace = FunctionValueGenerator(trace_filename)

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
                # uncomment in pi
		lat, lon, alt = gps.gpsdaemon.read()
		#lat, lon, alt = (0,0,0)
		return (self.event_id, self.value, int(self.time), lat, lon, alt)



# Event Handlers
# ---------------

class ReadHandler(Component):
	def read_and_queue(self, sensor, readings_queue):
		sensor_name = c["sensor"][sensor.id]["name"]
		### value = sensors.read(sensor_name, sensor.pin)
		event_name = c["event"][sensor.id]["name"]
                pins =  c["sensor"][sensor.id]["pin"]

                # uncomment in pi
                value0, value1 = sensors.read(sensor_name, sensor.pin)
		
		#if event_name == "temperature":
		#value0 = CircuitsApp.sensors[sensor.id].trace.get_value(time.time() - CircuitsApp.starttime)
		#value1 = CircuitsApp.sensors[sensor.id].trace.get_value(time.time() - CircuitsApp.starttime)
		value = [value0, value1]
		
		print (value)
		lprint(EventReport("Generated\t"+sensor_name, str(value0)))
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
		t = time.time() - CircuitsApp.starttime
		if t > c["interval"]["M"]:
			self.fire(EndEvent())
		
		yield self.read_and_queue(args[0], args[1])
		s1 = args[0]
		q = args[1]
		print(EventReport(s1.name, "read complete."))
		CircuitsApp.timers["sense"] = Timer(s1.period, ReadEvent(s1, q), persist=False).register(self)



class UploadHandler(Component):      
	@handler("UploadEvent", priority=50)
	def upload_event(self, *args, **kwargs):
		
		## args[0] is the reading queue    
		queue = args[0]
		print(EventReport("UploadEvent", (str(args) + ", " + str(kwargs))))
		#lprint(EventReport("UploadEvent", "started"))
		
	
		
		CircuitsApp.shareState = 0
		yield self.call(task(upload_a_bundle(queue)))
		print ("Upload successful.")
		CircuitsApp.shareState = 1
		lprint(EventReport("UploadEvent", "ENDED"))
		CircuitsApp.last_uploaded = getSentByte() - CircuitsApp.startbyte
		lprint(EventReport("UploadedSoFar", str(convert_size(CircuitsApp.last_uploaded))), 45) 
		M = c["interval"]["M"]
		t = time.time() - CircuitsApp.starttime
		if (M == t):
			return
			#~ if(M - t < c["interval"]["upload"]):
			#~ CircuitsApp.timers["upload"] = Timer((M - t), UploadEvent(args[0]), persist=False).register(self)
		#~ else:
			
		if not CircuitsApp.isEnd:		
			CircuitsApp.timers["upload"] = Timer(c["interval"]["upload"], UploadEvent(args[0]), persist=False).register(self)
		rate = CircuitsApp.upload_rate
		u = CircuitsApp.last_uploaded
		CircuitsApp.upload_rate = min((c["params"]["D"] - u) * 1.0 / (M - t), c["upload"]["max_rate"])
		#CircuitsApp.upload_rate = (c["params"]["D"] - u) * 1.0 / (M - t)
	   


class PeriodUpdateHandler(Component):
	@handler("PeriodUpdateEvent", priority=20)
	def update(self, *args, **kwargs):        
		print(EventReport("PeriodUpdateEvent", "started"))
		CircuitsApp.timers["period_update"] = Timer(c["interval"]["period_update"], PeriodUpdateEvent(), persist=False).register(self)
		choice = CircuitsApp.choice
		# loss function = ln (f)   
		
	
		
		k = len(CircuitsApp.sensors)            
		alpha = c["params"]["alpha"]
		#alpha = 0
		beta = c["params"]["beta"]
		rate = CircuitsApp.upload_rate
		T = c["interval"]["upload"]
		c["overhead"] = 10
		if rate*T == alpha:
			return
		
		t = time.time() - CircuitsApp.starttime

		if CircuitsApp.choice == 2:
			lamb = CircuitsApp.aComputer.computeLambda(CircuitsApp.last_uploaded, t)
			if CircuitsApp.aComputer.fitsBudget == False:
				lprint(EventReport("Fit","No"))
				if lamb > 0:
					CircuitsApp.dataDrop = False
					lprint(EventReport("DataDrop","No"))
					for i in range(0, k):
						wi = CircuitsApp.sensors[i].weight
						Fi = CircuitsApp.sensors[i].F
						bi = CircuitsApp.sensors[i].b
						fi = (Fi - (lamb*bi)/(2.0*wi)) 
						if fi <= 0:
							for j in range(0, k):	
								CircuitsApp.sensors[i].period = 1.0/CircuitsApp.sensors[j].F
							CircuitsApp.dataDrop = True	
							lprint(EventReport("DataDrop","NegativeYes"))
							break
						pi = 1.0/fi   						
						lprint(EventReport("PeriodUpdate\t"+CircuitsApp.sensors[i].name, str(pi)))
						CircuitsApp.sensors[i].period = pi   		
				else:
					lprint(EventReport("DataDrop","Yes"))
					CircuitsApp.dataDrop = True
			else:
				lprint(EventReport("Fit","Yes"))
				for i in range(0, k):	
					CircuitsApp.sensors[i].period = 1.0/CircuitsApp.sensors[i].F
		
		if CircuitsApp.choice == 0:
			lamb = CircuitsApp.aComputer.computeLambda(CircuitsApp.last_uploaded, t)
			if CircuitsApp.aComputer.fitsBudget == False:
				lprint(EventReport("Fit","No"))
				if lamb > 0:
					CircuitsApp.dataDrop = False
					lprint(EventReport("DataDrop","No"))
					for i in range(0, k):
						wi = CircuitsApp.sensors[i].weight
						Fi = CircuitsApp.sensors[i].F
						bi = CircuitsApp.sensors[i].b
						fi =  (wi)/(lamb*bi)
						if fi <= 0:
							for j in range(0, k):	
								CircuitsApp.sensors[i].period = 1.0/CircuitsApp.sensors[j].F
							CircuitsApp.dataDrop = True	
							lprint(EventReport("DataDrop","NegativeYes"))
							break
						pi = 1.0/fi   						
						lprint(EventReport("PeriodUpdate\t"+CircuitsApp.sensors[i].name, str(pi)))
						CircuitsApp.sensors[i].period = pi   		
				else:
					lprint(EventReport("DataDrop","Yes"))
					CircuitsApp.dataDrop = True
			else:
				lprint(EventReport("Fit","Yes"))
				for i in range(0, k):	
					CircuitsApp.sensors[i].period = 1.0/CircuitsApp.sensors[i].F
		#~ for i in range(0, k):			
			#~ if CircuitsApp.choice == 0:
				#~ pi = max(0, 1.0 * (denom/math.sqrt(CircuitsApp.sensors[i].weight)) * (math.sqrt(CircuitsApp.sensors[i].size/8.0) + c["overhead"]) * beta * T / (rate * T - alpha))
				#~ CircuitsApp.sensors[i].period = pi
				
			#~ if CircuitsApp.choice == 1:
				#~ pi = max(0, 1.0 * (1/CircuitsApp.sensors[i].weight) * ((CircuitsApp.sensors[i].size/8.0) + c["overhead"]) * beta * T / (rate * T - alpha))
				#~ CircuitsApp.sensors[i].period = pi
				
			
				
	
class EndHandler(Component):
	@handler("EndEvent", priority=100)
	
	def end_event(self, *args, **kwargs):
		lprint(EventReport("EndEvent", "started"))
		CircuitsApp.isEnd = True
		CircuitsApp.h1.unregister()
		CircuitsApp.h2.unregister()
		CircuitsApp.h3.unregister()
		try:
			util = CircuitsApp.last_uploaded*100.0/c["params"]["D"]
			goodput = CircuitsApp.good_uploaded*100.0/CircuitsApp.last_uploaded
		except:
			util = 0
			goodput = 0
			traceback.print_exc()
		
		result = [c["params"]["D"],c["interval"]["M"],c["interval"]["upload"], util, goodput ]
		if CircuitsApp.shareState == 0:
			lprint(EventReport("EndEvent", "UPLOAD"))
			#yield self.fire(task(UploadEvent(CircuitsApp.readings_queue)))
		lprint(EventReport("Utilization", str( CircuitsApp.last_uploaded*100.0/c["params"]["D"]   )  ) )
		lprint(EventReport("Goodput", str(CircuitsApp.good_uploaded*100.0/CircuitsApp.last_uploaded)) )
		with open(c["filename"], 'a') as f:
			writer = csv.writer(f)
			writer.writerow(result)
		CircuitsApp.unregister()
		exit(0)

 
class AdaptiveComputer:
	def __init__(self, choice, D, M, alpha, beta, T, sensors):
		self.choice = choice
		self.D = D*1.0
		self.M = M*1.0
		self.alpha = alpha*1.0
		self.beta = beta*1.0
		self.T = T*1.0
		self.sensors = sensors
		self.sum_biFi = 0.0
		self.sum_bi_wi = 0.0
		self.A = (D/M - self.alpha/self.T)/self.beta
		
		self.fitsBudget = False
		for s in sensors:
			self.sum_biFi += s.b * s.F
			self.sum_bi_wi += s.b/s.weight
		
		
	def computeA(self, total_uploaded_so_far, current_time):
		D = self.D - total_uploaded_so_far
		M = self.M - current_time
		#D = c["params"]["D"]
		#M = end_time = c["interval"]["M"]
		A = (D/M - self.alpha/(self.T))/self.beta
		if self.sum_biFi <= A:
			self.fitsBudget = True
		else:
			self.fitsBudget = False
		if A <= 0:
			lprint(EventReport("NoUpload", "A negative"))
			CircuitsApp.dataDrop = True
		self.A = A
		return A
	
	
	def computeLambda(self, total_uploaded_so_far, current_time):
		# Calculation of A
		A = self.computeA(total_uploaded_so_far, current_time)
		# loss function (Fi - fi)^2
		if self.choice == 2:
			lamb = 2.0*(self.sum_biFi - A)/self.sum_bi_wi
		if self.choice == 0:
			lamb = 1.0/A	
		return lamb
		
		


class ReadEvent(Event):
	"""read"""
class UploadEvent(Event):
	"""upload: args[0]: self.readings_queue"""
class PeriodUpdateEvent(Event):
	"""upload"""
class EndEvent(Event):
	"""end"""


class App(Component):
	#@# Register all handlers
	h1 = UploadHandler()
	h2 = ReadHandler()
	h3 = PeriodUpdateHandler()
	h4 = EndHandler()
	#~ h4 = RateUpdateHandler()

	##@# Shared state communication
	shareState = 0
	isEnd = False
	dataDrop = False
	
	readings_queue = Queue.Queue()
	bought_data = c["params"]["D"]
	end_time = c["interval"]["M"]
	upload_rate = 1.0 * bought_data / end_time
	
	
	##@# Globals and performance variables 
	sensors = []
	last_uploaded = 0.0
	good_uploaded = 0.0
	
	startbyte = getSentByte()
	startrbyte = getRcvdByte()
	starttime = time.time()
	#lprint(EventReport("Info", "Start Time is: " + get_time_as_string(starttime)))

	endtime = 0
	timers = {}

	def init_scene(self):       
		##@# Time starts here
		
		lprint(EventReport("Event", "Init Scene"))
		
		self.lag = 0
		self.sensors = []
		sum_weight = 0.0		
		num_sensors = len(c["sensor"])
		for i in range(0, num_sensors):
			s1 = Sensor(i, c["sensor"][i]["name"], c["sensor"][i]["readlatency"], c["sensor"][i]["period"],
						c["sensor"][i]["pin"], c["sensor"][i]["weight"], c["sensor"][i]["size"], c["sensor"][i]["trace"])
			sum_weight = sum_weight + c["sensor"][i]["weight"]
			self.sensors.append(s1)
		
		for i in range(0, num_sensors):
			s1 = self.sensors[i]
			s1.weight = (s1.weight * 1.0) / sum_weight
		
		
		c["interval"]["M"] = int(MM)
		c["params"]["D"] = int(DD)
		c["interval"]["period_update"] = int(UU)
		c["interval"]["upload"]= int(UU)
		
		self.endtime = (c["interval"]["M"])
		self.bought_data = c["params"]["D"]
		self.choice = c["choice"]
		
		print(self.sensors)
		
		self.aComputer = AdaptiveComputer(self.choice, c["params"]["D"], c["interval"]["M"], c["params"]["alpha"], c["params"]["beta"], c["interval"]["upload"], self.sensors)
			
		##@# Schedule first-time sensor events	
		for i in range(0, num_sensors):
			s1 = self.sensors[i]
			CircuitsApp.timers["sense"] = Timer(s1.period, ReadEvent(s1, self.readings_queue), persist=False).register(self)

		CircuitsApp.timers["upload"] = Timer(c["interval"]["upload"], UploadEvent(self.readings_queue), persist=False, process=True).register(self)
		# self.fire(PeriodUpdateEvent())
		CircuitsApp.timers["period_update"] = Timer(c["interval"]["period_update"], PeriodUpdateEvent(), persist=False).register(self)
		CircuitsApp.timers["end"] = Timer(c["interval"]["M"], EndEvent(), persist=False).register(self)
		# CircuitsApp.timers["rate_update"] = Timer(c["update_interval"]["rate"], RateUpdateEvent(self.readings_queue), persist=False).register(self)
		self.starttime = time.time()
		starttimes[0] =  self.starttime
	def started(self, component):
		##@# Registering MQTT Controller
		while True:
			break
			try:
				actuatorClient = mqttc.Client()
				actuatorClient.on_connect = on_connect
				actuatorClient.on_message = on_message
				actuatorClient.connect(MQTT_BROKER_HOSTNAME, 1883, 60)
				actuatorClient.loop_start()
				lprint(EventReport("Success", "MQTT controller connected."))
				print(EventReport("Tx", str(get_tx_bytes(TX_MEDIUM))))
				break
			except gaierror:
				print(EventReport("Error", "Failure connecting to MQTT controller."))
			time.sleep(TIMEOUT_MQTT_RETRY)
		self.init_scene()

##@# MQTT Connect
def on_connect(client, userdata, flags, rc):
	print("PI is listening for controls from paho/test/iotBUET/piCONTROL/ with result code " + str(rc))
	client.subscribe("paho/test/iotBUET/piCONTROL/")

##@# MQTT Listen
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
			print(EventReport("Event", "Execution paused."))

		if (parsed_json["camera"] == "Y"):
			print(EventReport("Control", "TAKE PICTURE received."))
			newstr = "image" + str(time.time()) + ".jpg"
			try:
				take_picture(newstr)
				print(EventReport("Event", "Picture taken."))
			except:
				print(EventReport("Error", "picture."))

		lprint(EventReport("Event", "Received a control string."))
		print(parsed_json)
	except:
		print("From topic: " + msg.topic + " INVALID DATA")


CircuitsApp = App()
CircuitsApp.run()
#~ if __name__ == '__main__':
	#~ (App()).run()
#~ lprint(EventReport("Keyboard Exit."))
