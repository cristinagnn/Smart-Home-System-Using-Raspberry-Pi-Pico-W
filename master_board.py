import network
import utime
import json
from umqtt.simple import MQTTClient
from machine import Pin
from mfrc522 import MFRC522
from time import localtime

# Load configuration for Wi-Fi connection 
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
ssid = config['ssid']
password = config['password']
broker = config['broker_ip']

# Those are the topics requred for communication between boards
client_id = 'pico_master'
topic_ac_control = b'ac_control'
topic_heating_control = b'heating_control'
topic_temperature = b'room_temperature'
topic_heating_manual_temp = b'heating_manual_temp'
topic_mode = b'control_mode'

# Determine the current season based on the current month
def get_current_season():
    month = localtime()[1]
    if month in [9, 10, 11, 12, 1, 2]:
        return 'winter'
    else:
        return 'summer'

current_season = get_current_season()

current_temperature = 0
mode = 'automatic'
manual_temperature = 0

# Initialize the MFRC522 object from the library
spi_id = 0
sck = 18   # GP18 for SPI0 SCK
mosi = 19  # GP19 for SPI0 MOSI
miso = 16  # GP16 for SPI0 MISO
cs = 17    # GP17 for Chip Select 
rst = 22   # GPIO22 for Reset 
button_pin = 28  # GP28 for button input
reader = MFRC522(spi_id=spi_id, sck=sck, mosi=mosi, miso=miso, cs=cs, rst=rst)

# Load user data from json file in order to not lose them at every run
def load_users_from_file():
    try:
        with open('users_card_id.json', 'r') as f:
            users_card_id = json.load(f)
            users_card_id = {int(k): v for k, v in users_card_id.items()}  # Convert keys back to int
            print("Loaded users from file.")
            return users_card_id
    except OSError:
        print("No users file found, starting with an empty dictionary.")
    except json.JSONDecodeError:
        print("Failed to decode JSON, starting with an empty dictionary.")
    return {}

def add_new_user(card, users_card_id):
    response = input("Do you want to add the user? (yes/no): ").strip().lower()
    if response == 'yes':
        save_users_to_file(users_card_id)
        print(f"Added new user {card} with temperatures: Winter {winter_temp}, Summer {summer_temp}")

def delete_user(card, users_card_id):
    if card in users_card_id:
        del users_card_id[card]
        save_users_to_file(users_card_id)
        print(f"Deleted user {card}.")
    else:
        print(f"User {card} not found.")

def clear_all_users(users_card_id):
    users_card_id.clear()
    save_users_to_file(users_card_id)
    print("All users have been deleted.")

def save_users_to_file(users_card_id):
    try:
        with open('users_card_id.json', 'w') as f:
            json.dump({str(k): v for k, v in users_card_id.items()}, f)  # Convert keys to str
            json.dump({str(k): v for k, v in users_card_id.items()}, f)
            print("User data saved to file.")
    except OSError as e:
        print(f"Failed to save user data to file: {e}")




users_card_id = load_users_from_file()
current_user = None
last_interrupt_time = 0
debounce_time = 200
button_pressed = False

# Wi-Fi connection
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print('Connecting to Wi-Fi...')
        utime.sleep(1)
    print('Connected to Wi-Fi:', wlan.ifconfig())
    return wlan.isconnected()

# Handle incoming MQTT messages
def message_callback(topic, msg):
    global current_temperature, manual_temperature
    data = json.loads(msg)
    if topic == topic_temperature:
        # Receive room temperature from A/C board
        if 'room_temperature' in data:
            current_temperature = data['room_temperature']
            print(f"Current room temperature: {current_temperature:.2f} °C")
            check_temperature()
    # Receive manual temperature from heating board
    elif topic == topic_heating_manual_temp:
        if 'manual_temperature' in data:
            manual_temperature = data['manual_temperature']
            print(f"Received manual temperature: {manual_temperature:.2f} °C")
            check_temperature()

# Check the temperature and send commands to heating or cooling system
def check_temperature():
    global current_user, manual_temperature
    if current_user or mode == 'manual':
        if mode == 'manual':
            target_temp = manual_temperature
        else:
            user_prefs = users_card_id[current_user]
            target_temp = user_prefs['summer'] if current_season == 'summer' else user_prefs['winter']

        if current_season == 'summer' and current_temperature > target_temp:
            client.publish(topic_ac_control, json.dumps({'command': 'start_cooling'}))
            print('Sent start cooling command')
        elif current_season == 'winter' and current_temperature < target_temp:
            client.publish(topic_heating_control, json.dumps({'command': 'start_heating'}))
            print('Sent start heating command')
        elif current_season == 'summer' and current_temperature <= target_temp:
            client.publish(topic_ac_control, json.dumps({'command': 'stop_cooling'}))
            print('Sent stop cooling command')
        elif current_season == 'winter' and current_temperature >= target_temp:
            client.publish(topic_heating_control, json.dumps({'command': 'stop_heating'}))
            print('Sent stop heating command')

# Scan for RFID cards
def scan_rfid():
    global current_user
    reader.init()
    (stat, tag_type) = reader.request(reader.REQIDL)
    if stat == reader.OK:
        (stat, uid) = reader.SelectTagSN()
        if stat == reader.OK:
            card = int.from_bytes(bytes(uid), "little")
            if card in users_card_id:
                current_user = card
                print(f"User {card} identified with preferences: {users_card_id[card]}")
            else:
                print("Unknown user")
                add_new_user(card, users_card_id)
            print("CARD ID: " + str(card))

# Handle button press for mode switching
def button_handler(pin):
    global mode, last_interrupt_time, button_pressed
    current_time = utime.ticks_ms()
    if utime.ticks_diff(current_time, last_interrupt_time) > debounce_time:
        if not button_pressed:
            mode = 'manual' if mode == 'automatic' else 'automatic'
            print(f"Mode changed to: {mode}")
            client.publish(topic_mode, json.dumps({'mode': mode}))
            button_pressed = True
        else:
            button_pressed = False
        last_interrupt_time = current_time

# Set up the button with an interrupt on both rising and falling edges
def setup_button():
    button = Pin(button_pin, Pin.IN, Pin.PULL_DOWN)
    button.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_handler)

def main():
    global client
    
    if not connect_to_wifi():
        return
    
    client = MQTTClient(client_id, broker)
    client.set_callback(message_callback)
    
    try:
        client.connect()
        client.subscribe(topic_temperature)
        client.subscribe(topic_heating_manual_temp)
        print('Connected to MQTT broker and subscribed to topics')
    except Exception as e:
        print(f'Failed to connect to MQTT broker: {e}')
        return
    
    setup_button()
    
    print("Bring TAG closer...")
    last_scan_time = utime.ticks_ms()
    scan_interval = 1000  
    while True:
        client.check_msg()
        
        current_time = utime.ticks_ms()
        if utime.ticks_diff(current_time, last_scan_time) >= scan_interval:
            scan_rfid()
            last_scan_time = current_time
        
        check_temperature()
        utime.sleep_ms(500)

if __name__ == "__main__":
    main()

