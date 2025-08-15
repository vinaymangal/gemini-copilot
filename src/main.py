import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk
import sv_ttk
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
import extract_msg
import email
import queue

# --- Load API Key and Configure Gemini ---
load_dotenv() 
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("CRITICAL ERROR: GEMINI_API_KEY not found.")

# --- Global variables ---
window = None
text_area = None
prompt_entry = None
update_queue = queue.Queue()
processed_content = "" # Stores the combined text from all successfully read files

# --- Gemini API Function ---
def call_gemini(instruction):
    global processed_content
    if not text_area or not api_key: 
        messagebox.showerror("API Key Error", "Gemini API Key not found.")
        return
    
    # Use the stored content from the file processing
    if not processed_content.strip():
        messagebox.showerror("Error", "No file content has been processed. Please choose a file or folder first.")
        return

    if not instruction or not instruction.strip():
        messagebox.showerror("Error", "Please provide an instruction in the prompt box.")
        return

    system_instruction = "You are Vinay's Windows Copilot. Be concise, actionable, and format your output clearly."
    final_prompt = f"{system_instruction}\n\n---INSTRUCTION---\n{instruction}\n\n---CONTENT---\n{processed_content}"
    
    text_area.insert(tk.END, "\n\n====================\nAsking Gemini... Please wait.\n")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(final_prompt)
        # We append the response instead of replacing the log
        text_area.insert(tk.END, "--- GEMINI RESPONSE ---\n" + response.text)
    except Exception as e:
        text_area.insert(tk.END, f"An error occurred with the Gemini API:\n{e}")

def send_to_gemini_threaded(instruction):
    threading.Thread(target=call_gemini, args=(instruction,), daemon=True).start()

def custom_prompt_action():
    """Gets instruction from the custom prompt box and calls Gemini."""
    if prompt_entry:
        instruction = prompt_entry.get()
        send_to_gemini_threaded(instruction)

# --- File/Folder Readers ---
FILE_HANDLERS = {
    '.txt': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.py': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.js': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.html': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.css': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.pdf': lambda p: "".join(page.extract_text() or "" for page in PyPDF2.PdfReader(open(p, 'rb')).pages),
    '.docx': lambda p: "\n".join(para.text for para in docx.Document(p).paragraphs),
    '.msg': lambda p: f"From: {extract_msg.Message(p).sender}\nTo: {extract_msg.Message(p).to}\nSubject: {extract_msg.Message(p).subject}\nDate: {extract_msg.Message(p).date}\n\n{extract_msg.Message(p).body}",
    '.eml': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read()
}

def process_path_threaded(path):
    """Background thread for reading files and sending log updates."""
    combined_content_list = []
    try:
        if os.path.isfile(path):
            filename = os.path.basename(path)
            _, ext = os.path.splitext(path)
            handler = FILE_HANDLERS.get(ext.lower())
            if handler:
                try:
                    content = handler(path)
                    if content.strip():
                        combined_content_list.append(content)
                        update_queue.put(("log", f"Reading {filename}... OK\n"))
                    else:
                        update_queue.put(("log", f"Reading {filename}... SKIPPED (File is empty or contains no text)\n"))
                except Exception as e:
                    update_queue.put(("log", f"Reading {filename}... FAILED ({e})\n"))
            else:
                update_queue.put(("log", f"Reading {filename}... SKIPPED (Unsupported file type)\n"))
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    filename = os.path.basename(file)
                    filepath = os.path.join(root, file)
                    _, ext = os.path.splitext(file)
                    if ext.lower() in FILE_HANDLERS:
                        try:
                            content = FILE_HANDLERS[ext.lower()](filepath)
                            if content.strip():
                                combined_content_list.append(f"--- Content of {filename} ---\n{content}\n\n")
                                update_queue.put(("log", f"Reading {filename}... OK\n"))
                            else:
                                update_queue.put(("log", f"Reading {filename}... SKIPPED (File is empty or contains no text)\n"))
                        except Exception as e:
                            update_queue.put(("log", f"Reading {filename}... FAILED ({e})\n"))
                    else:
                        update_queue.put(("log", f"Reading {filename}... SKIPPED (Unsupported file type)\n"))
    except Exception as e:
        update_queue.put(("log", f"A critical error occurred: {e}\n"))
    
    final_content = "".join(combined_content_list)
    update_queue.put(("finished", final_content))

def check_update_queue():
    """Checks queue for updates from the background thread and updates the UI."""
    global processed_content
    try:
        while not update_queue.empty():
            msg_type, data = update_queue.get_nowait()
            if msg_type == "log":
                text_area.insert(tk.END, data)
                text_area.see(tk.END) # Auto-scroll to the bottom
            elif msg_type == "finished":
                processed_content = data
                text_area.insert(tk.END, "\n--- Analysis Complete. Ready for instructions. ---\n")
                text_area.see(tk.END)
    finally:
        window.after(100, check_update_queue)

def start_processing(path):
    """Clears UI and starts the background file reading thread."""
    global processed_content
    processed_content = ""
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", f"Starting analysis of: {path}\n" + "="*40 + "\n")
    threading.Thread(target=process_path_threaded, args=(path,), daemon=True).start()

def open_file_dialog():
    filepath = filedialog.askopenfilename()
    if filepath: start_processing(filepath)

def open_folder_dialog():
    folderpath = filedialog.askdirectory()
    if folderpath: start_processing(folderpath)

def load_path_from_startup(path):
    if window:
        show_window()
        start_processing(path)

# --- UI Helper Functions ---
def copy_to_clipboard():
    if text_area:
        window.clipboard_clear()
        window.clipboard_append(text_area.get("1.0", tk.END))
        messagebox.showinfo("Copied", "Log & Response copied to clipboard.")
def clear_text_area():
    global processed_content
    if text_area:
        text_area.delete("1.0", tk.END)
        processed_content = ""

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
    global window, text_area, prompt_entry
    window = tk.Tk()
    window.title("Gemini Copilot")
    window.geometry("800x650") # Increased height for prompt box
    window.protocol("WM_DELETE_WINDOW", hide_window)

    sv_ttk.set_theme("dark")

    main_frame = ttk.Frame(window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # --- Top Frame for Browse and Settings ---
    top_frame = ttk.Frame(main_frame)
    top_frame.pack(fill=tk.X, pady=(0, 10))
    ttk.Button(top_frame, text="Choose File...", command=open_file_dialog).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    ttk.Button(top_frame, text="Choose Folder...", command=open_folder_dialog).pack(side=tk.LEFT, expand=True, fill=tk.X)
    ttk.Button(top_frame, text="Toggle Theme", command=sv_ttk.toggle_theme).pack(side=tk.LEFT, padx=(5, 0))

    # --- Text Area is now the Log Viewer ---
    text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=("Segoe UI", 10), height=15)
    text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    text_area.insert(tk.INSERT, "Welcome! Choose a file/folder to begin analysis.")

    # --- NEW Prompt Frame ---
    prompt_frame = ttk.Frame(main_frame)
    prompt_frame.pack(fill=tk.X, pady=(0, 10))
    prompt_entry = ttk.Entry(prompt_frame, font=("Segoe UI", 10))
    prompt_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    prompt_entry.insert(0, "Summarize the content above.") # Default prompt
    ttk.Button(prompt_frame, text="Ask Gemini", command=custom_prompt_action, style="Accent.TButton").pack(side=tk.LEFT)

    # --- Utility Frame ---
    util_frame = ttk.Frame(main_frame)
    util_frame.pack(fill=tk.X)
    ttk.Button(util_frame, text="Copy Log", command=copy_to_clipboard).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    ttk.Button(util_frame, text="Clear", command=clear_text_area).pack(side=tk.LEFT, expand=True, fill=tk.X)

    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
        window.after(100, load_path_from_startup, path_arg)
    else:
        hide_window()
    
    window.after(100, check_update_queue)
    window.mainloop()

if __name__ == "__main__":
    keyboard.add_hotkey("ctrl+space", toggle_window)
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    main()