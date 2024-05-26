import network
import utime
import json
from umqtt.simple import MQTTClient
from machine import Pin
from mfrc522 import MFRC522

# Load configuration
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
ssid = config['ssid']
password = config['password']
broker = config['broker_ip']

client_id = 'pico_master'
topic_ac_control = b'ac_control'
topic_heating_control = b'heating_control'
topic_temperature = b'room_temperature'

current_season = 'winter'  # Change based on actual season
current_temperature = 0

# Initialize the MFRC522 object
spi_id = 0
sck = 18   # GP18 for SPI0 SCK
mosi = 19  # GP19 for SPI0 MOSI
miso = 16  # GP16 for SPI0 MISO
cs = 17    # GP17 for Chip Select (you can choose any GPIO)
rst = 22   # GPIO22 for Reset (you can choose any GPIO)
reader = MFRC522(spi_id=spi_id, sck=sck, mosi=mosi, miso=miso, cs=cs, rst=rst)

# Load user data from file
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

users_card_id = load_users_from_file()
current_user = None

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
    global current_temperature
    data = json.loads(msg)
    if topic == topic_temperature:
        if 'room_temperature' in data:
            current_temperature = data['room_temperature']
            print(f"Current room temperature: {current_temperature:.2f} °C")
            check_temperature()

def check_temperature():
    global current_user
    if current_user:
        user_prefs = users_card_id[current_user]
        if current_season == 'summer' and current_temperature > user_prefs['summer']:
            client.publish(topic_ac_control, json.dumps({'command': 'start_cooling'}))
            print('Sent start cooling command')
        elif current_season == 'winter' and current_temperature < user_prefs['winter']:
            client.publish(topic_heating_control, json.dumps({'command': 'start_heating'}))
            print('Sent start heating command')
        elif current_season == 'summer' and current_temperature <= user_prefs['summer']:
            client.publish(topic_ac_control, json.dumps({'command': 'stop_cooling'}))
            print('Sent stop cooling command')
        elif current_season == 'winter' and current_temperature >= user_prefs['winter']:
            client.publish(topic_heating_control, json.dumps({'command': 'stop_heating'}))
            print('Sent stop heating command')

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

def main():
    global client
    print(f"SSID: {ssid}, Password: {password}, Broker: {broker}")
    
    if not connect_to_wifi():
        return
    
    client = MQTTClient(client_id, broker)
    client.set_callback(message_callback)
    
    try:
        client.connect()
        client.subscribe(topic_temperature)
        print('Connected to MQTT broker and subscribed to topics')
    except Exception as e:
        print(f'Failed to connect to MQTT broker: {e}')
        return

    last_scan_time = utime.ticks_ms()
    scan_interval = 100  # Scan RFID every 10 seconds
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

