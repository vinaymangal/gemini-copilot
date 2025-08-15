import tkinter as tk
from tkinter import scrolledtext, filedialog
import keyboard
from PIL import Image, ImageDraw
import pystray
import threading
import os
import PyPDF2  # <-- CORRECTED LINE
import docx
import openpyxl

# --- Global variables ---
window = None
text_area = None

# --- File Reading Functions ---

def read_txt(filepath):
    """Reads content from a .txt file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def read_pdf(filepath):
    """Reads content from a .pdf file."""
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)  # <-- CORRECTED LINE
            content = ""
            for page in reader.pages:
                content += page.extract_text() or ""
            return content
    except Exception as e:
        return f"Error reading PDF: {e}"

def read_docx(filepath):
    """Reads content from a .docx file."""
    doc = docx.Document(filepath)
    content = "\n".join([para.text for para in doc.paragraphs])
    return content

def read_xlsx(filepath):
    """Reads content from a .xlsx file."""
    workbook = openpyxl.load_workbook(filepath)
    content = ""
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        content += f"--- Sheet: {sheet_name} ---\n"
        for row in sheet.iter_rows(values_only=True):
            content += ", ".join([str(cell) if cell is not None else "" for cell in row]) + "\n"
    return content

def read_file(filepath):
    """
    Reads a file by detecting its extension and calling the appropriate reader function.
    """
    if not text_area:
        return

    text_area.delete('1.0', tk.END) # Clear previous content
    try:
        filename = os.path.basename(filepath)
        text_area.insert(tk.INSERT, f"Reading file: {filename}\n" + "="*30 + "\n\n")
        
        _, extension = os.path.splitext(filepath)
        extension = extension.lower()

        content = ""
        if extension == '.txt':
            content = read_txt(filepath)
        elif extension == '.pdf':
            content = read_pdf(filepath)
        elif extension == '.docx':
            content = read_docx(filepath)
        elif extension == '.xlsx':
            content = read_xlsx(filepath)
        else:
            content = f"Unsupported file type: {extension}"
        
        text_area.insert(tk.INSERT, content)

    except Exception as e:
        text_area.insert(tk.INSERT, f"An error occurred: {e}")

def open_file_dialog():
    """Opens a file dialog to select a file and then reads it."""
    filepath = filedialog.askopenfilename()
    if filepath:
        # Run file reading in a separate thread to keep the UI responsive
        threading.Thread(target=read_file, args=(filepath,), daemon=True).start()

# --- Window and Tray Management ---

def create_image():
    width = 64; height = 64; color1 = "black"; color2 = "white"
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image

def show_window():
    if window:
        window.deiconify(); window.lift(); window.focus_force()

def hide_window():
    if window:
        window.withdraw()

def toggle_window():
    if window:
        if window.state() == "withdrawn": show_window()
        else: hide_window()

def quit_app(icon, item):
    icon.stop()
    if window: window.quit()

def setup_tray():
    image = create_image()
    menu = (pystray.MenuItem("Show/Hide", toggle_window, default=True),
            pystray.MenuItem("Quit", quit_app))
    icon = pystray.Icon("gemini_copilot", image, "Gemini Copilot", menu)
    icon.run()

def main():
    global window, text_area
    window = tk.Tk()
    window.title("Gemini Copilot")
    window.geometry("600x500")
    window.protocol("WM_DELETE_WINDOW", hide_window)

    main_frame = tk.Frame(window, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Create a frame for buttons
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(0, 10))

    choose_file_button = tk.Button(button_frame, text="Choose File", font=("Segoe UI", 10), command=open_file_dialog)
    choose_file_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

    send_button = tk.Button(button_frame, text="Send to Gemini", font=("Segoe UI", 10))
    send_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, font=("Segoe UI", 10))
    text_area.pack(fill=tk.BOTH, expand=True)
    text_area.insert(tk.INSERT, "Welcome! Choose a file or type a question.")

    hide_window()
    window.mainloop()

if __name__ == "__main__":
    keyboard.add_hotkey("ctrl+space", toggle_window)
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    main()