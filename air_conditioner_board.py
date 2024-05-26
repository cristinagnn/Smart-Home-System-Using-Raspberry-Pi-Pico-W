import network
from machine import ADC, Pin
from picozero import LED
import utime
import json
from umqtt.simple import MQTTClient

# Load configuration from file
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
ssid = config['ssid']
password = config['password']
broker = config['broker_ip']

client_id = 'pico_ac_board'
topic_control = b'ac_control'
topic_temperature = b'room_temperature'

green = LED(15)
red = LED(14)
potentiometer = ADC(Pin(26))

num_samples = 10
adc_buffer = [0] * num_samples
buffer_index = 0

alpha = 0.3
ema_value = 0

def read_potentiometer():
    global buffer_index, ema_value
    adc_value = potentiometer.read_u16()
    adc_buffer[buffer_index] = adc_value
    buffer_index = (buffer_index + 1) % num_samples
    moving_average = sum(adc_buffer) / num_samples
    ema_value = (alpha * moving_average) + ((1 - alpha) * ema_value)
    return ema_value

def map_value(value, from_low, from_high, to_low, to_high):
    return to_low + ((value - from_low) / (from_high - from_low)) * (to_high - to_low)

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
        if command == 'start_cooling':
            print('Received start cooling command')
            green.on()
            red.off()
        elif command == 'stop_cooling':
            print('Received stop cooling command')
            green.off()
            red.on()
def main():
    red.on()
    green.off()
    
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
    
    last_publish_time = utime.ticks_ms()
    publish_interval = 5000  # Send temperature updates every 5 seconds
    
    while True:
        client.check_msg()
        
        filtered_adc_value = read_potentiometer()
        min_adc = 0
        max_adc = 65535
        temperature = map_value(filtered_adc_value, min_adc, max_adc, 15, 40)
        
        # Send current temperature at periodic interval of times
        current_time = utime.ticks_ms()
        if utime.ticks_diff(current_time, last_publish_time) >= publish_interval:
            client.publish(topic_temperature, json.dumps({'room_temperature': temperature}))
            print(f"Set temperature: {temperature:.2f} °C")
            last_publish_time = current_time

        utime.sleep_ms(100)

if __name__ == "__main__":
    main()

