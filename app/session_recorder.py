import json
import time
import threading
import cv2
import mss
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

class SessionRecorder:
    """Handles synchronized screen recording and keystroke logging for a continuous session."""
    
    def __init__(self, output_dir: Path, region: dict):
        self.output_dir = output_dir
        self.region = region  # Screen capture region {'top', 'left', 'width', 'height'}
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_recording = False
        self._start_time = 0.0
        self._log_file = None
        self._video_writer = None
        self._recording_thread = None
        self._lock = threading.Lock()
        
        # Stats for the UI
        self.fights_marked = 0
        self.last_action = ""

    def start_session(self, session_name: str):
        if self.is_recording:
            print("Session already in progress.")
            return

        print(f"Starting session: {session_name}")
        self.is_recording = True
        self._start_time = time.perf_counter()
        self.fights_marked = 0
        self.last_action = ""
        
        # Setup files
        video_path = self.output_dir / f"{session_name}.mp4"
        log_path = self.output_dir / f"{session_name}.jsonl"
        
        # Setup video writer (e.g., at 10 FPS)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (self.region['width'], self.region['height']))
        
        # Setup log file
        self._log_file = open(log_path, 'w')
        
        # Start the background recording thread
        self._recording_thread = threading.Thread(target=self._worker, daemon=True)
        self._recording_thread.start()

    def stop_session(self):
        if not self.is_recording:
            return
            
        print("Stopping session...")
        self.is_recording = False
        # The worker thread will see the flag and exit gracefully
        
        # Wait for the thread to finish writing
        if self._recording_thread:
            self._recording_thread.join(timeout=2.0)

        # Cleanup is handled in the worker's finally block
        print("Session stopped and files saved.")

    def log_key_event(self, event_type: str, key: str):
        """Logs a standard keyboard event."""
        if not self.is_recording or self._log_file is None:
            return
            
        timestamp = time.perf_counter() - self._start_time
        log_entry = {'event': event_type, 'key': key, 't': timestamp}
        self._log_file.write(json.dumps(log_entry) + '\n')
        
        # Update last action for UI
        self.last_action = f"{key} ({event_type})"

    def log_marker_event(self, marker_type: str):
        """Logs a special marker event, e.g., 'fight_start'."""
        if not self.is_recording or self._log_file is None:
            return
            
        if marker_type == "fight_start":
            self.fights_marked += 1

        timestamp = time.perf_counter() - self._start_time
        log_entry = {'event': 'marker', 'type': marker_type, 't': timestamp}
        self._log_file.write(json.dumps(log_entry) + '\n')
        print(f"Marker logged: {marker_type} at {timestamp:.2f}s")
        self.last_action = f"MARKER: {marker_type}"

    def get_session_stats(self) -> dict:
        """Provides current session stats for the UI."""
        if not self.is_recording:
            return {'elapsed_s': 0, 'fights_marked': 0, 'last_action': 'Idle'}
            
        with self._lock:
            elapsed_s = time.perf_counter() - self._start_time
            return {
                'elapsed_s': elapsed_s,
                'fights_marked': self.fights_marked,
                'last_action': self.last_action
            }

    def _worker(self):
        """The main worker loop that runs in a background thread."""
        try:
            with mss.mss() as sct:
                while self.is_recording:
                    frame_start_time = time.perf_counter()
                    
                    # Grab the screen region
                    img = sct.grab(self.region)
                    img_np = np.array(img)
                    
                    # Convert from BGRA (mss format) to BGR (OpenCV format)
                    frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                    
                    # Write the frame to the video file
                    self._video_writer.write(frame_bgr)
                    
                    # Enforce FPS by sleeping for the remaining frame time
                    sleep_duration = (1/10.0) - (time.perf_counter() - frame_start_time)
                    if sleep_duration > 0:
                        time.sleep(sleep_duration)
        finally:
            # This block ensures cleanup happens even if there's an error
            with self._lock:
                if self._video_writer:
                    self._video_writer.release()
                    self._video_writer = None
                if self._log_file:
                    self._log_file.close()
                    self._log_file = None