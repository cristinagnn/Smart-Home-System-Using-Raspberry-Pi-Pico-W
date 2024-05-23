from machine import ADC, Pin
from picozero import LED
import utime
from umqtt.simple import MQTTClient
import json
# ASTA ESTE AERUL CONDITIONAT

# Load configuration from file
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()

# Wi-Fi configuration
ssid = config['ssid']
password = config['password']
broker = config['broker_ip']

# MQTT Configuration
client_id = 'pico_ac_board'
topic_control = b'ac_control'
topic_temperature = b'room_temperature'

# Initialize pins for LEDs
green = LED(15)
red = LED(14)

# Initialize ADC for the potentiometer
potentiometer = ADC(Pin(26))  

# Moving average filter variables
num_samples = 10
adc_buffer = [0] * num_samples
buffer_index = 0

# Exponential moving average variables
alpha = 0.3 
ema_value = 0

# Function to handle incoming messages
def message_callback(topic, msg):
    print(msg)
    data = json.loads(msg)
    temperature = data['temperature']
    print(f"Received temperature {temperature} celsius")
    
    if temperature > 26:
        green.on()
        red.off()
    else:
        red.on()
        green.off()

def read_potentiometer():
    global buffer_index, ema_value
    # Read the ADC value
    adc_value = potentiometer.read_u16()
    
    # Update the buffer with the new reading
    adc_buffer[buffer_index] = adc_value
    buffer_index = (buffer_index + 1) % num_samples
    
    # Calculate the moving average of the buffer
    moving_average = sum(adc_buffer) / num_samples
    
    # Update the EMA value
    ema_value = (alpha * moving_average) + ((1 - alpha) * ema_value)
    
    return ema_value

def map_value(value, from_low, from_high, to_low, to_high):
    # Helper function to map one range of values to another
    return to_low + ((value - from_low) / (from_high - from_low)) * (to_high - to_low)

def main():
    client = MQTTClient(client_id, broker)
    client.set_callback(message_callback)
    client.connect()
    client.subscribe(topic_control)
    print('Connected to MQTT broker and subscribed to topic')
    
    while True:
        client.wait_msg()
        # Read the potentiometer and get the filtered value
        filtered_adc_value = read_potentiometer()
        
        # Assuming the range of the ADC is from 0 to 65535
        min_adc = 0
        max_adc = 65535  # Adjust this based on actual observed values
        temperature = map_value(filtered_adc_value, min_adc, max_adc, 15, 40)
        
        client.publish(topic_temperature, json.dumps({'room_temperature': temperature}))
        # Print the set temperature
        print(f"Set temperature: {temperature:.2f} °C")

        # Sleep for a short while to avoid flooding the output
        utime.sleep_ms(100)

# Call the main function
if __name__ == "__main__":
    main()

