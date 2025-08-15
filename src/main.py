import tkinter as tk
from tkinter import scrolledtext
import keyboard
from PIL import Image, ImageDraw
import pystray
import threading

# --- Global variable for the window ---
window = None

def create_image():
    """Creates a simple placeholder image for the tray icon."""
    width = 64
    height = 64
    color1 = "black"
    color2 = "white"
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 2, 0, width, height // 2),
        fill=color2)
    dc.rectangle(
        (0, height // 2, width // 2, height),
        fill=color2)
    return image

def show_window():
    """Shows the main window."""
    if window:
        window.deiconify() # Un-hides the window
        window.lift()
        window.focus_force()

def hide_window():
    """Hides the main window."""
    if window:
        window.withdraw() # Hides the window

def toggle_window():
    """Shows the window if it's hidden, hides it if it's visible."""
    if window:
        if window.state() == "withdrawn":
            show_window()
        else:
            hide_window()

def quit_app(icon, item):
    """Stops the tray icon and closes the app."""
    icon.stop()
    if window:
        window.quit()

def setup_tray():
    """Sets up and runs the system tray icon."""
    image = create_image()
    menu = (pystray.MenuItem("Show/Hide", toggle_window, default=True),
            pystray.MenuItem("Quit", quit_app))
    icon = pystray.Icon("gemini_copilot", image, "Gemini Copilot", menu)
    icon.run()

def main():
    """Creates and runs the main application window."""
    global window
    window = tk.Tk()
    window.title("Gemini Copilot")
    window.geometry("600x400")

    # Hide the window when the user clicks the 'X' button, instead of closing it.
    window.protocol("WM_DELETE_WINDOW", hide_window)

    main_frame = tk.Frame(window, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, font=("Segoe UI", 10))
    text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    text_area.insert(tk.INSERT, "Welcome! Press Ctrl+Space to show/hide this window.")

    send_button = tk.Button(main_frame, text="Send", font=("Segoe UI", 10))
    send_button.pack(fill=tk.X)

    # Initially hide the window
    hide_window()

    # Start the GUI event loop
    window.mainloop()

if __name__ == "__main__":
    # Set up the hotkey
    keyboard.add_hotkey("ctrl+space", toggle_window)

    # Run the system tray icon in a separate thread
    # This is important so the tray icon and the GUI don't block each other
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    # Run the main GUI
    main()