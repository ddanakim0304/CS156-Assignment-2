import cv2
import mss
import numpy as np
import time
from collections import deque
from tensorflow.keras.models import load_model # Use the stable import path

# --- Configuration ---
# These MUST match the values from your Colab training notebook
IMG_HEIGHT = 72
IMG_WIDTH = 128
SEQUENCE_LENGTH = 10 # This was STACK_SIZE before, now it's for the RNN

# This MUST match the region you used for your recording sessions
CAPTURE_REGION = {'top': 289, 'left': 3, 'width': 716, 'height': 401}

ACTIONS = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'JUMP', 'SHOOT', 'DASH']

# --- Load the Trained Models ---
print("Loading trained models...")
try:
    # Make sure you've downloaded 'trained_models.zip' and unzipped these files
    encoder = load_model('cuphead_encoder.keras')
    brain = load_model('cuphead_brain.keras')
    print("✅ Models loaded successfully.")
except Exception as e:
    print(f"❌ Error loading models: {e}")
    print("Please make sure 'cuphead_encoder.keras' and 'cuphead_brain.keras' are in this directory.")
    exit()

# --- Initialize Agent State ---
# Use a deque to automatically manage the sequence of latent vectors
latent_vector_sequence = deque(maxlen=SEQUENCE_LENGTH)

print("\n--- Starting Live Agent ---")
print("Agent is now watching the screen.")
print("Press 'q' in the display window to quit.")

# --- Main Agent Loop ---
with mss.mss() as sct:
    while True:
        frame_start_time = time.perf_counter()

        # 1. Grab the screen
        screen_raw = sct.grab(CAPTURE_REGION)
        img = np.array(screen_raw)
        
        # 2. Pre-process the frame (same as in training)
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        frame = cv2.resize(frame, (IMG_WIDTH, IMG_HEIGHT))
        frame = frame / 255.0
        frame_reshaped = frame.reshape(1, IMG_HEIGHT, IMG_WIDTH, 1)

        # 3. Use the Encoder to get the current latent vector
        latent_vector = encoder.predict(frame_reshaped, verbose=0)
        
        # 4. Append the new vector to our sequence
        # The deque will automatically discard the oldest vector if it's full
        latent_vector_sequence.append(latent_vector)

        # 5. Predict actions ONLY if we have a full sequence
        predicted_actions = []
        if len(latent_vector_sequence) == SEQUENCE_LENGTH:
            # Convert the deque of arrays into a single 3D NumPy array
            # The shape should be (1, 10, num_features) which is what the RNN expects
            sequence_input = np.array(list(latent_vector_sequence)).reshape(1, SEQUENCE_LENGTH, -1)
            
            # Use the Brain to predict action probabilities from the sequence
            probabilities = brain.predict(sequence_input, verbose=0)[0]
            
            # Determine which actions are "pressed" based on a 0.5 threshold
            for i, prob in enumerate(probabilities):
                if prob > 0.5:
                    predicted_actions.append(ACTIONS[i])

        # 6. Visualize the output on the live feed
        display_frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        # Draw a black box for text readability
        cv2.rectangle(display_frame, (5, 5), (200, 30 + (len(ACTIONS) * 25)), (0, 0, 0), -1)
        
        # Display the predicted actions
        if not predicted_actions:
            cv2.putText(display_frame, "IDLE", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)
        else:
            for i, action in enumerate(predicted_actions):
                cv2.putText(display_frame, action, (15, 30 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Display FPS for performance debugging
        fps = 1 / (time.perf_counter() - frame_start_time)
        cv2.putText(display_frame, f"FPS: {fps:.1f}", (display_frame.shape[1] - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Cuphead AI - Live View (Press 'q' to quit)", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cv2.destroyAllWindows()