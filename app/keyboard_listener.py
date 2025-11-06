#!/usr/bin/env python3
"""
Cuphead Boss Keystroke Data Logger - Keyboard Event Handler
"""
import threading
from typing import Callable, Set, Dict
from pynput import keyboard
from pynput.keyboard import Key


class KeyboardListener:
    """Handles global keyboard event listening"""
    # Keys to monitor for gameplay
    GAMEPLAY_KEYS = {
        Key.left: 'left',
        Key.right: 'right', 
        Key.up: 'up',
        Key.down: 'down', 
        Key.space: 'jump',
        'f': 'shoot',
        'a': 'special',
        'x': 'lock',
        'd': 'dash',
    }
    
    # Hotkeys to ignore from gameplay logging
    HOTKEYS = {Key.f1, Key.f2, Key.f8, Key.f9}
    
    # Keys to completely ignore
    IGNORE_KEYS = {
        Key.cmd, Key.cmd_l, Key.cmd_r,
        Key.ctrl, Key.ctrl_l, Key.ctrl_r,
        Key.alt, Key.alt_l, Key.alt_r,
        Key.shift_l, Key.shift_r,
        Key.caps_lock, Key.tab
    }
    
    def __init__(self, 
                 event_callback: Callable[[str, str], None] = None,
                 hotkey_callbacks: Dict[str, Callable] = None):
        """
        Initialize keyboard listener
        
        Args:
            event_callback: Function to call for gameplay events (event_type, key_name)
            hotkey_callbacks: Dict mapping hotkey names to callback functions
        """
        self.event_callback = event_callback
        self.hotkey_callbacks = hotkey_callbacks or {}
        
        self.listener = None
        self.is_running = False
        self._pressed_keys: Set = set()
        
    def start(self):
        """Start the keyboard listener in a background thread"""
        if self.is_running:
            return
            
        self.is_running = True
        self.listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.listener.start()
        
    def stop(self):
        """Stop the keyboard listener"""
        self.is_running = False
        if self.listener:
            self.listener.stop()
            self.listener = None
            
    def _normalize_key(self, key) -> str:
        """Convert key to consistent string representation"""
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        elif isinstance(key, Key):
            return f"Key.{key.name}"
        else:
            return str(key)
            
    def _is_gameplay_key(self, key) -> bool:
        """Check if key should be logged as gameplay event"""
        # Skip hotkeys
        if key in self.HOTKEYS:
            return False
            
        # Skip ignore keys
        if key in self.IGNORE_KEYS:
            return False
            
        # Check if it's a special key (like arrows, space)
        if key in self.GAMEPLAY_KEYS:
            return True
            
        # Check character keys
        if hasattr(key, 'char') and key.char:
            char_key = key.char.lower()
            return char_key in self.GAMEPLAY_KEYS
            
        return False
        
    def _get_gameplay_action(self, key) -> str:
        """Get the gameplay action name for a key"""
        # Check special keys first
        if key in self.GAMEPLAY_KEYS:
            return self.GAMEPLAY_KEYS[key]
        # Check character keys
        elif hasattr(key, 'char') and key.char:
            char_key = key.char.lower()
            if char_key in self.GAMEPLAY_KEYS:
                return self.GAMEPLAY_KEYS[char_key]
            return char_key
        return self._normalize_key(key)
        
    def _on_key_press(self, key):
        """Handle key press events"""
        try:
            # Prevent key repeat events
            if key in self._pressed_keys:
                return
            self._pressed_keys.add(key)
            
            # Handle hotkeys
            if key == Key.f1 and 'start' in self.hotkey_callbacks:
                self.hotkey_callbacks['start']()
            elif key == Key.f2 and 'end' in self.hotkey_callbacks:
                self.hotkey_callbacks['end']()
            elif key == Key.f8 and 'lose' in self.hotkey_callbacks:
                self.hotkey_callbacks['lose']()
            elif key == Key.f9 and 'win' in self.hotkey_callbacks:
                self.hotkey_callbacks['win']()
            
            # Handle gameplay events
            elif self._is_gameplay_key(key) and self.event_callback:
                action = self._get_gameplay_action(key)
                key_str = self._normalize_key(key)
                self.event_callback('keydown', f"{key_str}")
                
        except Exception as e:
            print(f"Error in key press handler: {e}")
            
    def _on_key_release(self, key):
        """Handle key release events"""
        try:
            # Remove from pressed keys
            self._pressed_keys.discard(key)
            
            # Only log gameplay key releases (ignore hotkeys)
            if self._is_gameplay_key(key) and self.event_callback:
                key_str = self._normalize_key(key)
                self.event_callback('keyup', f"{key_str}")
                
        except Exception as e:
            print(f"Error in key release handler: {e}")


# Test function for the keyboard listener
if __name__ == "__main__":
    def test_event_callback(event_type, key):
        print(f"Event: {event_type} - Key: {key}")
    
    def test_hotkey():
        print("Hotkey pressed!")
    
    listener = KeyboardListener(
        event_callback=test_event_callback,
        hotkey_callbacks={'start': test_hotkey}
    )
    
    print("Starting keyboard listener test. Press keys to see events.")
    print("Press Ctrl+C to exit.")
    
    listener.start()
    
    try:
        import time
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping listener...")
        listener.stop()