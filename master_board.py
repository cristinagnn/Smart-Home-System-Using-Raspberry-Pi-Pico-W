from mfrc522 import MFRC522
import utime
from machine import Pin
import json
from umqtt.simple import MQTTClient

# Load configuration from file
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()

# Wi-Fi configuration
ssid = config['ssid']
password = config['password']
broker = config['broker_ip']

# Initialize the MFRC522 object
spi_id = 0
sck = 18
mosi = 19
miso = 16
cs = 17
rst = 22
button_pin = 28
reader = MFRC522(spi_id=spi_id, sck=sck, mosi=mosi, miso=miso, cs=cs, rst=rst)

# MQTT configuration
client_id = 'pico_master'
topic_control = b'ac_control'
topic_temperature = b'room_temperature'

# Initialize mode and debounce variables
mode = 'automatic'
last_interrupt_time = 0
debounce_time = 200
button_pressed = False

# Load user data from file
def load_users_from_file():
    try:
        with open('users_card_id.json', 'r') as f:
            users_card_id = json.load(f)
            users_card_id = {int(k): v for k, v in users_card_id.items()}
            print("Loaded users from file.")
            return users_card_id
    except OSError:
        print("No users file found, starting with an empty dictionary.")
    except json.JSONDecodeError:
        print("Failed to decode JSON, starting with an empty dictionary.")
    return {}

# Interrupt handler for button press
def button_handler(pin):
    global mode, last_interrupt_time, button_pressed
    current_time = utime.ticks_ms()
    if utime.ticks_diff(current_time, last_interrupt_time) > debounce_time:
        if not button_pressed:
            mode = 'manual' if mode == 'automatic' else 'automatic'
            print(f"Mode changed to: {mode}")
            button_pressed = True
        else:
            button_pressed = False
        last_interrupt_time = current_time

# Set up the button with an interrupt on both rising and falling edges
def setup_button():
    button = Pin(button_pin, Pin.IN, Pin.PULL_DOWN)
    button.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_handler)

# Save user data to file
def save_users_to_file(users_card_id):
    try:
        with open('users_card_id.json', 'w') as f:
            json.dump({str(k): v for k, v in users_card_id.items()}, f)
            print("User data saved to file.")
    except OSError as e:
        print(f"Failed to save user data to file: {e}")

# Add a new user
def add_new_user(card, users_card_id):
    response = input("Do you want to add the user? (yes/no): ").strip().lower()
    if response == 'yes':
        winter_temp = int(input("Enter preferred winter temperature: "))
        summer_temp = int(input("Enter preferred summer temperature: "))
        users_card_id[card] = {'winter': winter_temp, 'summer': summer_temp}
        save_users_to_file(users_card_id)
        print(f"Added new user {card} with temperatures: Winter {winter_temp}, Summer {summer_temp}")

# Callback function to handle incoming messages
def message_callback(topic, msg):
    print(msg)
    data = json.loads(msg)
    if 'room_temperature' in data:
        print(f"Current room temperature: {data['room_temperature']} °C")

# Main function
def main():
    global mode
    users_card_id = load_users_from_file()
    setup_button()

    client = MQTTClient(client_id, broker)
    client.set_callback(message_callback)
    client.connect()
    client.subscribe(topic_temperature)
    print('Connected to MQTT broker and subscribed to topic')

    print("Bring TAG closer...")
    while True:
        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                card = int.from_bytes(bytes(uid), "little")
                if card in users_card_id:
                    print(f"Welcome back, user {card}.")
                    temperatures = users_card_id[card]
                    temp = temperatures['winter'] if mode == 'winter' else temperatures['summer']
                    client.publish(topic_control, json.dumps({'card': card, 'temperature': temp}))
                    print(f"Published temperature {temp} for user {card}.")
                else:
                    print("Unknown user")
                    add_new_user(card, users_card_id)
                print("CARD ID: " + str(card))
        utime.sleep_ms(500)
    client.disconnect()

if __name__ == "__main__":
    main()

