import time
from pynput import mouse

print("Move your mouse to the TOP-LEFT corner of the game window and wait...")
time.sleep(5)  # Gives you 5 seconds to position the mouse

def on_move(x, y):
    global top_left_x, top_left_y
    top_left_x, top_left_y = int(x), int(y)
    # Stop the listener after the first move event
    return False

with mouse.Listener(on_move=on_move) as listener:
    listener.join()

print(f"Captured Top-Left: (x={top_left_x}, y={top_left_y})")

print("\nNow, move your mouse to the BOTTOM-RIGHT corner of the game window and wait...")
time.sleep(5)

def on_move(x, y):
    global bottom_right_x, bottom_right_y
    bottom_right_x, bottom_right_y = int(x), int(y)
    return False

with mouse.Listener(on_move=on_move) as listener:
    listener.join()
    
print(f"Captured Bottom-Right: (x={bottom_right_x}, y={bottom_right_y})")

# Calculate the region for the config
width = bottom_right_x - top_left_x
height = bottom_right_y - top_left_y

print("\n--- Paste this into app/main.py ---")
print(f"self.CAPTURE_REGION = {{'top': {top_left_y}, 'left': {top_left_x}, 'width': {width}, 'height': {height}}}")