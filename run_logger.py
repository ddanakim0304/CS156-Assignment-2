#!/usr/bin/env python3
"""
Launcher script for the Cuphead Session Recorder UI (Assignment 2)
"""
import sys
import os

# Add the app directory to Python path
app_dir = os.path.join(os.path.dirname(__file__), 'app')
sys.path.insert(0, app_dir)

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        import pynput
        import tkinter
        import cv2
        import mss
        import numpy
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install requirements: pip install pynput opencv-python mss numpy")
        return False

def main():
    """Main launcher function"""
    print("Cuphead Imitation Learning - Session Recorder")
    print("============================================")
    
    if not check_dependencies():
        sys.exit(1)
    
    try:
        from main import SessionRecorderUI
        
        print("Starting Session Recorder UI...")
        print("Note: On macOS, you may need to grant Accessibility and Screen Recording permissions.")
        print("Press Ctrl+C in the terminal to exit.")
        
        app = SessionRecorderUI()
        app.run()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()