#include <WiFi.h>
#include <Arduino_MQTT_Client.h>
#include <ThingsBoard.h>
#include "DHT20.h"
#include "Wire.h"
#include <ArduinoOTA.h>

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define LED_PIN 48
#define SDA_PIN GPIO_NUM_11
#define SCL_PIN GPIO_NUM_12

// Wi-Fi network credentials
constexpr char WIFI_SSID[] = "WIFI_NAME";
constexpr char WIFI_PASSWORD[] = "WIFI_PASSWORD";

// ThingsBoard server configuration
constexpr char TOKEN[] = "ACCESS_TOKEN";
constexpr char THINGSBOARD_SERVER[] = "app.coreiot.io";
constexpr uint16_t THINGSBOARD_PORT = 1883U;

// Maximum size for MQTT messages and the baud rate for serial debugging
constexpr uint32_t MAX_MESSAGE_SIZE = 1024U;
constexpr uint32_t SERIAL_DEBUG_BAUD = 115200U;

// Define attribute names used in communication with ThingsBoard
constexpr char BLINKING_INTERVAL_ATTR[] = "blinkingInterval";
constexpr char LED_MODE_ATTR[] = "ledMode";
constexpr char LED_STATE_ATTR[] = "ledState";

// Define the minimum and maximum blinking interval values (ms)
constexpr uint16_t BLINKING_INTERVAL_MS_MIN = 10U;
constexpr uint16_t BLINKING_INTERVAL_MS_MAX = 60000U;

// Global variables to hold the LED blinking interval, LED state, and mode
volatile uint16_t blinkingInterval = 1000U;
volatile bool attributesChanged = false;
volatile bool ledState = false;
volatile int ledMode = 0;

// Telemetry send interval for sensor data (ms)
constexpr int16_t telemetrySendInterval = 5000U;

// Shared attributes to subscribe to on ThingsBoard
constexpr std::array<const char *, 2U> SHARED_ATTRIBUTES_LIST = {LED_STATE_ATTR, BLINKING_INTERVAL_ATTR};

WiFiClient wifiClient;
Arduino_MQTT_Client mqttClient(wifiClient);
ThingsBoard tb(mqttClient, MAX_MESSAGE_SIZE);
DHT20 dht20;

// Variables to track previous send times
uint32_t previousDataSend = 0;
uint32_t previousStateChange = 0;

// Functions for FreeRTOS tasks
void wifiTask(void *pvParameters);
void thingsBoardTask(void *pvParameters);
void sensorTask(void *pvParameters);

struct SensorData
{
    float temperature;
    float humidity;
};

// Generate a FreeRTOS queue to hold sensor data messages
QueueHandle_t sensorDataQueue;

// RPC Callback
RPC_Response setLedSwitchState(const RPC_Data &data)
{
    Serial.println("Received Switch state via RPC");
    bool newState = data;
    Serial.printf("Switch state change: %d\n", newState);

    digitalWrite(LED_PIN, newState);
    ledState = newState;
    attributesChanged = true;

    return RPC_Response("setLedSwitchValue", newState);
}

// Generate an array of RPC callbacks and Register the "setLedSwitchValue" callback
const std::array<RPC_Callback, 1U> callbacks = {RPC_Callback{"setLedSwitchValue", setLedSwitchState}};

// Process shared Attributes
void processSharedAttributes(const Shared_Attribute_Data &data)
{
    for (auto it = data.begin(); it != data.end(); ++it)
    {
        const char *key = it->key().c_str();

        if (strcmp(key, BLINKING_INTERVAL_ATTR) == 0)
        {
            uint16_t new_interval = it->value().as<uint16_t>();
            if (new_interval >= BLINKING_INTERVAL_MS_MIN && new_interval <= BLINKING_INTERVAL_MS_MAX)
            {
                blinkingInterval = new_interval;
                Serial.printf("Blinking interval set to: %u\n", new_interval);
            }
        }
        else if (strcmp(key, LED_STATE_ATTR) == 0)
        {
            bool newLedState = it->value().as<bool>();
            digitalWrite(LED_PIN, newLedState);
            ledState = newLedState;
            Serial.printf("LED state set to: %d\n", newLedState);
        }
    }
    attributesChanged = true;
}

const Shared_Attribute_Callback attributes_callback(
    &processSharedAttributes,
    SHARED_ATTRIBUTES_LIST.cbegin(),
    SHARED_ATTRIBUTES_LIST.cend());

const Attribute_Request_Callback attribute_shared_request_callback(
    &processSharedAttributes,
    SHARED_ATTRIBUTES_LIST.cbegin(),
    SHARED_ATTRIBUTES_LIST.cend());

// Initialize the serial port, hardware pins, sensor, and tasks
void setup()
{
    Serial.begin(SERIAL_DEBUG_BAUD);

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    Wire.begin(SDA_PIN, SCL_PIN);
    dht20.begin();

    sensorDataQueue = xQueueCreate(5, sizeof(SensorData));
    if (sensorDataQueue == NULL)
        Serial.println("Failed to create sensorDataQueue!");

    xTaskCreate(wifiTask, "WiFiTask", 4096, NULL, 1, NULL);
    xTaskCreate(thingsBoardTask, "ThingsBoardTask", 8192, NULL, 1, NULL);
    xTaskCreate(sensorTask, "SensorTask", 4096, NULL, 1, NULL);
}

void loop()
{
}

// Wifi connection
void wifiTask(void *pvParameters)
{
    (void)pvParameters;
    while (1)
    {
        if (WiFi.status() != WL_CONNECTED)
        {
            Serial.println("[WiFiTask] Connecting to Wi-Fi...");
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

            while (WiFi.status() != WL_CONNECTED)
            {
                vTaskDelay(500 / portTICK_PERIOD_MS);
                Serial.print(".");
            }
            Serial.println("\n[WiFiTask] Wi-Fi connected!");
        }

        vTaskDelay(2000 / portTICK_PERIOD_MS);
    }
}

// Manage the connection to the ThingsBoard server and Handle data transmission
void thingsBoardTask(void *pvParameters)
{
    (void)pvParameters;

    while (1)
    {
        if (WiFi.status() == WL_CONNECTED)
        {
            if (!tb.connected())
            {
                Serial.printf("[ThingsBoardTask] Connecting to %s with the private token %s\n",
                              THINGSBOARD_SERVER, TOKEN);
                if (!tb.connect(THINGSBOARD_SERVER, TOKEN, THINGSBOARD_PORT))
                    Serial.println("[ThingsBoardTask] Failed to connect to ThingsBoard");
                else
                {
                    Serial.println("[ThingsBoardTask] Connected to ThingsBoard");

                    tb.sendAttributeData("macAddress", WiFi.macAddress().c_str());

                    Serial.println("[ThingsBoardTask] Subscribing for RPC...");
                    if (!tb.RPC_Subscribe(callbacks.cbegin(), callbacks.cend()))
                        Serial.println("[ThingsBoardTask] Failed to subscribe for RPC");

                    if (!tb.Shared_Attributes_Subscribe(attributes_callback))
                        Serial.println("[ThingsBoardTask] Failed to subscribe for shared attributes");

                    if (!tb.Shared_Attributes_Request(attribute_shared_request_callback))
                        Serial.println("[ThingsBoardTask] Failed to request shared attributes");
                }
            }

            if (tb.connected())
            {
                tb.loop();

                if (attributesChanged)
                {
                    attributesChanged = false;
                    tb.sendAttributeData(LED_STATE_ATTR, (bool)digitalRead(LED_PIN));
                }

                if (sensorDataQueue != NULL && uxQueueMessagesWaiting(sensorDataQueue) > 0)
                {
                    SensorData newData;
                    if (xQueueReceive(sensorDataQueue, &newData, 0) == pdTRUE)
                    {
                        tb.sendTelemetryData("temperature", newData.temperature);
                        tb.sendTelemetryData("humidity", newData.humidity);
                    }
                }
            }
        }

        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

// Handle sensor data reading and transmission
void sensorTask(void *pvParameters)
{
    (void)pvParameters;
    while (1)
    {
        if (WiFi.status() == WL_CONNECTED && tb.connected())
        {
            dht20.read();
            float temperature = dht20.getTemperature();
            float humidity = dht20.getHumidity();

            if (isnan(temperature) || isnan(humidity))
                Serial.println("[SensorTask] Failed to read from DHT20 sensor!");
            else
            {
                Serial.printf("[SensorTask] Temperature: T = %.2f °C, Humidity: H = %.2f %%\n", temperature, humidity);

                SensorData dataToSend;
                dataToSend.temperature = temperature;
                dataToSend.humidity = humidity;

                if (sensorDataQueue != NULL)
                    xQueueSend(sensorDataQueue, &dataToSend, 0);
            }

            tb.sendAttributeData("rssi", WiFi.RSSI());
            tb.sendAttributeData("channel", WiFi.channel());
            tb.sendAttributeData("bssid", WiFi.BSSIDstr().c_str());
            tb.sendAttributeData("localIp", WiFi.localIP().toString().c_str());
            tb.sendAttributeData("ssid", WiFi.SSID().c_str());
        }

        vTaskDelay(telemetrySendInterval / portTICK_PERIOD_MS);
    }
}
