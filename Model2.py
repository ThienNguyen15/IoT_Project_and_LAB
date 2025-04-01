import paho.mqtt.client as mqttclient
import time
import json
import threading
import pandas as pd
import random
import re

BROKER_ADDRESS = "app.coreiot.io"
PORT = 1883

DEVICES = [
    {"client_id": "IOT_DEVICE_2", "username": "iot_device2", "token": "csek21"},
]

df = pd.read_csv(r"C:/GIT/IOT LAB/test.csv")
humidity_list = df['Relative_humidity_room'].tolist()[:100]
temp_list = df['Indoor_temperature_room'].tolist()[:100]

predicted_humidity = []
predicted_temp = []

with open(r"C:/GIT/IOT LAB/predictions2.txt", "r") as f:
    lines = f.readlines()
    for i in range(0, len(lines)-3, 4):
        match_humid = re.search(r"Predicted humidity:\s*([0-9.]+)", lines[i+1])
        match_temp = re.search(r"Predicted temperature:\s*([0-9.]+)", lines[i+2])

        if match_humid and match_temp:
            predicted_humidity.append(float(match_humid.group(1)))
            predicted_temp.append(float(match_temp.group(1)))

assert len(humidity_list) == len(predicted_humidity) == len(temp_list) == len(predicted_temp), "Mismatch data length!"

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
    client = mqttclient.Client(device_info["client_id"])
    client.username_pw_set(device_info["username"], device_info["token"])
    client.user_data_set(device_info)
    client.on_connect = connected
    client.on_subscribe = subscribed
    client.on_message = recv_message
    client.connect(BROKER_ADDRESS, PORT)
    client.loop_start()

    idx = 0
    i = 0
    while True:
        if idx > 0 and idx % 3 == 2:
            data = {
                "humidity": round(humidity_list[i], 2),
                "predicted_humidity": round(predicted_humidity[i], 2),
                "temperature": round(temp_list[i], 2),
                "predicted_temperature": round(predicted_temp[i], 2)
            }
            i += 3
        else:
            data = {
                "humidity": round(humidity_list[idx], 2),
                "temperature": round(temp_list[idx], 2)
            }
        idx += 1

        client.publish('v1/devices/me/telemetry', json.dumps(data), qos=1)
        print(f"[{device_info['username']}] Published: {data}")
        time.sleep(1)

threads = []
for device in DEVICES:
    t = threading.Thread(target=publish_data, args=(device,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
