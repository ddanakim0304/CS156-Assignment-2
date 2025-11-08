from pynput import keyboard
from pynput.keyboard import Key

class KeyboardListener:
    """Handles global keyboard event listening for gameplay and session markers."""
    
    # Define keys to track for gameplay
    GAMEPLAY_KEYS = {
        'a', 'd', 'f', 'x', Key.space, 
        Key.up, Key.down, Key.left, Key.right
    }

    def __init__(self, key_callback, marker_callback, session_toggle_callback):
        self.key_callback = key_callback
        self.marker_callback = marker_callback
        self.session_toggle_callback = session_toggle_callback
        
        self.listener = None
        self._pressed_keys = set()

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
        """Convert pynput key object to a simple, consistent string."""
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        return str(key)

    def _on_press(self, key):
        # Prevent key-repeat events from being logged
        if key in self._pressed_keys:
            return
        self._pressed_keys.add(key)
        
        # MODIFIED: The entire hotkey logic is changed to use number keys
        # This is a safe way to get the character of a key, if it exists
        key_char = getattr(key, 'char', None)

        # --- Handle Hotkeys ---
        if key_char == '0':
            self.session_toggle_callback()
            return # IMPORTANT: Return to not log hotkeys as gameplay
        if key_char == '8':
            self.marker_callback("fight_start")
            return
        if key_char == '9':
            self.marker_callback("fight_end")
            return

        # --- Handle Gameplay Keys ---
        # Check against both character keys and special Key objects
        if key in self.GAMEPLAY_KEYS or (key_char and key_char in self.GAMEPLAY_KEYS):
            self.key_callback('keydown', self._normalize_key(key))

    def _on_release(self, key):
        self._pressed_keys.discard(key)

        # --- Handle Gameplay Keys ---
        key_char = getattr(key, 'char', None)
        if key in self.GAMEPLAY_KEYS or (key_char and key_char in self.GAMEPLAY_KEYS):
            self.key_callback('keyup', self._normalize_key(key))