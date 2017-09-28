import paho.mqtt.client as mqtt

HOST_ECLIPSE = "iot.eclipse.org"
HOST_IQUEUE = "iqueue.ics.uci.edu"
HOST = HOST_ECLIPSE


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("enviroscale/encoded/74da382afd91/#")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print("From topic: "+msg.topic+" , received: "+str(msg.payload))


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(HOST, 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
