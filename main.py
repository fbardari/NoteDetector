"""
Real-Time Note Detector with Graphical User Interface.

Dependencies: pip install numpy sounddevice    (tkinter is included with Python)
Usage:        python main.py
"""

import tkinter as tk
from note_detector.gui import App


def main():
    """Application entry point function."""
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()