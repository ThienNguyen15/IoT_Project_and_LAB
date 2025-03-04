import paho.mqtt.client as mqttclient
import time
import json
import threading

BROKER_ADDRESS = "app.coreiot.io"
PORT = 1883

# Declare device credentials for each device
DEVICES = [
    {"client_id": "NAME", "username": "iot_device1", "token": "PASS"},
    {"client_id": "NAME", "username": "iot_device2", "token": "PASS"},
    {"client_id": "NAME", "username": "iot_device3", "token": "PASS"},
]

def connected(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{userdata['username']}] Connected successfully!")
        client.subscribe("v1/devices/me/rpc/request/+")
    else:
        print(f"[{userdata['username']}] Connection failed! (rc={rc})")

def subscribed(client, userdata, mid, granted_qos):
    print(f"[{userdata['username']}] Subscribed successfully!")

def recv_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    print(f"[{userdata['username']}] Received: {payload}")
    try:
        jsonobj = json.loads(payload)
        if jsonobj.get('method') == "setValue":
            response = {'value': jsonobj.get('params', True)}
            client.publish('v1/devices/me/attributes', json.dumps(response), qos=1)
    except Exception as e:
        print(f"[{userdata['username']}] Error processing message: {e}")

def publish_data(device_info):
    # Create a client with a unique client ID for each device
    client = mqttclient.Client(device_info["client_id"])
    client.username_pw_set(device_info["username"], device_info["token"])

    # Set the user_data so that callbacks can identify which device is being used
    client.user_data_set(device_info)

    # Assign callbacks
    client.on_connect = connected
    client.on_subscribe = subscribed
    client.on_message = recv_message

    # Connect to the broker
    client.connect(BROKER_ADDRESS, PORT)
    client.loop_start()

    # Simulate sensor values
    temp = 26
    humi = 35
    light_intensity = 44

    # HCMUT
    if device_info["username"] == "iot_device1":
        long = 106.65789107082472
        lat = 10.772175109674038
    elif device_info["username"] == "iot_device2":
        long = 106.75789107082472
        lat = 10.872175109674038
    elif device_info["username"] == "iot_device3":
        long = 106.85789107082472
        lat = 10.972175109674038

    while True:
        collect_data = {
            "temperature": temp,
            "humidity": humi,
            "light": light_intensity,
            "long": long,
            "lat": lat
        }
        temp += 1
        humi += 1
        light_intensity += 1

        # Publish telemetry data
        client.publish('v1/devices/me/telemetry', json.dumps(collect_data), qos=1)
        print(f"[{device_info['username']}] Published: {collect_data}")
        time.sleep(5)

# Create and start a thread for each device
threads = []
for device in DEVICES:
    t = threading.Thread(target=publish_data, args=(device,))
    t.start()
    threads.append(t)

# Keep the main thread running
for t in threads:
    t.join()
