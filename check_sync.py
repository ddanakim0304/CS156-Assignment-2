# FILE: check_sync.py
import cv2
import json
import numpy as np
from pathlib import Path

def build_key_state_timeline(log_path: Path) -> list:
    """
    Parses the JSONL log file to create a timeline of keyboard state changes.
    Each entry in the list is a tuple: (timestamp, key, event_type).
    """
    key_events = []
    with open(log_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                # We only care about keydown and keyup events for this
                if data.get('event') in ['keydown', 'keyup']:
                    key_events.append((data['t'], data['key'], data['event']))
            except json.JSONDecodeError:
                continue
    
    # Sort by timestamp just in case
    key_events.sort(key=lambda x: x[0])
    return key_events

def get_keys_down_at_time(timeline: list, current_time: float) -> set:
    """
    Determines which keys were held down at a specific point in time
    by replaying the event timeline up to that point.
    """
    keys_down = set()
    for t, key, event in timeline:
        if t > current_time:
            break # We've gone past the current time, so we can stop
        if event == 'keydown':
            keys_down.add(key)
        elif event == 'keyup':
            keys_down.discard(key)
    return keys_down

def draw_key_state_on_frame(frame, keys_down: set):
    """
    Draws a simple visual representation of the currently pressed keys on the video frame.
    """
    # Define positions and colors for our key indicators
    key_positions = {
        'Key.up': (70, 50),
        'Key.left': (30, 90),
        'Key.down': (70, 90),
        'Key.right': (110, 90),
        'Key.space': (30, 150),
        'f': (150, 150),
        'd': (200, 150),
    }
    
    y_offset = 30 # Position the whole block from the top
    x_offset = 20
    
    # Draw background rectangle for better visibility
    cv2.rectangle(frame, (x_offset - 10, y_offset - 10), (x_offset + 350, y_offset + 170), (0, 0, 0), -1)
    
    for key, (x, y) in key_positions.items():
        pos = (x + x_offset, y + y_offset)
        color = (0, 255, 0) if key in keys_down else (100, 100, 100) # Green if pressed, gray if not
        
        # Make the key name more readable for display
        display_key = key.replace("Key.", "").upper()
        if key == 'f': display_key = "SHOOT"
        if key == 'd': display_key = "DASH"
        
        cv2.putText(frame, display_key, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)
    return frame

def main():
    session_name = input("Enter the session name to check (e.g., cagney_session_1): ")
    
    data_dir = Path("./data/sessions")
    video_path = data_dir / f"{session_name}.mp4"
    log_path = data_dir / f"{session_name}.jsonl"
    
    if not video_path.exists() or not log_path.exists():
        print(f"Error: Could not find files for session '{session_name}'")
        print(f"Checked for: {video_path}")
        print(f"Checked for: {log_path}")
        return

    # 1. Load the video and build the key state timeline
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    key_timeline = build_key_state_timeline(log_path)
    
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    print("\n--- Starting Sync Check ---")
    print(f"Video FPS: {fps:.2f}")
    print("Press 'q' to quit.")
    print("Press 'space' to pause/play.")

    is_paused = False
    
    # 2. Loop through video frames
    while cap.isOpened():
        if not is_paused:
            ret, frame = cap.read()
            if not ret:
                break

            # 3. Calculate current time in the video
            current_frame_num = cap.get(cv2.CAP_PROP_POS_FRAMES)
            current_time_sec = current_frame_num / fps

            # 4. Get the keys that were down at this specific time
            keys_down = get_keys_down_at_time(key_timeline, current_time_sec)
            
            # 5. Draw the state and info on the frame
            frame_with_overlay = draw_key_state_on_frame(frame.copy(), keys_down)
            
            # Draw current timestamp
            time_text = f"Time: {current_time_sec:.2f}s"
            cv2.putText(frame_with_overlay, time_text, (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 2)
            
            cv2.imshow('Sync Check - Press "q" to quit', frame_with_overlay)

        # Handle user input for pause/play/quit
        key = cv2.waitKey(int(1000 / fps)) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            is_paused = not is_paused
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n--- Sync Check Finished ---")

if __name__ == '__main__':
    main()