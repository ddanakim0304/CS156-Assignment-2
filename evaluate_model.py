# FILE: evaluate_model.py
# A script to load pre-trained models and evaluate their performance on a local dataset.

import os
import json
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import gc

# --- Step 0: Environment and Configuration ---
print("--- [Step 0] Setting up environment and configuration ---")
os.environ["KERAS_BACKEND"] = "tensorflow"

import keras
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
SESSION_NAME = "Cagney_1"  # The session you want to evaluate
DATA_DIR = Path("./data/sessions")
VIDEO_PATH = DATA_DIR / f"{SESSION_NAME}.mp4"
LOG_PATH = DATA_DIR / f"{SESSION_NAME}.jsonl"

IMG_HEIGHT, IMG_WIDTH = 72, 128
SEQUENCE_LENGTH = 10
ACTIONS = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'JUMP', 'SHOOT', 'DASH', 'LOCK', 'SPECIAL']
ACTION_MAP = {'Key.up': 0, 'Key.down': 1, 'Key.left': 2, 'Key.right': 3, 'Key.space': 4, 'f': 5, 'd': 6, 'x': 7, 'a': 8}
NUM_ACTIONS = len(ACTIONS)
BATCH_SIZE = 32

print(f"✅ Configuration loaded for session: {SESSION_NAME}")

# --- Step 1: Load Pre-Trained Models ---
print("\n--- [Step 1] Loading pre-trained Encoder and Brain models ---")
try:
    encoder = keras.models.load_model('cuphead_encoder.keras')
    brain_model_rnn = keras.models.load_model('cuphead_brain.keras')
    print("✅ Models loaded successfully.")
    encoder.summary()
    brain_model_rnn.summary()
except Exception as e:
    print(f"❌ Error loading models: {e}")
    print("Please make sure 'cuphead_encoder.keras' and 'cuphead_brain.keras' are in this directory.")
    exit()

# --- Step 2: Data Preparation Functions ---
# (These are the same helper functions from your notebook)
def get_fight_intervals(log_path):
    intervals = []
    start_time = None
    with open(log_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            if data.get('event') == 'marker':
                if data['type'] == 'fight_start': start_time = data['t']
                elif data['type'] == 'fight_end' and start_time is not None:
                    intervals.append((start_time, data['t']))
                    start_time = None
    return intervals

def get_key_state_timeline(log_path):
    key_events = []
    with open(log_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            if data.get('event') in ['keydown', 'keyup']:
                key_events.append((data['t'], data['key'], data['event']))
    key_events.sort(key=lambda x: x[0])
    return key_events

def get_keys_down_at_time(timeline, current_time):
    keys_down = set()
    for t, key, event in timeline:
        if t > current_time: break
        if event == 'keydown': keys_down.add(key)
        elif event == 'keyup': keys_down.discard(key)
    return keys_down

# --- Step 3: Process the Video and Create the Evaluation Dataset ---
print("\n--- [Step 3] Processing video to create evaluation dataset ---")

fight_intervals = get_fight_intervals(LOG_PATH)
key_timeline = get_key_state_timeline(LOG_PATH)
cap = cv2.VideoCapture(str(VIDEO_PATH))
fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0: fps = 10.0

all_frames = []
all_labels = []

total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
for _ in tqdm(range(total_video_frames), desc="Reading video frames"):
    ret, frame = cap.read()
    if not ret: break
    current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
    if any(start <= current_time <= end for start, end in fight_intervals):
        processed_frame = cv2.resize(frame, (IMG_WIDTH, IMG_HEIGHT))
        processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        processed_frame = processed_frame / 255.0
        all_frames.append(processed_frame)

        keys_down = get_keys_down_at_time(key_timeline, current_time)
        label = np.zeros(NUM_ACTIONS, dtype=int)
        for key in keys_down:
            if key in ACTION_MAP:
                label[ACTION_MAP[key]] = 1
        all_labels.append(label)
cap.release()

X_data_full = np.array(all_frames).reshape(-1, IMG_HEIGHT, IMG_WIDTH, 1)
y_data_full = np.array(all_labels)
del all_frames, all_labels # Free memory
gc.collect()

print(f"✅ Full dataset loaded into memory. Shape: {X_data_full.shape}")

# --- Step 4: Create Latent Vectors and Sequences ---
print("\n--- [Step 4] Creating sequences from latent vectors ---")
latent_vectors = encoder.predict(X_data_full, batch_size=BATCH_SIZE, verbose=1)
del X_data_full # Free memory
gc.collect()

X_sequences, y_sequences = [], []
for i in tqdm(range(len(latent_vectors) - SEQUENCE_LENGTH), desc="Creating sequences"):
    X_sequences.append(latent_vectors[i:i+SEQUENCE_LENGTH])
    y_sequences.append(y_data_full[i + SEQUENCE_LENGTH - 1])
X_sequences = np.array(X_sequences)
y_sequences = np.array(y_sequences)
del latent_vectors, y_data_full # Free memory
gc.collect()

print(f"✅ Sequential dataset created. Shape: {X_sequences.shape}")

# --- Step 5: Generate Predictions and Evaluate ---
print("\n--- [Step 5] Generating predictions and performance report ---")
y_pred_probs = brain_model_rnn.predict(X_sequences, batch_size=BATCH_SIZE, verbose=1)
y_pred_binary = (y_pred_probs > 0.5).astype(int)

report = classification_report(
    y_sequences, 
    y_pred_binary, 
    target_names=ACTIONS, 
    zero_division=0
)

print("\n\n--- Full Classification Report ---")
print(report)

# --- Step 6: Visualize Class Imbalance ---
print("\n--- Data Distribution (Support) for Each Action ---")
support = np.sum(y_sequences, axis=0)
support_df = pd.DataFrame({'Action': ACTIONS, 'Frames': support}).sort_values('Frames', ascending=False)

plt.figure(figsize=(12, 7))
sns.barplot(x='Frames', y='Action', data=support_df, orient='h', palette='viridis_r')
plt.title(f'Action Frequency in "{SESSION_NAME}" Dataset', fontsize=16)
plt.xlabel('Number of Frames (Support)', fontsize=12)
plt.ylabel('Action', fontsize=12)
plt.grid(axis='x', linestyle='--', alpha=0.6)
for index, value in enumerate(support_df['Frames']):
    plt.text(value, index, f' {value}', va='center')
plt.tight_layout()
plt.savefig(f'evaluation_report_{SESSION_NAME}.png')
print(f"\n✅ Evaluation complete. Support plot saved to 'evaluation_report_{SESSION_NAME}.png'")
plt.show()