from machine import ADC, Pin
import utime

# Initialize ADC for the potentiometer
potentiometer = ADC(Pin(26))  # GP26 corresponds to ADC0

# Moving average filter variables
num_samples = 10  # Reduce the number of samples for more responsiveness
adc_buffer = [0] * num_samples
buffer_index = 0

# Exponential moving average variables
alpha = 0.3  # Increase the smoothing factor for more responsiveness
ema_value = 0

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

while True:
    # Read the potentiometer and get the filtered value
    filtered_adc_value = read_potentiometer()
    
    # Assuming the range of the ADC is from 0 to 65535
    min_adc = 0
    max_adc = 65535  # Adjust this based on actual observed values
    temperature = map_value(filtered_adc_value, min_adc, max_adc, 15, 40)
    
    # Print the set temperature
    print(f"Set temperature: {temperature:.2f} °C")
    
    # Sleep for a short while to avoid flooding the output
    utime.sleep_ms(100)