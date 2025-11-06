#!/usr/bin/env python3
"""
Cuphead Boss Keystroke Data Logger - Main UI Application
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import csv
from pathlib import Path
from enum import Enum
from collections import defaultdict

from data_logger import DataLogger
from keyboard_listener import KeyboardListener


class AppState(Enum):
    IDLE = "idle"
    RECORDING = "recording"  
    ENDED = "ended"


class CupheadLoggerUI:
    """Main UI application for Cuphead keystroke logging"""
    
    def __init__(self, use_new_dataset: bool = False):
        self.root = tk.Tk()
        self.root.title("Cuphead Boss Keystroke Logger")
        self.root.geometry("500x600")  # Much larger window
        self.root.resizable(True, True)  # Allow resizing
        self.root.minsize(450, 550)  # Set minimum size
        
        # Make window always on top
        self.root.attributes('-topmost', True)
        
        # Initialize state
        self.state = AppState.IDLE
        # Use new dataset paths if specified
        if use_new_dataset:
            self.data_logger = DataLogger(raw_subdir="raw_new", csv_filename="fight_summaries_new.csv")
        else:
            self.data_logger = DataLogger()
        self.keyboard_listener = None
        
        # UI update thread control
        self.update_thread_running = False
        
        # Session history for display
        self.session_history = []
        
        # Keystroke display timeout
        self.keystroke_timeout_id = None
        
        # Boss fight counts cache
        self.boss_fight_counts = {}
        
        # Create UI elements
        self._create_widgets()
        self._setup_keyboard_listener()
        self._load_existing_sessions()  # Load existing sessions from CSV
        self._update_boss_counts()  # Load boss fight counts
        self._update_ui_state()
        
        # Start UI update loop
        self._start_ui_updates()
    
    def _create_widgets(self):
        """Create all UI widgets"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure root grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Configure button styles for different states
        style = ttk.Style()
        
        # Set theme that supports colors better
        try:
            style.theme_use('clam')
        except:
            pass  # Fallback to default theme
            
        # Configure custom button styles
        style.configure('Green.TButton', 
                       foreground='white', 
                       background='#4CAF50', 
                       font=('Arial', 12, 'bold'),
                       padding=(10, 8))
        style.configure('Red.TButton', 
                       foreground='white', 
                       background='#f44336', 
                       font=('Arial', 12, 'bold'),
                       padding=(10, 8))
        
        # Configure hover effects
        style.map('Green.TButton', 
                 background=[('active', '#45a049'), ('pressed', '#3d8b40')])
        style.map('Red.TButton', 
                 background=[('active', '#da190b'), ('pressed', '#c41e3a')])
        
        # Boss selection
        ttk.Label(main_frame, text="Boss:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.boss_var = tk.StringVar(value="Cagney Carnation")
        self.boss_combo = ttk.Combobox(main_frame, textvariable=self.boss_var, width=30, state="readonly")
        self.boss_combo['values'] = self.data_logger.config.get('bosses', [])
        self.boss_combo.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Loadout
        ttk.Label(main_frame, text="Loadout:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.loadout_var = tk.StringVar(value=self.data_logger.config.get('loadout', 'Peashooter + Smoke Bomb'))
        self.loadout_entry = ttk.Entry(main_frame, textvariable=self.loadout_var, width=30)
        self.loadout_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Difficulty
        ttk.Label(main_frame, text="Difficulty:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.difficulty_var = tk.StringVar(value=self.data_logger.config.get('difficulty', 'Regular'))
        self.difficulty_combo = ttk.Combobox(main_frame, textvariable=self.difficulty_var, width=30, state="readonly")
        self.difficulty_combo['values'] = ['Regular', 'Simple', 'Expert']
        self.difficulty_combo.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=15, sticky=(tk.W, tk.E))
        
        self.start_btn = ttk.Button(button_frame, text="Start (F1)", command=self._toggle_fight)
        self.start_btn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.lose_btn = ttk.Button(button_frame, text="Lose (F8)", command=self._mark_lose)
        self.lose_btn.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.win_btn = ttk.Button(button_frame, text="Win (F9)", command=self._mark_win)
        self.win_btn.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        self.delete_btn = ttk.Button(button_frame, text="Delete Selected", command=self._delete_selected_session)
        self.delete_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Large elapsed time display (most prominent)
        self.elapsed_var = tk.StringVar(value="00:00")
        self.elapsed_label = ttk.Label(main_frame, textvariable=self.elapsed_var, 
                                     font=('Arial', 24, 'bold'), 
                                     foreground='#2E7D32')
        self.elapsed_label.grid(row=4, column=0, columnspan=3, pady=15)
        
        # Telemetry display (compact)
        telemetry_frame = ttk.LabelFrame(main_frame, text="Session Stats", padding="8")
        telemetry_frame.grid(row=5, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        # Compact stats in one row
        self.events_var = tk.StringVar(value="Events: 0")
        ttk.Label(telemetry_frame, textvariable=self.events_var, font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.boss_info_var = tk.StringVar(value="")
        ttk.Label(telemetry_frame, textvariable=self.boss_info_var, font=('Arial', 10)).grid(row=0, column=1, sticky=tk.E, pady=2)
        
        # Current keystroke display (more prominent)
        self.keystroke_var = tk.StringVar(value="Press F1 to Start")
        self.keystroke_label = ttk.Label(telemetry_frame, textvariable=self.keystroke_var, 
                                       font=('Arial', 11, 'bold'), foreground="#666")
        self.keystroke_label.grid(row=1, column=0, columnspan=2, pady=8)
        
        # Pin on top checkbox
        self.pin_var = tk.BooleanVar(value=True)
        self.pin_check = ttk.Checkbutton(main_frame, text="Pin on top", variable=self.pin_var, command=self._toggle_pin)
        self.pin_check.grid(row=6, column=0, columnspan=3, pady=8)
        
        # Session history
        history_frame = ttk.LabelFrame(main_frame, text="Recent Sessions (Last 5)", padding="8")
        history_frame.grid(row=7, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create Treeview for session history
        self.history_tree = ttk.Treeview(history_frame, columns=('outcome', 'duration', 'events'), show='headings', height=6)
        self.history_tree.heading('#1', text='Outcome')
        self.history_tree.heading('#2', text='Duration')
        self.history_tree.heading('#3', text='Events')
        
        # Configure column widths for better visibility
        self.history_tree.column('#1', width=100, anchor='center')
        self.history_tree.column('#2', width=100, anchor='center')
        self.history_tree.column('#3', width=80, anchor='center')
        
        # Add scrollbar for history
        history_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        history_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights for proper resizing
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(7, weight=1)  # Make history frame expandable
        
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        telemetry_frame.columnconfigure(0, weight=1)
        telemetry_frame.columnconfigure(1, weight=1)
        
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
    def _setup_keyboard_listener(self):
        """Setup global keyboard listener with hotkey callbacks"""
        hotkey_callbacks = {
            'start': self._toggle_fight,  # F1 now toggles start/end
            'lose': self._mark_lose,
            'win': self._mark_win
        }
        
        self.keyboard_listener = KeyboardListener(
            event_callback=self._on_keyboard_event,
            hotkey_callbacks=hotkey_callbacks
        )
        self.keyboard_listener.start()
        
    def _on_keyboard_event(self, event_type: str, key: str):
        """Handle keyboard events from the listener"""
        if self.state == AppState.RECORDING:
            self.data_logger.log_event(event_type, key)
        
        # Update current keystroke display
        self._update_keystroke_display(event_type, key)
            
    def _toggle_fight(self):
        """Toggle between starting and ending a fight based on current state"""
        if self.state == AppState.IDLE:
            self._start_fight()
        elif self.state == AppState.RECORDING:
            self._end_fight()
            
    def _start_fight(self):
        """Start a new fight session"""
        if self.state != AppState.IDLE:
            # Remove this line since status_var doesn't exist
            # self.status_var.set("Warning: End current fight first!")
            return
            
        try:
            boss = self._extract_boss_name(self.boss_var.get())  # Extract actual boss name
            loadout = self.loadout_var.get()
            difficulty = self.difficulty_var.get()
            
            fight_id = self.data_logger.start_fight(boss, loadout, difficulty)
            self.state = AppState.RECORDING
            self._update_ui_state()
            
            print(f"Started fight: {fight_id}")
            
        except Exception as e:
            # Remove this line since status_var doesn't exist
            # self.status_var.set(f"Error starting fight: {str(e)}")
            print(f"Error starting fight: {e}")
            
    def _end_fight(self):
        """End the current fight session"""
        if self.state != AppState.RECORDING:
            return
            
        self.state = AppState.ENDED
        self._update_ui_state()
        
    def _mark_lose(self):
        """Mark the fight as a loss"""
        self._complete_fight("lose")
        
    def _mark_win(self):
        """Mark the fight as a win"""
        self._complete_fight("win")
        
    def _complete_fight(self, outcome: str):
        """Complete the fight with the given outcome"""
        try:
            # Auto-end if still recording
            if self.state == AppState.RECORDING:
                self.state = AppState.ENDED
                
            if self.state != AppState.ENDED:
                return
                
            session_data = self.data_logger.end_fight(outcome)
            self.state = AppState.IDLE
            self._update_ui_state()
            
            # Add to session history
            duration = session_data['duration_s']
            events = session_data['n_events']
            fight_id = session_data['fight_id']
            boss = session_data.get('boss', 'Unknown')
            
            # Create session entry
            session_entry = {
                'fight_id': fight_id,
                'boss': boss,
                'outcome': outcome.upper(),
                'duration': f"{duration:.1f}s",
                'events': str(events),
                'timestamp': time.strftime("%H:%M:%S")
            }
            
            self._add_to_history(session_entry)
            
            # Update boss counts after completing a fight
            self._update_boss_counts()
            
            print(f"Completed fight {fight_id}: {outcome} ({duration:.1f}s, {events} events)")
            
        except Exception as e:
            # Remove this line since status_var doesn't exist
            # self.status_var.set(f"Error: {str(e)}")
            print(f"Error completing fight: {e}")
            self.state = AppState.IDLE
            self._update_ui_state()

    def _update_ui_state(self):
        """Update UI elements based on current state"""
        if self.state == AppState.IDLE:
            self.start_btn.config(state="normal", text="🟢 START RECORDING", style="Green.TButton")
            self.lose_btn.config(state="disabled")
            self.win_btn.config(state="disabled")
            self.delete_btn.config(state="normal")
            self.events_var.set("Events: 0")
            self.elapsed_var.set("00:00")
            self.boss_info_var.set("")
            self.keystroke_var.set("Press F1 to Start Recording")
            self.keystroke_label.config(foreground="#666")
            self.elapsed_label.config(foreground="#666")
            
        elif self.state == AppState.RECORDING:
            self.start_btn.config(state="normal", text="🔴 STOP RECORDING", style="Red.TButton")
            self.lose_btn.config(state="disabled")
            self.win_btn.config(state="disabled")
            self.delete_btn.config(state="normal")
            
            session_info = self.data_logger.get_session_info()
            if session_info:
                boss = session_info['boss']
                self.boss_info_var.set(f"Boss: {boss}")
                self.elapsed_label.config(foreground="#d32f2f")  # Red when recording
                
        elif self.state == AppState.ENDED:
            self.start_btn.config(state="disabled", text="🟢 START RECORDING", style="Green.TButton")
            self.lose_btn.config(state="normal")
            self.win_btn.config(state="normal")
            self.delete_btn.config(state="normal")
            self.keystroke_var.set("Fight ended - Mark Win/Loss")
            self.keystroke_label.config(foreground="#ff9800")
            self.elapsed_label.config(foreground="#666")
            
    def _update_telemetry(self):
        """Update telemetry display during recording"""
        if self.state == AppState.RECORDING:
            session_info = self.data_logger.get_session_info()
            if session_info:
                events = session_info['event_count']
                elapsed_ms = session_info['elapsed_ms']
                
                minutes = elapsed_ms // 60000
                seconds = (elapsed_ms // 1000) % 60
                
                self.events_var.set(f"Events: {events}")
                self.elapsed_var.set(f"{minutes:02d}:{seconds:02d}")
    
    def _update_keystroke_display(self, event_type: str, key: str):
        """Update the current keystroke display"""
        if self.state != AppState.RECORDING:
            return
            
        # Cancel any existing timeout
        if self.keystroke_timeout_id:
            self.root.after_cancel(self.keystroke_timeout_id)
        
        # Create a readable key name
        readable_key = self._format_key_name(key)
        
        # Show different colors for press vs release
        if event_type == "keydown":
            self.keystroke_var.set(f"🔽 {readable_key}")
            self.keystroke_label.config(foreground="#d32f2f")  # Red for press
        else:  # keyup
            self.keystroke_var.set(f"🔼 {readable_key}")
            self.keystroke_label.config(foreground="#1976d2")  # Blue for release
        
        # Set timeout to clear display after 1.5 seconds
        self.keystroke_timeout_id = self.root.after(1500, self._clear_keystroke_display)
    
    def _format_key_name(self, key: str) -> str:
        """Format key name for better readability"""
        # Convert special key names to more readable format
        key_mappings = {
            'Key.space': 'SPACE',
            'Key.left': 'LEFT ARROW',
            'Key.right': 'RIGHT ARROW', 
            'Key.up': 'UP ARROW',
            'Key.down': 'DOWN ARROW',
            'f': 'F (Shoot)',
            'a': 'A (Special)',
            'x': 'X (Lock)',
            'd': 'D (Dash)',
        }
        
        return key_mappings.get(key, key.upper())
    
    def _clear_keystroke_display(self):
        """Clear the keystroke display"""
        if self.state == AppState.RECORDING:
            self.keystroke_var.set("Recording... (F1 to stop)")
            self.keystroke_label.config(foreground="#666")
        self.keystroke_timeout_id = None
    
    def _load_existing_sessions(self):
        """Load existing sessions from CSV file to populate the history"""
        csv_path = self.data_logger.summaries_dir / self.data_logger.csv_filename
        if not csv_path.exists():
            return
        
        try:
            sessions = []
            with open(csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                # Get the last 5 sessions (most recent)
                all_sessions = list(reader)
                recent_sessions = all_sessions[-5:] if len(all_sessions) > 5 else all_sessions
                
                for row in recent_sessions:
                    session_entry = {
                        'fight_id': row['fight_id'],
                        'boss': row['boss'],
                        'outcome': row['outcome'].upper(),
                        'duration': f"{float(row['duration_s']):.1f}s",
                        'events': row['n_events'],
                        'timestamp': 'Loaded'  # Mark as loaded from file
                    }
                    sessions.append(session_entry)
            
            # Reverse to show most recent first
            self.session_history = list(reversed(sessions))
            self._update_history_display()
            print(f"Loaded {len(self.session_history)} existing sessions from CSV")
            
        except Exception as e:
            print(f"Error loading existing sessions: {e}")
            # Don't show error to user, just continue without loaded sessions
                
    def _toggle_pin(self):
        """Toggle always-on-top behavior"""
        self.root.attributes('-topmost', self.pin_var.get())
        
    def _add_to_history(self, session_entry):
        """Add a session to the history list and update the display"""
        # Add to beginning of list
        self.session_history.insert(0, session_entry)
        
        # Keep only last 5 sessions
        if len(self.session_history) > 5:
            self.session_history = self.session_history[:5]
            
        # Update the treeview
        self._update_history_display()
        
    def _update_history_display(self):
        """Update the history treeview with current session data"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # Add sessions to treeview
        for session in self.session_history:
            # Create display text with boss and timestamp
            display_text = f"{session['boss']} ({session['timestamp']})"
            
            # Parse duration to check for anomalies
            duration_str = session['duration']
            duration_value = float(duration_str.replace('s', ''))
            
            # Set tag for coloring based on duration anomalies
            if duration_value < 10 or duration_value > 150:
                tag = 'anomaly'  # Red for anomalous durations
            else:
                tag = 'normal'   # Normal color for regular durations
            
            self.history_tree.insert('', 'end', 
                                   text=display_text,
                                   values=(session['outcome'], session['duration'], session['events']),
                                   tags=(tag,))
        
        # Configure tags for coloring
        self.history_tree.tag_configure('anomaly', foreground='red')
        self.history_tree.tag_configure('normal', foreground='black')
        
    def _delete_selected_session(self):
        """Delete the selected session from both UI and data files"""
        # Get selected item from treeview
        selected_items = self.history_tree.selection()
        if not selected_items:
            print("No session selected to delete")
            return
            
        if self.state != AppState.IDLE:
            print("Cannot delete while recording")
            return
            
        try:
            # Get the selected item
            selected_item = selected_items[0]
            item_index = self.history_tree.index(selected_item)
            
            # Get the corresponding session from our history
            if item_index >= len(self.session_history):
                print("Invalid selection")
                return
                
            selected_session = self.session_history[item_index]
            fight_id = selected_session['fight_id']
            
            print(f"Attempting to delete session: {fight_id}")
            
            # Delete the raw data file
            raw_file = self.data_logger.raw_dir / f"{fight_id}.jsonl"
            print(f"Looking for raw file: {raw_file}")
            
            if raw_file.exists():
                raw_file.unlink()
                print(f"Deleted raw file: {raw_file}")
            else:
                print(f"Raw file not found: {raw_file}")
                
            # Remove from CSV summary
            csv_removed = self._remove_from_csv_summary(fight_id)
            
            # Remove from UI history
            self.session_history.pop(item_index)
            self._update_history_display()
            
            # Update boss counts after deletion
            self._update_boss_counts()
            
            if csv_removed:
                print(f"Deleted session: {fight_id}")
            else:
                print(f"Partially deleted: {fight_id} (CSV entry not found)")
            
            print(f"Successfully processed deletion for: {fight_id}")
            
        except Exception as e:
            print(f"Error deleting session: {str(e)}")
            print(f"Error deleting session: {e}")
            import traceback
            traceback.print_exc()
    
    def _remove_from_csv_summary(self, fight_id: str) -> bool:
        """Remove a fight from the CSV summary file"""
        csv_path = self.data_logger.summaries_dir / self.data_logger.csv_filename
        
        if not csv_path.exists():
            return False
        
        try:
            # Read all rows except the one to delete
            rows_to_keep = []
            found = False
            
            with open(csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row['fight_id'] == fight_id:
                        found = True
                        print(f"Found fight_id in CSV: {fight_id}")
                    else:
                        rows_to_keep.append(row)
            
            # Rewrite the CSV without the deleted row
            if found:
                with open(csv_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows_to_keep)
                print(f"Rewrote CSV with {len(rows_to_keep)} rows")
            
            return found
            
        except Exception as e:
            print(f"Error removing from CSV: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _count_boss_fights(self):
        """Count total fights for each boss from CSV data"""
        csv_path = self.data_logger.summaries_dir / self.data_logger.csv_filename
        boss_counts = defaultdict(int)
        
        if not csv_path.exists():
            return boss_counts
        
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    boss = row['boss']
                    boss_counts[boss] += 1
        except Exception as e:
            print(f"Error counting boss fights: {e}")
        
        return dict(boss_counts)
    
    def _update_boss_counts(self):
        """Update the boss fight counts and refresh the combo box"""
        self.boss_fight_counts = self._count_boss_fights()
        self._refresh_boss_combo()
    
    def _refresh_boss_combo(self):
        """Refresh the boss combo box with updated fight counts"""
        bosses = self.data_logger.config.get('bosses', [])
        boss_options = []
        
        for boss in bosses:
            count = self.boss_fight_counts.get(boss, 0)
            boss_options.append(f"{boss} ({count} fights)")
        
        # Store current selection to restore it
        current_boss = self._extract_boss_name(self.boss_var.get())
        
        # Update combo box values
        self.boss_combo['values'] = boss_options
        
        # Restore selection if possible
        for option in boss_options:
            if option.startswith(current_boss):
                self.boss_var.set(option)
                break
        else:
            # If current boss not found, set to first option
            if boss_options:
                self.boss_var.set(boss_options[0])
    
    def _extract_boss_name(self, display_text):
        """Extract the actual boss name from the display text (removes count)"""
        # Remove the count part like " (5 fights)"
        if '(' in display_text:
            return display_text.split(' (')[0]
        return display_text
    
    def _start_ui_updates(self):
        """Start the UI update loop"""
        self.update_thread_running = True
        
        def update_loop():
            while self.update_thread_running:
                try:
                    self.root.after(0, self._update_telemetry)
                    time.sleep(0.5)  # Update every 500ms
                except:
                    break
                    
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        
    def run(self):
        """Start the UI application"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_closing()
            
    def _on_closing(self):
        """Handle application closing"""
        self.update_thread_running = False
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            
        # Save any ongoing session
        if self.state == AppState.RECORDING:
            try:
                self.data_logger.end_fight("interrupted")
                print("Saved interrupted session")
            except:
                pass
                
        self.root.quit()
        self.root.destroy()


def main():
    """Main entry point"""
    app = CupheadLoggerUI()
    app.run()


if __name__ == "__main__":
    main()