import cv2
import json
import numpy as np
from pathlib import Path

def build_key_state_timeline(log_path: Path) -> list:
    """
    Parses the _events.jsonl file (UTC timestamps).
    """
    key_events = []
    if not log_path.exists():
        print(f"❌ Event log not found: {log_path}")
        return []

    with open(log_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('event') in ['keydown', 'keyup']:
                    key_events.append((data['t'], data['key'], data['event']))
            except json.JSONDecodeError: continue
    
    # Sort by UTC timestamp
    key_events.sort(key=lambda x: x[0])
    return key_events

def load_frame_timestamps(frame_log_path: Path) -> list:
    """
    Parses the _frames.jsonl file.
    Returns a list where list[i] = UTC timestamp of Frame i.
    """
    timestamps = []
    if not frame_log_path.exists():
        print(f"❌ Frame log not found: {frame_log_path}")
        return []

    with open(frame_log_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                timestamps.append(data['t'])
            except: continue
    return timestamps

def get_keys_down_at_time(timeline: list, target_utc: float) -> set:
    """
    Replays history up to target_utc.
    """
    keys_down = set()
    for t, key, event in timeline:
        if t > target_utc: break
        if event == 'keydown': keys_down.add(key)
        elif event == 'keyup': keys_down.discard(key)
    return keys_down

def draw_key_state_on_frame(frame, keys_down: set, offset: float, utc_time: float):
    # Visual overlay
    key_positions = {
        'Key.up': (70, 50), 'Key.left': (30, 90), 'Key.down': (70, 90), 'Key.right': (110, 90),
        'Key.space': (30, 150), 'f': (150, 150), 'd': (200, 150)
    }
    # Draw Background
    cv2.rectangle(frame, (10, 20), (370, 220), (0, 0, 0), -1)
    
    # Draw Keys
    for key, (x, y) in key_positions.items():
        pos = (x + 20, y + 30)
        color = (0, 255, 0) if key in keys_down else (100, 100, 100)
        display_key = key.replace("Key.", "").upper()
        if key == 'f': display_key = "SHOOT"
        if key == 'd': display_key = "DASH"
        cv2.putText(frame, display_key, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)
    
    # Draw Debug Info
    cv2.putText(frame, f"UTC: {utc_time:.2f}", (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(frame, f"Offset: {offset:+.2f}s", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(frame, "[ / ] to adjust", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    return frame

def main():
    session_name = input("Enter session name (e.g. Train_1): ")
    data_dir = Path("./data/sessions")
    
    # New File Structure
    video_path = data_dir / f"{session_name}.mp4"
    event_path = data_dir / f"{session_name}_events.jsonl"
    frame_path = data_dir / f"{session_name}_frames.jsonl"
    
    if not video_path.exists(): 
        print(f"Video not found: {video_path}")
        return

    # Load Data
    print("Loading logs...")
    key_timeline = build_key_state_timeline(event_path)
    frame_timestamps = load_frame_timestamps(frame_path)
    
    if not frame_timestamps:
        print("CRITICAL: Frame timestamps missing. Cannot sync perfectly.")
        return

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    offset = 0.0
    is_paused = False
    frame_idx = 0

    print("\n--- GOLD STANDARD CHECKER ---")
    print(f"Loaded {len(frame_timestamps)} frame timestamps.")
    print(f"Loaded {len(key_timeline)} key events.")
    print("Press 'q' to quit, SPACE to pause, [ / ] to add manual offset.")

    while cap.isOpened():
        if not is_paused:
            ret, frame = cap.read()
            if not ret: 
                # Loop video for convenience
                frame_idx = 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            # --- THE MAGIC LOGIC ---
            # Instead of calculating time from FPS, we look it up!
            if frame_idx < len(frame_timestamps):
                base_utc = frame_timestamps[frame_idx]
            else:
                # Fallback if video is longer than log (rare)
                base_utc = frame_timestamps[-1] + (0.1 * (frame_idx - len(frame_timestamps)))

            # Apply manual offset just in case visual lag exists
            current_lookup_time = base_utc + offset
            
            # Get State
            keys = get_keys_down_at_time(key_timeline, current_lookup_time)
            
            # Draw
            frame = draw_key_state_on_frame(frame, keys, offset, base_utc)
            cv2.imshow('Sync Check (UTC)', frame)
            
            frame_idx += 1

        # Controls
        k = cv2.waitKey(int(1000/fps)) & 0xFF
        if k == ord('q'): break
        elif k == ord(' '): is_paused = not is_paused
        elif k == ord('['): offset -= 0.05; print(f"Offset: {offset:.2f}")
        elif k == ord(']'): offset += 0.05; print(f"Offset: {offset:.2f}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()