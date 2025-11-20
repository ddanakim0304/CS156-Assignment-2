# FILE: app/keyboard_listener.py (CORRECTED with pause/resume)
from pynput import keyboard
from pynput.keyboard import Key

class KeyboardListener:
    """Handles global keyboard event listening for gameplay and session markers."""
    
    GAMEPLAY_KEYS = {'d', 'f', Key.space, Key.up, Key.down, Key.left, Key.right}

    def __init__(self, key_callback, marker_callback, session_toggle_callback):
        self.key_callback = key_callback
        self.marker_callback = marker_callback
        self.session_toggle_callback = session_toggle_callback
        
        self.listener = None
        self._pressed_keys = set()
        self.is_paused = False # NEW: Add a pause flag

    # NEW: Method to pause the listener
    def pause(self):
        self.is_paused = True

    # NEW: Method to resume the listener
    def resume(self):
        self.is_paused = False

    def start(self):
        if not self.listener:
            self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    @staticmethod
    def _normalize_key(key):
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        return str(key)

    def _on_press(self, key):
        # MODIFIED: Check if paused at the very beginning
        if self.is_paused:
            return

        if key in self._pressed_keys:
            return
        self._pressed_keys.add(key)
        
        key_char = getattr(key, 'char', None)

        if key_char == '1':
            self.session_toggle_callback()
            return 
        if key_char == '8':
            self.marker_callback("fight_start")
            return
        if key_char == '9':
            self.marker_callback("fight_end")
            return

        if key in self.GAMEPLAY_KEYS or (key_char and key_char in self.GAMEPLAY_KEYS):
            self.key_callback('keydown', self._normalize_key(key))

    def _on_release(self, key):
        # MODIFIED: Also check if paused on release
        if self.is_paused:
            return

        self._pressed_keys.discard(key)
        key_char = getattr(key, 'char', None)
        if key in self.GAMEPLAY_KEYS or (key_char and key_char in self.GAMEPLAY_KEYS):
            self.key_callback('keyup', self._normalize_key(key))