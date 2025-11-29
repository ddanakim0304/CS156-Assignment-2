# FILE: app/main.py (CORRECTED to pause the listener)
import tkinter as tk
from tkinter import ttk, simpledialog
import threading
import time
from pathlib import Path
from datetime import datetime
import queue

from session_recorder import SessionRecorder
from keyboard_listener import KeyboardListener

class SessionRecorderUI:
    """Main UㄱI for the Cuphead Session Recorder."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cuphead Session Recorder (A2)")
        self.root.geometry("400x400")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

        self.is_recording = False
        self.session_recorder = None
        self.keyboard_listener = None
        self.update_thread_running = True
    
        self.ui_action_queue = queue.Queue()
        self.CAPTURE_REGION = {'top': 264, 'left': 0, 'width': 720, 'height': 403}
        self._create_widgets()
        self._setup_keyboard_listener()
        self._start_ui_updates()
        self._process_ui_queue()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Green.TButton', background='#4CAF50', font=('Arial', 12, 'bold'))
        style.configure('Red.TButton', background='#f44336', font=('Arial', 12, 'bold'))

        self.start_stop_btn = ttk.Button(main_frame, text="Start Session (1)", 
                                         command=self.toggle_session, style='Green.TButton')
        self.start_stop_btn.pack(pady=10, ipady=10, fill=tk.X)

        status_frame = ttk.LabelFrame(main_frame, text="Live Status", padding="10")
        status_frame.pack(pady=10, expand=True, fill=tk.BOTH)

        self.session_time_var = tk.StringVar(value="Session Time: 00:00")
        ttk.Label(status_frame, textvariable=self.session_time_var, font=('Arial', 14)).pack(pady=5)

        self.fights_marked_var = tk.StringVar(value="Fights Marked: 0")
        ttk.Label(status_frame, textvariable=self.fights_marked_var).pack(pady=5)

        self.last_action_var = tk.StringVar(value="Last Action: Idle")
        ttk.Label(status_frame, textvariable=self.last_action_var).pack(pady=5)

        hotkey_frame = ttk.LabelFrame(main_frame, text="Hotkeys", padding="10")
        hotkey_frame.pack(pady=10, fill=tk.X)
        ttk.Label(hotkey_frame, text="1: Start/Stop Session").pack(anchor=tk.W)
        ttk.Label(hotkey_frame, text="8: Mark Fight START").pack(anchor=tk.W)
        ttk.Label(hotkey_frame, text="9: Mark Fight END").pack(anchor=tk.W)

    def _setup_keyboard_listener(self):
        self.keyboard_listener = KeyboardListener(
            key_callback=self._on_key_event,
            marker_callback=lambda marker: self.ui_action_queue.put(('marker', marker)),
            session_toggle_callback=lambda: self.ui_action_queue.put(('toggle_session', None))
        )
        self.keyboard_listener.start()
        
    def _process_ui_queue(self):
        try:
            message_type, data = self.ui_action_queue.get_nowait()
            if message_type == 'toggle_session':
                self.toggle_session()
            elif message_type == 'marker':
                self._on_marker_event(data)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_ui_queue)

    def toggle_session(self):
        if self.is_recording:
            if self.session_recorder:
                self.session_recorder.stop_session()
            self.is_recording = False
            self.start_stop_btn.config(text="Start Session (1)", style='Green.TButton')
        else:
            # MODIFIED: Pause listener before showing dialog
            self.keyboard_listener.pause()
            session_name = simpledialog.askstring("Session Name", "Enter a name for this session:",
                                                  initialvalue=f"session_{datetime.now():%Y-%m-%d_%H-%M}")
            # MODIFIED: Resume listener after dialog is closed
            self.keyboard_listener.resume()

            if not session_name:
                return

            output_path = Path(__file__).parent.parent / "data" / "sessions"
            self.session_recorder = SessionRecorder(output_dir=output_path, region=self.CAPTURE_REGION)
            self.session_recorder.start_session(session_name)
            self.is_recording = True
            self.start_stop_btn.config(text="Stop Session (1)", style='Red.TButton')
    
    def _on_key_event(self, event_type, key):
        if self.is_recording and self.session_recorder:
            self.session_recorder.log_key_event(event_type, key)

    def _on_marker_event(self, marker_type):
        if self.is_recording and self.session_recorder:
            self.session_recorder.log_marker_event(marker_type)

    def _update_telemetry(self):
        if self.session_recorder:
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
                except (tk.TclError, RuntimeError):
                    break
        threading.Thread(target=update_loop, daemon=True).start()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()

    def _on_closing(self):
        self.update_thread_running = False
        if self.is_recording and self.session_recorder:
            self.session_recorder.stop_session()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    import sys
    import platform
    
    # Check for macOS and warn about accessibility permissions
    if platform.system() == "Darwin":
        print("=" * 60)
        print("macOS Accessibilx ity Permissions Required")
        print("=" * 60)
        print("If the app crashes with 'trace trap', you need to:")
        print("1. Open System Settings → Privacy & Security → Accessibility")
        print("2. Add your Terminal app and grant permission")
        print("3. Restart this application")
        print("=" * 60)
        print()
    
    try:
        app = SessionRecorderUI()
        app.run()
    except Exception as e:
        print(f"\nError starting application: {e}")
        if platform.system() == "Darwin":
            print("\nThis might be an accessibility permissions issue.")
            print("Please check System Settings → Privacy & Security → Accessibility")
        sys.exit(1)