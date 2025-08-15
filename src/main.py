import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import keyboard
from PIL import Image, ImageDraw
import pystray
import threading
import os
import sys
import PyPDF2
import docx
import openpyxl
from dotenv import load_dotenv
import google.generativeai as genai

# --- Load API Key and Configure Gemini ---
# This simplified line works for both running the script and the final .exe
load_dotenv() 

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    # This message will appear in the terminal if the key isn't found.
    print("CRITICAL ERROR: GEMINI_API_KEY not found. Ensure a .env file is next to the .exe or in the project root.")

# --- Global variables ---
window = None
text_area = None
original_content = ""

# --- Gemini API Function ---
def call_gemini(prompt_instruction):
    global original_content
    if not text_area or not api_key: 
        messagebox.showerror("API Key Error", "Gemini API Key not found. Please check your .env file.")
        return
    content_to_process = original_content if original_content else text_area.get("1.0", tk.END)
    if not content_to_process.strip():
        messagebox.showerror("Error", "There is no content to process.")
        return
    system_instruction = "You are Vinay's Windows Copilot. Be concise, actionable, and format your output clearly."
    final_prompt = f"{system_instruction}\n\n---INSTRUCTION---\n{prompt_instruction}\n\n---CONTENT---\n{content_to_process}"
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", "Asking Gemini... Please wait.")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(final_prompt)
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", response.text)
    except Exception as e:
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", f"An error occurred with the Gemini API:\n{e}")

def send_to_gemini_threaded(instruction):
    threading.Thread(target=call_gemini, args=(instruction,), daemon=True).start()

# --- File Reading Functions ---
def read_file(filepath):
    global original_content
    if not text_area: return
    text_area.delete('1.0', tk.END)
    try:
        filename = os.path.basename(filepath)
        text_area.insert(tk.INSERT, f"Reading file: {filename}\n" + "="*30 + "\n\n")
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        content = {
            '.txt': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
            '.pdf': lambda p: "".join(page.extract_text() or "" for page in PyPDF2.PdfReader(open(p, 'rb')).pages),
            '.docx': lambda p: "\n".join(para.text for para in docx.Document(p).paragraphs),
            '.xlsx': read_xlsx
        }.get(ext, lambda p: f"Unsupported file type: {ext}")(filepath)
        text_area.insert(tk.INSERT, content)
        original_content = content
    except Exception as e:
        original_content = ""
        text_area.insert(tk.INSERT, f"An error occurred reading the file: {e}")

def read_xlsx(filepath):
    workbook = openpyxl.load_workbook(filepath)
    content = ""
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        content += f"--- Sheet: {sheet_name} ---\n"
        for row in sheet.iter_rows(values_only=True):
            content += ", ".join([str(cell) if cell is not None else "" for cell in row]) + "\n"
    return content

def open_file_dialog():
    filepath = filedialog.askopenfilename()
    if filepath: threading.Thread(target=read_file, args=(filepath,), daemon=True).start()

def load_file_from_startup(filepath):
    if window:
        show_window()
        read_file(filepath)

# --- Window and Tray Management ---
def create_image():
    width=64; height=64; color1="black"; color2="white"
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image
def show_window():
    if window: window.deiconify(); window.lift(); window.focus_force()
def hide_window():
    if window: window.withdraw()
def toggle_window():
    if window and window.state() == "withdrawn": show_window()
    elif window: hide_window()
def quit_app(icon, item):
    icon.stop()
    if window: window.quit()
def setup_tray():
    image = create_image()
    menu = (pystray.MenuItem("Show/Hide", toggle_window, default=True), pystray.MenuItem("Quit", quit_app))
    icon = pystray.Icon("gemini_copilot", image, "Gemini Copilot", menu)
    icon.run()

def main():
    global window, text_area
    window = tk.Tk()
    window.title("Gemini Copilot")
    window.geometry("700x500")
    window.protocol("WM_DELETE_WINDOW", hide_window)
    main_frame = tk.Frame(window, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    action_frame = tk.Frame(main_frame)
    action_frame.pack(fill=tk.X, pady=(0, 10))
    summarize_button = tk.Button(action_frame, text="Summarize", font=("Segoe UI", 10), command=lambda: send_to_gemini_threaded("Summarize the following content."))
    summarize_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    key_points_button = tk.Button(action_frame, text="Key Points", font=("Segoe UI", 10), command=lambda: send_to_gemini_threaded("Extract the key points from the following content as a bulleted list."))
    key_points_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    actions_button = tk.Button(action_frame, text="Next Actions", font=("Segoe UI", 10), command=lambda: send_to_gemini_threaded("List the potential next actions or to-do items from the following content."))
    actions_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 0))
    file_button = tk.Button(main_frame, text="Choose File...", font=("Segoe UI", 10), command=open_file_dialog)
    file_button.pack(fill=tk.X, pady=(0, 10))
    text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, font=("Segoe UI", 10))
    text_area.pack(fill=tk.BOTH, expand=True)
    text_area.insert(tk.INSERT, "Welcome! Choose a file and then select an action above.")
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        window.after(100, load_file_from_startup, filepath)
    else:
        hide_window()

    window.mainloop()

if __name__ == "__main__":
    keyboard.add_hotkey("ctrl+space", toggle_window)
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    main()