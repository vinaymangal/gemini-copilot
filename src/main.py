import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk # The new library for our modern UI
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

# --- Global variables for UI and Logic ---
window = None
log_textbox = None # Renamed from text_area for clarity
prompt_entry = None
update_queue = queue.Queue()
processed_content = "" # Stores the combined text from all successfully read files

# --- Gemini API Function (Backend Logic - Unchanged) ---
def call_gemini(instruction):
    global processed_content
    if not log_textbox or not api_key: 
        messagebox.showerror("API Key Error", "Gemini API Key not found.")
        return
    if not processed_content.strip():
        messagebox.showerror("Error", "No file content has been processed. Please choose a file or folder first.")
        return
    if not instruction or not instruction.strip():
        messagebox.showerror("Error", "Please provide an instruction in the prompt box.")
        return

    system_instruction = "You are Vinay's Windows Copilot. Be concise, actionable, and format your output clearly."
    final_prompt = f"{system_instruction}\n\n---INSTRUCTION---\n{instruction}\n\n---CONTENT---\n{processed_content}"
    
    log_textbox.insert(tk.END, "\n\n====================\nAsking Gemini... Please wait.\n")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(final_prompt)
        log_textbox.insert(tk.END, "--- GEMINI RESPONSE ---\n" + response.text)
    except Exception as e:
        log_textbox.insert(tk.END, f"An error occurred with the Gemini API:\n{e}")

def send_to_gemini_threaded(instruction):
    threading.Thread(target=call_gemini, args=(instruction,), daemon=True).start()

def custom_prompt_action():
    if prompt_entry:
        instruction = prompt_entry.get()
        send_to_gemini_threaded(instruction)

# --- File/Folder Readers (Backend Logic - Unchanged) ---
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
    # ... (This function is unchanged)
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
    # ... (This function is unchanged)
    global processed_content
    try:
        while not update_queue.empty():
            msg_type, data = update_queue.get_nowait()
            if msg_type == "log":
                log_textbox.insert(tk.END, data)
                log_textbox.see(tk.END)
            elif msg_type == "finished":
                processed_content = data
                log_textbox.insert(tk.END, "\n--- Analysis Complete. Ready for instructions. ---\n")
                log_textbox.see(tk.END)
    finally:
        if window: window.after(100, check_update_queue)

def start_processing(path):
    # ... (This function is unchanged)
    global processed_content
    processed_content = ""
    log_textbox.delete("1.0", tk.END)
    log_textbox.insert("1.0", f"Starting analysis of: {path}\n" + "="*40 + "\n")
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
    if log_textbox:
        window.clipboard_clear()
        window.clipboard_append(log_textbox.get("1.0", tk.END))
        messagebox.showinfo("Copied", "Log & Response copied to clipboard.")
def clear_text_area():
    global processed_content
    if log_textbox:
        log_textbox.delete("1.0", tk.END)
        processed_content = ""

# --- Window and Tray Management (Backend Logic - Unchanged) ---
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

# --- NEW: Main UI Function using CustomTkinter ---
def main():
    global window, log_textbox, prompt_entry

    # --- Design Choice: Initial Theme Setup ---
    # Sets the default look and feel of the application.
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue") # Matches Windows 11 accent color

    # --- Design Choice: Main Application Window ---
    # Using CTk object for the main window provides all the modern styling.
    window = ctk.CTk()
    window.title("Gemini Copilot")
    window.geometry("1100x720")
    window.protocol("WM_DELETE_WINDOW", hide_window)

    # --- Design Choice: Grid Layout ---
    # A grid is used for the main layout to create the responsive sidebar and main content area.
    # Column 0 is the sidebar, Column 1 is the main content and will expand.
    window.grid_columnconfigure(1, weight=1)
    window.grid_rowconfigure(0, weight=1)

    # --- Design Choice: Left Navigation Panel ---
    # A CTkFrame is used to group the navigation elements.
    # It has a fixed width and is set to span the full height of the window.
    nav_frame = ctk.CTkFrame(window, width=200, corner_radius=0)
    nav_frame.grid(row=0, column=0, sticky="nsew")
    nav_frame.grid_rowconfigure(4, weight=1) # Pushes settings to the bottom

    # --- Design Choice: Typography and Branding ---
    # A bold, larger font for the title gives the app a clear identity.
    app_title = ctk.CTkLabel(nav_frame, text="Gemini Copilot", font=ctk.CTkFont(family="Segoe UI Variable", size=20, weight="bold"))
    app_title.grid(row=0, column=0, padx=20, pady=(20, 10))

    # --- Design Choice: Navigation Buttons ---
    # Consistent buttons for primary actions like file/folder selection.
    file_button = ctk.CTkButton(nav_frame, text="Choose File", command=open_file_dialog)
    file_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
    folder_button = ctk.CTkButton(nav_frame, text="Choose Folder", command=open_folder_dialog)
    folder_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

    # --- Design Choice: Settings Section ---
    # Grouping settings at the bottom of the nav bar is a common and clean UX pattern.
    settings_label = ctk.CTkLabel(nav_frame, text="Settings", font=ctk.CTkFont(family="Segoe UI Variable", size=14, weight="bold"))
    settings_label.grid(row=5, column=0, padx=20, pady=(20, 0))
    
    theme_label = ctk.CTkLabel(nav_frame, text="Appearance:")
    theme_label.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="w")
    theme_menu = ctk.CTkOptionMenu(nav_frame, values=["Dark", "Light", "System"], command=ctk.set_appearance_mode)
    theme_menu.grid(row=7, column=0, padx=20, pady=10, sticky="ew")

    # --- Design Choice: Main Content Area ---
    # This frame holds all the interactive elements. It's transparent to blend with the window.
    main_content_frame = ctk.CTkFrame(window, corner_radius=8, fg_color="transparent")
    main_content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
    main_content_frame.grid_columnconfigure(0, weight=1)
    main_content_frame.grid_rowconfigure(0, weight=1) # Log area expands

    # --- Design Choice: Log/Response Textbox ---
    # CTkTextbox provides the modern look with rounded corners and proper scrollbars.
    log_textbox = ctk.CTkTextbox(main_content_frame, font=("Segoe UI", 13), corner_radius=8)
    log_textbox.grid(row=0, column=0, columnspan=2, sticky="nsew")
    log_textbox.insert("0.0", "Welcome! Choose a file or folder from the left panel to begin analysis.")

    # --- Design Choice: Prompt Entry and Button ---
    # A dedicated entry with placeholder text guides the user. The accent color on the button
    # signifies it's the primary action in this view.
    prompt_entry = ctk.CTkEntry(main_content_frame, placeholder_text="Summarize the content, or type your custom instruction here...", height=35, corner_radius=8)
    prompt_entry.grid(row=1, column=0, padx=(0, 10), pady=10, sticky="ew")
    ask_button = ctk.CTkButton(main_content_frame, text="Ask Gemini", command=custom_prompt_action, height=35, corner_radius=8)
    ask_button.grid(row=1, column=1, pady=10, sticky="e")

    # --- Design Choice: Utility Buttons ---
    # Secondary actions like Copy and Clear are placed at the bottom.
    util_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent")
    util_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
    util_frame.grid_columnconfigure(0, weight=1)
    copy_button = ctk.CTkButton(util_frame, text="Copy Log", command=copy_to_clipboard, fg_color="gray50", hover_color="gray60")
    copy_button.grid(row=0, column=0, padx=(0, 5), sticky="e")
    clear_button = ctk.CTkButton(util_frame, text="Clear", command=clear_text_area, fg_color="gray50", hover_color="gray60")
    clear_button.grid(row=0, column=1, padx=(5, 0), sticky="w")

    # --- Startup Logic ---
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