import json
import time
import threading
import cv2
import mss
import numpy as np
from pathlib import Path

class SessionRecorder:
    """Handles synchronized screen recording and keystroke logging for a continuous session."""
    
    def __init__(self, output_dir: Path, region: dict):
        self.output_dir = output_dir
        self.region = region
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_recording = False
        self._start_time = 0.0
        self._log_file = None
        self._video_writer = None
        self._recording_thread = None
        self._shutdown_event = threading.Event()
        
        # UI Stats
        self.fights_marked = 0
        self.last_action = ""

    def start_session(self, session_name: str):
        if self.is_recording:
            return

        print(f"Starting session: {session_name}")
        self.is_recording = True
        self._shutdown_event.clear()
        self._start_time = time.perf_counter()
        self.fights_marked = 0
        self.last_action = ""
        
        video_path = self.output_dir / f"{session_name}.mp4"
        log_path = self.output_dir / f"{session_name}.jsonl"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (self.region['width'], self.region['height']))
        self._log_file = open(log_path, 'w')
        
        self._recording_thread = threading.Thread(target=self._worker, daemon=True)
        self._recording_thread.start()

    def stop_session(self):
        """Signals the recording thread to stop. This is now NON-BLOCKING."""
        if not self.is_recording:
            return
            
        print("Signaling recording thread to stop...")
        self.is_recording = False
        self._shutdown_event.set()

    def log_key_event(self, event_type: str, key: str):
        if not self.is_recording: return
        timestamp = time.perf_counter() - self._start_time
        log_entry = {'event': event_type, 'key': key, 't': timestamp}
        self._log_file.write(json.dumps(log_entry) + '\n')
        self.last_action = f"{key} ({event_type})"

    def log_marker_event(self, marker_type: str):
        if not self.is_recording: return
        if marker_type == "fight_start":
            self.fights_marked += 1
        timestamp = time.perf_counter() - self._start_time
        log_entry = {'event': 'marker', 'type': marker_type, 't': timestamp}
        self._log_file.write(json.dumps(log_entry) + '\n')
        print(f"Marker logged: {marker_type} at {timestamp:.2f}s")
        self.last_action = f"MARKER: {marker_type}"

    def get_session_stats(self) -> dict:
        if not self.is_recording:
            return {'elapsed_s': 0, 'fights_marked': self.fights_marked, 'last_action': 'Stopped'}
        elapsed_s = time.perf_counter() - self._start_time
        return {'elapsed_s': elapsed_s, 'fights_marked': self.fights_marked, 'last_action': self.last_action}

    def _worker(self):
        """The main worker loop that runs in a background thread."""
        try:
            with mss.mss() as sct:
                while not self._shutdown_event.is_set():
                    frame_start_time = time.perf_counter()
                    
                    img = sct.grab(self.region)
                    img_np = np.array(img)
                    frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                    self._video_writer.write(frame_bgr)
                    
                    sleep_duration = (1/10.0) - (time.perf_counter() - frame_start_time)
                    if sleep_duration > 0:
                        time.sleep(sleep_duration)
        finally:
            # This cleanup now happens safely in the background
            print("Worker thread cleaning up and saving files...")
            if self._video_writer:
                self._video_writer.release()
            if self._log_file:
                self._log_file.close()
            print("Files saved successfully.")