import network
import utime
import json
from machine import Pin
from picozero import LED
from umqtt.simple import MQTTClient

# Load configuration from file
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
ssid = config['ssid']
password = config['password']
broker = config['broker_ip']

client_id = 'heating_system_board'
topic_control = b'heating_control'

green = LED(15)
red = LED(14)

def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print('Connecting to Wi-Fi...')
        utime.sleep(1)
    print('Connected to Wi-Fi:', wlan.ifconfig())
    return wlan.isconnected()

def message_callback(topic, msg):
    data = json.loads(msg)
    if 'command' in data:
        command = data['command']
        if command == 'start_heating':
            print('Received start heating command')
            red.off()
            green.on()
        elif command == 'stop_heating':
            print('Received stop heating command')
            red.on()
            green.off()

def main():
    global client
    client = MQTTClient(client_id, broker)
    client.set_callback(message_callback)
    
    if not connect_to_wifi():
        return
    
    try:
        client.connect()
        client.subscribe(topic_control)
        print('Connected to MQTT broker and subscribed to topic')
    except Exception as e:
        print(f'Failed to connect to MQTT broker: {e}')
        return

    while True:
        client.check_msg()
        utime.sleep_ms(100)

if __name__ == "__main__":
    main()

