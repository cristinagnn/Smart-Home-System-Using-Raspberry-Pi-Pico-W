from mfrc522 import MFRC522
import utime
from machine import Pin
import json

# Define the pins based on the Raspberry Pi Pico W's pinout
spi_id = 0
sck = 18   # GP18 for SPI0 SCK
mosi = 19  # GP19 for SPI0 MOSI
miso = 16  # GP16 for SPI0 MISO
cs = 17    # GP17 for Chip Select (you can choose any GPIO)
rst = 22   # GPIO22 for Reset (you can choose any GPIO)
button_pin = 28  # GP28 for button input

# Initialize the MFRC522 object
reader = MFRC522(spi_id=spi_id, sck=sck, mosi=mosi, miso=miso, cs=cs, rst=rst)

# Initialize mode and debounce variables
mode = 'automatic'
last_interrupt_time = 0  # To keep track of the last interrupt time
debounce_time = 200  # Debounce time in milliseconds
button_pressed = False  # Track the button state

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

# Interrupt handler for button press
def button_handler(pin):
    global mode, last_interrupt_time, button_pressed
    current_time = utime.ticks_ms()
    
    # Debouncing
    if utime.ticks_diff(current_time, last_interrupt_time) > debounce_time:
        # Toggle mode only if button was previously not pressed
        if not button_pressed:
            if mode == 'automatic':
                mode = 'manual'
            else:
                mode = 'automatic'
            print(f"Mode changed to: {mode}")
            button_pressed = True
        else:
            # Reset button_pressed when button is released
            button_pressed = False
        last_interrupt_time = current_time

# Set up the button with an interrupt on both rising and falling edges
def setup_button():
    button = Pin(button_pin, Pin.IN, Pin.PULL_DOWN)
    button.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_handler)

def save_users_to_file(users_card_id):
    try:
        with open('users_card_id.json', 'w') as f:
            json.dump({str(k): v for k, v in users_card_id.items()}, f)  # Convert keys to str
            print("User data saved to file.")
    except OSError as e:
        print(f"Failed to save user data to file: {e}")

def add_new_user(card, users_card_id):
    response = input("Do you want to add the user? (yes/no): ").strip().lower()
    if response == 'yes':
        winter_temp = int(input("Enter preferred winter temperature: "))
        summer_temp = int(input("Enter preferred summer temperature: "))
        users_card_id[card] = {'winter': winter_temp, 'summer': summer_temp}
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

def main():
    global mode
    users_card_id = load_users_from_file()
    setup_button()
    #delete_user(1494033744, users_card_id)
    
    print("Bring TAG closer...")
    print("")
    
    while True:
        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                card = int.from_bytes(bytes(uid), "little")
                if card in users_card_id:
                    # Perform actions for known user
                    print(f"Welcome back, user {card}.")
                    # Add your temperature control logic here
                else:
                    print("Unknown user")
                    add_new_user(card, users_card_id)
                print("CARD ID: " + str(card))
        
        utime.sleep_ms(500)

if __name__ == "__main__":
    main()
