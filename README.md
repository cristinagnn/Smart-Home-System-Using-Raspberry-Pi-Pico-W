# Smart-Home-System-Using-Raspberry-Pi-Pico-W

**Introduction**

This project develops a Smart-Home system capable of automatically and manually controlling heating and cooling systems (heating system and air conditioning) based on predefined parameters. The system operates in two modes: automatic and manual.

**How It Works**

**Automatic Mode**
In this mode, the system uses an RFID card to detect user presence. When a user leaves home and scans the card at the door, the system deactivates the boiler or air conditioning to save energy. Upon return, scanning the card reactivates the heating or cooling system according to the season and the user’s preferred temperature, adjusting the indoor temperature accordingly.

**Manual Mode**
Users can manually set the desired room temperature, independent of predefined preferences and outside temperature, allowing quick and personalized adjustments.

**General Description**

The system uses three Raspberry Pi Pico W boards. The master unit manages user data via an RFID module and controls heating and cooling preferences. The other two boards manage the boiler and air conditioning, receiving wireless instructions from the master. The system includes manual overrides and status indicators.

**Block diagram**

![diagrama_bloc_finala drawio](https://github.com/cristinagnn/Smart-Home-System-Using-Raspberry-Pi-Pico-W/assets/60398307/f6e8c85f-d1e0-4470-9bea-64d038809f60)


**Hardware Design**

**Components**
- 3 x Raspberry Pi Pico W
- RFID RC522 module
- Potentiometers for temperature settings
- Button for mode switching
- LEDs for system status

**Electrical schematic**


![proiect_cu_label](https://github.com/cristinagnn/Smart-Home-System-Using-Raspberry-Pi-Pico-W/assets/60398307/b292a421-699e-4cec-937a-cd7132d23ffa)

