import paho.mqtt.client as mqtt
import time, json, threading
import random

BROKER_ADDRESS = "app.coreiot.io"
PORT = 1883

DEVICES = [
    { "client_id": "IOT_DEVICE_1",
      "token":     "Token" },
]

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{client._client_id.decode()}] Connected successfully!")
        client.subscribe("v1/devices/me/rpc/request/+")
    else:
        print(f"[{client._client_id.decode()}] Connection failed! rc={rc}")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"[{client._client_id.decode()}] Subscribed successfully!")

def on_message(client, userdata, message):
    print(f"[{client._client_id.decode()}] Received: {message.payload.decode()}")

def publish_data(device):
    client = mqtt.Client(client_id=device["client_id"])
    # only token as username
    client.username_pw_set(device["token"])
    client.on_connect, client.on_subscribe, client.on_message = on_connect, on_subscribe, on_message
    client.connect(BROKER_ADDRESS, PORT)
    client.loop_start()

    temp = random.randint(25, 35)
    hum = random.randint(45, 65)
    predicted_temp = random.randint(22, 32)
    predicted_humid = random.randint(42, 62)
    light = random.randint(0,500)
    while True:
        telemetry = {"temperature": temp, "humidity": hum, "predicted_temp": predicted_temp, "predicted_humid": predicted_humid, "light": light}
        client.publish('v1/devices/me/telemetry', json.dumps(telemetry), qos=1)
        print(f"[{device['client_id']}] Published: {telemetry}")
        # temp += 1; hum += 1
        # predicted_temp +=1; predicted_humid +=1
        temp = random.randint(25, 35)
        hum = random.randint(45, 65)
        predicted_temp = random.randint(22, 32)
        predicted_humid = random.randint(42, 62)
        light = random.randint(0,500)
        time.sleep(5)

if __name__ == '__main__':
    threads = []
    for d in DEVICES:
        t = threading.Thread(target=publish_data, args=(d,))
        t.start()
        threads.append(t)
    for t in threads: t.join()
