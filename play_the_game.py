import cv2
import mss
import numpy as np
import time
from collections import deque
from tensorflow.keras.models import load_model
from pynput.keyboard import Controller, Key # Import the Controller

# --- Keyboard Controller Setup ---
keyboard = Controller()

# Map the model's output names to pynput Key objects
# This is crucial for simulating the correct key presses.
KEY_MAP = {
    'UP': Key.up,
    'DOWN': Key.down,
    'LEFT': Key.left,
    'RIGHT': Key.right,
    'JUMP': Key.space,
    'SHOOT': 'f',
    'DASH': 'd',
}
ACTIONS = list(KEY_MAP.keys())

# --- Configuration (same as before) ---
IMG_HEIGHT, IMG_WIDTH = 72, 128
SEQUENCE_LENGTH = 10
CAPTURE_REGION = {'top': 289, 'left': 3, 'width': 716, 'height': 401}

# --- Load Models (same as before) ---
print("Loading trained models...")
try:
    encoder = load_model('cuphead_encoder.keras')
    brain = load_model('cuphead_brain.keras')
    print("✅ Models loaded successfully.")
except Exception as e:
    print(f"❌ Error loading models: {e}")
    exit()

# --- Initialize Agent State ---
latent_vector_sequence = deque(maxlen=SEQUENCE_LENGTH)
# NEW: Keep track of which keys the AI is currently holding down
keys_currently_pressed = set()

print("\n--- STARTING AI GAMEPLAY ---")
print("Click on the Cuphead game window NOW.")
print("The AI will take control in 5 seconds...")
print("To stop the AI, click the 'Live View' window and press 'q'.")
time.sleep(5)

# --- Main Agent Loop ---
with mss.mss() as sct:
    while True:
        # 1. See: Grab and process the screen
        screen_raw = sct.grab(CAPTURE_REGION)
        img = np.array(screen_raw)
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        frame = cv2.resize(frame, (IMG_WIDTH, IMG_HEIGHT))
        frame = frame / 255.0
        frame_reshaped = frame.reshape(1, IMG_HEIGHT, IMG_WIDTH, 1)

        # 2. Think: Get prediction from models
        latent_vector = encoder.predict(frame_reshaped, verbose=0)
        latent_vector_sequence.append(latent_vector)

        predicted_actions_set = set()
        if len(latent_vector_sequence) == SEQUENCE_LENGTH:
            sequence_input = np.array(list(latent_vector_sequence)).reshape(1, SEQUENCE_LENGTH, -1)
            probabilities = brain.predict(sequence_input, verbose=0)[0]
            
            for i, prob in enumerate(probabilities):
                if prob > 0.5:
                    predicted_actions_set.add(ACTIONS[i])

        # 3. Act: Press and release keys to match the prediction
        # Find keys that need to be released
        keys_to_release = keys_currently_pressed - predicted_actions_set
        for key_name in keys_to_release:
            key_to_press = KEY_MAP[key_name]
            keyboard.release(key_to_press)
            # print(f"Released: {key_name}")

        # Find keys that need to be pressed
        keys_to_press_new = predicted_actions_set - keys_currently_pressed
        for key_name in keys_to_press_new:
            key_to_press = KEY_MAP[key_name]
            keyboard.press(key_to_press)
            # print(f"Pressed: {key_name}")

        # Update the state of currently pressed keys
        keys_currently_pressed = predicted_actions_set
        
        # 4. Visualize (same as before)
        display_frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        # ... [visualization code is the same] ...
        cv2.rectangle(display_frame, (5, 5), (200, 30 + (len(ACTIONS) * 25)), (0, 0, 0), -1)
        if not predicted_actions_set:
            cv2.putText(display_frame, "IDLE", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
        else:
            for i, action in enumerate(sorted(list(predicted_actions_set))):
                cv2.putText(display_frame, action, (15, 30 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow("Cuphead AI - Live View (Press 'q' to quit)", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            # IMPORTANT: Release all keys before quitting!
            for key_name in keys_currently_pressed:
                keyboard.release(KEY_MAP[key_name])
            break

cv2.destroyAllWindows()
print("AI stopped.")