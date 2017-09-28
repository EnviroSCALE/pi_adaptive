import paho.mqtt.client as mqttClient
import paho.mqtt.publish as pub
#import sqlite_db

from bitstruct import *
import time
import datetime
import traceback
import json


HOST_ECLIPSE = "iot.eclipse.org"
HOST_IQUEUE = "iqueue.ics.uci.edu"


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
            "readlatency": 0.6,
            "period": 8.0,
            "pin": 1
        },
        {
            "name": "mq4",
            "readlatency": 0.6,
            "period": 8.0,
            "pin": 6,
            "calib": 2
        },
        {
            "name": "mq6",
            "readlatency": 0.6,
            "period": 8.0,
            "pin": 7,
            "calib": 3
        },
        {
            "name": "mq135",
            "readlatency": 0.6,
            "period": 8.0,
            "pin": 8,
            "calib": 4
        },
        {
            "name": "dust",
            "readlatency": 0.6,
            "period": 8.0,
            "pin": 5
        }
    ],
    "params": {
        "alpha": 800,
        "beta": 1,
        "lambda": 0.005,
        "D": 100000
    },
    "interval": {
        "period_update": 100,
        "M": 1000,
        "upload": 10
    },
    "tx_medium": "wlan0",
    "mqtt_broker_host": "iqueue.ics.uci.edu"
}


sensor_conf = json.dumps(d)
c = json.loads(sensor_conf)


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("enviroscale/encoded/74da382afd91/")


# The callback for when a PUBLISH message is received from the server.
# Sent directly from raspberry pi to iot.eclipse.org
def on_message(client, userdata, msg):
    try:
        #print ("From topic: " + msg.topic + " , received: " + str(msg.payload))
        print ("From topic: " + msg.topic + " , received: ")
        # print (msg.payload)
        unpacked = decode_bitstruct(msg.payload, c)
        print unpacked
        N = unpacked[0]
        initial_time = unpacked[1]

        for i in range(N):
            id = unpacked[i+2]
            value = unpacked[i + N + 2]
            time_offset = unpacked[i + N*2 + 2]
            #lat = unpacked[2 + i*3 + (N)*3]
            #lon = unpacked[2 + i*3 + (N)*3 + 1]
            #alt = unpacked[2 + i*3 + (N)*3 + 2]
            lat = 10
            lon = 10
            alt = 10
            print ("lat", lat, "lin ", lon, "alt", alt)

            print ("Publishing now: ", id, value, time_offset)
            time = initial_time + (time_offset)
            #timestring =  datetime.datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S.%f')
            timestring = time
            publish(HOST_ECLIPSE, c["event"][id]["name"], value, timestring, lat, lon, alt)
    except:
        traceback.print_exc()
        print ("MQTT publish error")


#PCMAC:  d0df9a95296c (d0:df:9a:95:29:6c)
#PiMac:  74da382afd91
def publish(hostname, event, value,  timestamp, lat, lon, alt, device_id="74da382afd91", prio_class="low", prio_value=10 ):
    if lat == -1:
        lat = None
        lon = None
        alt = None

    d = {"d":
            {
                "timestamp": timestamp,
                "event": event,
                "value": value,
                "prio_class": prio_class,
                "prio_value": prio_value,
                "geotag":{
                    "lat": lat,
                    "lon": lon,
                    "alt": alt
                }
            }
        }
    #sqlite_db.insert(timestamp, event, value,prio_class,prio_value, lat, alt, lon)
    jsonstr = json.dumps(d)
    msg = jsonstr

    try:
        # "iot-1/d/801f02da69bc/evt/light/json"
        topic = "iot-1/d/" + device_id + "/evt/" + event + "/json"
        #topic = "paho/test/iotBUET/bulk/"
        #msgs = [{'topic': topic, 'payload': msg},
        #        ("paho/test/multiple", "multiple 2", 0, False)]
        pub.single(topic, payload=msg, hostname=hostname, port=1883)
        pub.single(topic+"plotly" , payload=msg, hostname=hostname, port=1883 )
        return True
    except:
        print ("error")
        traceback.print_exc()
        return False



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


#listen for receiving an encoded bundle
client = mqttClient.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(HOST_ECLIPSE, 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
