import tkinter as tk
from tkinter import ttk, simpledialog
import threading
import time
from pathlib import Path
from datetime import datetime

from session_recorder import SessionRecorder
from keyboard_listener import KeyboardListener

class SessionRecorderUI:
    """Main UI for the Cuphead Session Recorder."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cuphead Session Recorder (A2)")
        self.root.geometry("400x400")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        # --- State Management ---
        self.is_recording = False
        self.session_recorder = None
        self.keyboard_listener = None
        self.update_thread_running = True
        
        # This is your updated capture region
        self.CAPTURE_REGION = {'top': 245, 'left': 6, 'width': 1123, 'height': 586}

        self._create_widgets()
        self._setup_keyboard_listener()
        self._start_ui_updates()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Green.TButton', background='#4CAF50', font=('Arial', 12, 'bold'))
        style.configure('Red.TButton', background='#f44336', font=('Arial', 12, 'bold'))

        # Main control button
        # MODIFIED: Changed button text from (F8) to (0)
        self.start_stop_btn = ttk.Button(main_frame, text="Start Session (0)", 
                                         command=self.toggle_session, style='Green.TButton')
        self.start_stop_btn.pack(pady=10, ipady=10, fill=tk.X)

        # Status and Telemetry
        status_frame = ttk.LabelFrame(main_frame, text="Live Status", padding="10")
        status_frame.pack(pady=10, expand=True, fill=tk.BOTH)

        self.session_time_var = tk.StringVar(value="Session Time: 00:00")
        ttk.Label(status_frame, textvariable=self.session_time_var, font=('Arial', 14)).pack(pady=5)

        self.fights_marked_var = tk.StringVar(value="Fights Marked: 0")
        ttk.Label(status_frame, textvariable=self.fights_marked_var).pack(pady=5)

        self.last_action_var = tk.StringVar(value="Last Action: Idle")
        ttk.Label(status_frame, textvariable=self.last_action_var).pack(pady=5)

        # Hotkey instructions
        hotkey_frame = ttk.LabelFrame(main_frame, text="Hotkeys", padding="10")
        hotkey_frame.pack(pady=10, fill=tk.X)
        # MODIFIED: Changed all hotkey instruction labels
        ttk.Label(hotkey_frame, text="0: Start/Stop Session").pack(anchor=tk.W)
        ttk.Label(hotkey_frame, text="8: Mark Fight START").pack(anchor=tk.W)
        ttk.Label(hotkey_frame, text="9: Mark Fight END").pack(anchor=tk.W)

    def _setup_keyboard_listener(self):
        self.keyboard_listener = KeyboardListener(
            key_callback=self._on_key_event,
            marker_callback=self._on_marker_event,
            session_toggle_callback=self.toggle_session
        )
        self.keyboard_listener.start()

    def toggle_session(self):
        if self.is_recording:
            # Stop the recording
            self.session_recorder.stop_session()
            self.is_recording = False
            # MODIFIED: Changed button text from (F8) to (0)
            self.start_stop_btn.config(text="Start Session (0)", style='Green.TButton')
        else:
            # Start a new recording
            session_name = simpledialog.askstring("Session Name", "Enter a name for this session:",
                                                  initialvalue=f"session_{datetime.now():%Y-%m-%d_%H-%M}")
            if not session_name:
                return

            output_path = Path(__file__).parent.parent / "data" / "sessions"
            self.session_recorder = SessionRecorder(output_dir=output_path, region=self.CAPTURE_REGION)
            self.session_recorder.start_session(session_name)
            self.is_recording = True
            # MODIFIED: Changed button text from (F8) to (0)
            self.start_stop_btn.config(text="Stop Session (0)", style='Red.TButton')
    
    def _on_key_event(self, event_type, key):
        if self.is_recording:
            self.session_recorder.log_key_event(event_type, key)

    def _on_marker_event(self, marker_type):
        if self.is_recording:
            self.session_recorder.log_marker_event(marker_type)

    def _update_telemetry(self):
        """Periodically updates the UI labels with stats from the recorder."""
        if self.is_recording and self.session_recorder:
            stats = self.session_recorder.get_session_stats()
            
            elapsed_s = int(stats['elapsed_s'])
            minutes, seconds = divmod(elapsed_s, 60)
            self.session_time_var.set(f"Session Time: {minutes:02d}:{seconds:02d}")
            
            self.fights_marked_var.set(f"Fights Marked: {stats['fights_marked']}")
            self.last_action_var.set(f"Last Action: {stats['last_action']}")

    def _start_ui_updates(self):
        def update_loop():
            while self.update_thread_running:
                try:
                    self.root.after(0, self._update_telemetry)
                    time.sleep(0.5)
                except (tk.TclError, RuntimeError): # Handle window being closed
                    break
        threading.Thread(target=update_loop, daemon=True).start()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()

    def _on_closing(self):
        self.update_thread_running = False
        if self.is_recording:
            self.session_recorder.stop_session()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    app = SessionRecorderUI()
    app.run()