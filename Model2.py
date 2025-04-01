import paho.mqtt.client as mqttclient
import time
import json
import threading
import random
import numpy as np
import pandas as pd
import tensorflow as tf

BROKER_ADDRESS = "app.coreiot.io"
PORT = 1883

DEVICES = [
    {"client_id": "NAME", "username": "NAME", "token": "PASS"},
]

model = tf.keras.models.load_model("C:/GIT/IOT LAB/model2.h5", compile=False)
df = pd.read_csv("C:/GIT/IOT LAB/test.csv")
humidity_data = df["Relative_humidity_room"].values.tolist()
temperature_data = df["Indoor_temperature_room"].dropna().values.tolist()

n_steps = 3
n_features = 2

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

    humi_seq_test = []
    temp_seq_test = []
    count = 0

    while count < len(humidity_data):
        random_idx = random.randint(0, len(humidity_data) - 3 - 1)
        humidity = humidity_data[random_idx]
        temperature = temperature_data[random_idx]

        humi_seq_test.append(humidity)
        temp_seq_test.append(temperature)

        count += 1

        telemetry_data = {
            "humidity": round(float(humidity), 4),
            "temperature": round(float(temperature), 4)
        }

        if len(humi_seq_test) >= n_steps and count % 3 == 0:
            humi_slice = humi_seq_test[-n_steps:]
            temp_slice = temp_seq_test[-n_steps:]

            x_input = np.vstack((humi_slice, temp_slice)).T
            x_input = x_input.reshape((1, n_steps, n_features))

            predicted_value = model.predict(x_input, verbose=0)[0]
            telemetry_data["predicted_humidity"] = round(float(predicted_value[0]), 4)
            telemetry_data["predicted_temperature"] = round(float(predicted_value[1]), 4)

        client.publish('v1/devices/me/telemetry', json.dumps(telemetry_data), qos=1)
        print(f"[{device_info['username']}] Published: {telemetry_data}")

        time.sleep(1)

threads = []
for device in DEVICES:
    t = threading.Thread(target=publish_data, args=(device,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
