# import paho.mqtt.client as mqttclient
# import time
# import json
# import threading

# BROKER_ADDRESS = "app.coreiot.io"
# PORT = 1883

# # Declare device credentials for each device
# DEVICES = [
#     {"client_id": "NAME", "username": "iot_device1", "token": "PASS"},
#     {"client_id": "NAME", "username": "iot_device2", "token": "PASS"},
#     {"client_id": "NAME", "username": "iot_device3", "token": "PASS"},
# ]

# def connected(client, userdata, flags, rc):
#     if rc == 0:
#         print(f"[{userdata['username']}] Connected successfully!")
#         client.subscribe("v1/devices/me/rpc/request/+")
#     else:
#         print(f"[{userdata['username']}] Connection failed! (rc={rc})")

# def subscribed(client, userdata, mid, granted_qos):
#     print(f"[{userdata['username']}] Subscribed successfully!")

# def recv_message(client, userdata, message):
#     payload = message.payload.decode("utf-8")
#     print(f"[{userdata['username']}] Received: {payload}")
#     try:
#         jsonobj = json.loads(payload)
#         if jsonobj.get('method') == "setValue":
#             response = {'value': jsonobj.get('params', True)}
#             client.publish('v1/devices/me/attributes', json.dumps(response), qos=1)
#     except Exception as e:
#         print(f"[{userdata['username']}] Error processing message: {e}")

# def publish_data(device_info):
#     # Create a client with a unique client ID for each device
#     client = mqttclient.Client(device_info["client_id"])
#     client.username_pw_set(device_info["username"], device_info["token"])

#     # Set the user_data so that callbacks can identify which device is being used
#     client.user_data_set(device_info)

#     # Assign callbacks
#     client.on_connect = connected
#     client.on_subscribe = subscribed
#     client.on_message = recv_message

#     # Connect to the broker
#     client.connect(BROKER_ADDRESS, PORT)
#     client.loop_start()

#     # Simulate sensor values
#     temp = 26
#     humi = 35
#     light_intensity = 44

#     # HCMUT
#     if device_info["username"] == "iot_device1":
#         long = 106.65789107082472
#         lat = 10.772175109674038
#     elif device_info["username"] == "iot_device2":
#         long = 106.75789107082472
#         lat = 10.872175109674038
#     elif device_info["username"] == "iot_device3":
#         long = 106.85789107082472
#         lat = 10.972175109674038

#     while True:
#         collect_data = {
#             "temperature": temp,
#             "humidity": humi,
#             "light": light_intensity,
#             "long": long,
#             "lat": lat
#         }
#         temp += 1
#         humi += 1
#         light_intensity += 1

#         # Publish telemetry data
#         client.publish('v1/devices/me/telemetry', json.dumps(collect_data), qos=1)
#         print(f"[{device_info['username']}] Published: {collect_data}")
#         time.sleep(5)

# # Create and start a thread for each device
# threads = []
# for device in DEVICES:
#     t = threading.Thread(target=publish_data, args=(device,))
#     t.start()
#     threads.append(t)

# # Keep the main thread running
# for t in threads:
#     t.join()


import paho.mqtt.client as mqtt
import time
import json
import threading

BROKER_ADDRESS = "app.coreiot.io"
PORT = 1883

DEVICES = [
    {"client_id": "NAME", "username": "iot_device1", "token": "PASS"},
]

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{userdata['username']}] Connected successfully!")
        client.subscribe("v1/devices/me/rpc/request/+")
    else:
        print(f"[{userdata['username']}] Connection failed! (rc={rc})")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"[{userdata['username']}] Subscribed successfully!")

def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    print(f"[{userdata['username']}] Received: {payload}")
    try:
        data = json.loads(payload)
        if data.get('method') == "setValue":
            response = {'value': data.get('params', True)}
            client.publish('v1/devices/me/attributes', json.dumps(response), qos=1)
    except Exception as e:
        print(f"[{userdata['username']}] Error processing message: {e}")

def publish_data(device_info):
    client = mqtt.Client(client_id=device_info["client_id"])
    client.username_pw_set(device_info["username"], device_info["token"])
    client.user_data_set(device_info)

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    client.connect(BROKER_ADDRESS, PORT)
    client.loop_start()

    temperature = 39
    humidity = 59

    # if device_info["username"] == "iot_device1":
    #     longitude = 106.65789107082472
    #     latitude = 10.772175109674038

    while True:
        telemetry = {
            "temperature": temperature,
            "humidity": humidity,
            # "longitude": longitude,
            # "latitude": latitude
        }

        # if humidity >= 40:
        #     created_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        #     telemetry["createdTime"] = created_time
        #     telemetry["originator"] = device_info["username"]
        #     telemetry["type"] = "Critical"
        #     telemetry["severity"] = "Critical"
        #     telemetry["status"] = "Not good"

        client.publish('v1/devices/me/telemetry', json.dumps(telemetry), qos=1)
        print(f"[{device_info['username']}] Published telemetry: {telemetry}")

        temperature += 1
        humidity += 1

        time.sleep(5)

if __name__ == '__main__':
    threads = []
    for device in DEVICES:
        t = threading.Thread(target=publish_data, args=(device,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
