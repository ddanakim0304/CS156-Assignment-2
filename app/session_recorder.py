import json
import time
import threading
import cv2
import mss
import numpy as np
from pathlib import Path

class SessionRecorder:
    """
    Handles synchronized screen recording and keystroke logging using Absolute UTC Time.
    Produces: .mp4, _events.jsonl, and _frames.jsonl to eliminate drift.
    """
    
    def __init__(self, output_dir: Path, region: dict):
        self.output_dir = output_dir
        self.region = region
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_recording = False
        
        # File Handles
        self._video_writer = None
        self._event_file = None  # Stores Key presses
        self._frame_file = None  # Stores Frame timestamps
        
        self._recording_thread = None
        self._shutdown_event = threading.Event()
        
        # UI Stats
        self.fights_marked = 0
        self.last_action = ""
        
        # Fight Timer Logic (For UI Display Only)
        self.in_fight = False
        self.total_fight_time = 0.0  # Accumulated time of completed fights
        self.current_fight_start_time = 0.0 # Start time of current active fight

    def start_session(self, session_name: str):
        if self.is_recording:
            return

        print(f"Starting session: {session_name}")
        self.is_recording = True
        self._shutdown_event.clear()
        
        # Reset Stats
        self.fights_marked = 0
        self.last_action = "Ready"
        self.in_fight = False
        self.total_fight_time = 0.0
        self.current_fight_start_time = 0.0
        
        # --- Define Paths ---
        video_path = self.output_dir / f"{session_name}.mp4"
        event_path = self.output_dir / f"{session_name}_events.jsonl"
        frame_path = self.output_dir / f"{session_name}_frames.jsonl"
        
        # --- Init Video Writer (10 FPS) ---
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(
            str(video_path), 
            fourcc, 
            10.0, 
            (self.region['width'], self.region['height'])
        )
        
        # --- Init Logs ---
        self._event_file = open(event_path, 'w')
        self._frame_file = open(frame_path, 'w')
        
        # Start Worker
        self._recording_thread = threading.Thread(target=self._worker, daemon=True)
        self._recording_thread.start()

    def stop_session(self):
        if not self.is_recording:
            return
        
        # If we stop session while in a fight, add the partial time
        if self.in_fight:
            self.total_fight_time += (time.time() - self.current_fight_start_time)
            self.in_fight = False
            
        print("Stopping session...")
        self.is_recording = False
        self._shutdown_event.set()

    def log_key_event(self, event_type: str, key: str):
        """Logs a key press with exact UTC time."""
        if not self.is_recording: return
        
        # UTC TIMESTAMP
        t = time.time()
        
        entry = {'event': event_type, 'key': key, 't': t}
        self._event_file.write(json.dumps(entry) + '\n')
        self._event_file.flush() # Ensure it's written immediately
        
        self.last_action = f"{key} ({event_type})"

    def log_marker_event(self, marker_type: str):
        """Logs a fight marker with exact UTC time and updates Fight Timer."""
        if not self.is_recording: return
        
        # UTC TIMESTAMP
        t = time.time()
        
        entry = {'event': 'marker', 'type': marker_type, 't': t}
        self._event_file.write(json.dumps(entry) + '\n')
        self._event_file.flush()
        
        print(f"📍 MARKER: {marker_type}")
        self.last_action = f"MARKER: {marker_type}"
        
        # --- Timer Logic for UI ---
        if marker_type == 'fight_start':
            self.fights_marked += 1
            if not self.in_fight:
                self.in_fight = True
                self.current_fight_start_time = t
                
        elif marker_type == 'fight_end':
            if self.in_fight:
                # Add the duration of this specific fight to the total
                duration = t - self.current_fight_start_time
                self.total_fight_time += duration
                self.in_fight = False

    def get_session_stats(self) -> dict:
        """Returns stats for the UI. elapsed_s now returns Total Fight Time."""
        if not self.is_recording:
            return {'elapsed_s': 0, 'fights_marked': 0, 'last_action': 'Stopped'}
        
        # Calculate time to display
        current_display_time = self.total_fight_time
        if self.in_fight:
            current_display_time += (time.time() - self.current_fight_start_time)
            
        return {
            'elapsed_s': current_display_time, 
            'fights_marked': self.fights_marked, 
            'last_action': self.last_action
        }

    def _worker(self):
        """
        Uses UTC scheduling to ensure frames line up with wall-clock time.
        """
        try:
            with mss.mss() as sct:
                target_fps = 10.0
                frame_duration = 1.0 / target_fps
                
                # Schedule based on absolute UTC time
                next_frame_time = time.time()

                while not self._shutdown_event.is_set():
                    # 1. Capture Frame
                    try:
                        img = sct.grab(self.region)
                        img_np = np.array(img)
                        frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                    except Exception as e:
                        print(f"Capture error: {e}")
                        continue

                    # 2. Sync Logic
                    now = time.time()
                    
                    while next_frame_time < now:
                        # Write video frame
                        self._video_writer.write(frame_bgr)
                        
                        # RECORD EXACT MAPPING: Frame -> UTC Time
                        frame_entry = {"t": next_frame_time}
                        self._frame_file.write(json.dumps(frame_entry) + '\n')
                        
                        # Advance schedule
                        next_frame_time += frame_duration
                    
                    # 3. Sleep
                    # Only sleep if we are ahead of schedule
                    time_to_sleep = next_frame_time - time.time()
                    if time_to_sleep > 0:
                        time.sleep(time_to_sleep)
                    
        finally:
            print("Worker cleanup...")
            if self._video_writer:
                self._video_writer.release()
            if self._event_file:
                self._event_file.close()
            if self._frame_file:
                self._frame_file.close()
            print("Files closed and saved.")