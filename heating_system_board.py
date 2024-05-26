import network
import utime
import json
from machine import ADC, Pin
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
topic_manual_temp = b'heating_manual_temp'
topic_mode = b'control_mode'


green = LED(15)
red = LED(14)
potentiometer = ADC(Pin(26))

# default mode 
mode = 'automatic'

def read_potentiometer():
    adc_value = potentiometer.read_u16()
    min_adc = 0
    max_adc = 65535
    temperature = 15 + (adc_value / max_adc) * 25  # Map ADC value to temperature range (15-40)
    print(temperature)
    return round(temperature, 2)  # Return the temperature rounded to 2 decimal places


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
    global mode
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
    elif 'mode' in data:
        mode = data['mode']
        print(f"Mode set to: {mode}")

def publish_manual_temperature(client):
    temperature = read_potentiometer()
    client.publish(topic_manual_temp, json.dumps({'manual_temperature': temperature}))
    print(f"Sent manual temperature: {temperature:.2f} C")

def main():
    red.on()
    green.off()
    
    global client
    client = MQTTClient(client_id, broker)
    client.set_callback(message_callback)
    
    if not connect_to_wifi():
        return
    
    try:
        client.connect()
        client.subscribe(topic_control)
        client.subscribe(topic_mode)
        print('Connected to MQTT broker and subscribed to topic')
    except Exception as e:
        print(f'Failed to connect to MQTT broker: {e}')
        return

    manual_temp_interval = 5000  # 5 seconds
    last_manual_temp_time = utime.ticks_ms()
    
    while True:
        client.check_msg()
        
        current_time = utime.ticks_ms()
        if mode == 'manual' and utime.ticks_diff(current_time, last_manual_temp_time) >= manual_temp_interval:
            publish_manual_temperature(client)
            last_manual_temp_time = current_time
        
        utime.sleep_ms(100)

if __name__ == "__main__":
    main()

