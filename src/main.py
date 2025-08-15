import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import keyboard
from PIL import Image, ImageDraw
import pystray
import threading
import os
import sys
import docx
import openpyxl
from dotenv import load_dotenv
import google.generativeai as genai
import extract_msg
import email
import queue
import pytesseract
import fitz # PyMuPDF
import io
from typing import List, Tuple
from dataclasses import dataclass
from datetime import datetime
from persona_manager import PersonaManager
from settings_dialog import PersonaDialog

# --- Tesseract Configuration ---
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except Exception:
    print("Tesseract not found at the specified path. Please ensure it's installed and the path is correct.")

# --- Load API Key and Configure Gemini ---
load_dotenv() 
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("CRITICAL ERROR: GEMINI_API_KEY not found.")

# --- Global variables ---
window = None
log_textbox = None
prompt_entry = None
update_queue = queue.Queue()
processed_content = ""
processed_filenames = []
persona_manager = None
current_persona = None

@dataclass
class ChatMessage:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime

class ConversationManager:
    def __init__(self):
        self.history: List[ChatMessage] = []
        self.max_history = 10  # Keep last 10 messages for context

    def add_message(self, role: str, content: str):
        self.history.append(ChatMessage(role=role, content=content, timestamp=datetime.now()))
        if len(self.history) > self.max_history:
            self.history.pop(0)  # Remove oldest message

    def get_context(self) -> str:
        if not self.history:
            return ""
        
        context = "Previous conversation:\n"
        for msg in self.history[-3:]:  # Last 3 messages for immediate context
            context += f"{msg.role}: {msg.content}\n"
        return context

    def clear(self):
        self.history.clear()

# --- Gemini API Function (UPDATED WITH "PROMPT AUGMENTATION") ---
def call_gemini(instruction):
    global processed_content, processed_filenames, conversation_manager
    if not log_textbox or not api_key: 
        messagebox.showerror("API Key Error", "Gemini API Key not found.")
        return
    if not processed_content.strip():
        messagebox.showerror("Error", "No file content has been processed. Please choose a file or folder first.")
        return
    if not instruction or not instruction.strip():
        messagebox.showerror("Error", "Please provide an instruction in the prompt box.")
        return

    # Get conversation context
    chat_context = conversation_manager.get_context()
    
    # Format files list
    formatted_files = "\n".join([
        f"File {i+1}: {filename}" 
        for i, filename in enumerate(processed_filenames)
    ])

    system_instruction = (
        "You are Vinay's Windows Copilot. Be concise and clear.\n"
        "If you're answering a follow-up question, use the conversation history for context."
    )

    final_prompt = (
        f"{system_instruction}\n\n"
        f"--- CONVERSATION HISTORY ---\n{chat_context}\n\n"
        f"--- FILES ANALYZED ---\n{formatted_files}\n\n"
        f"--- NEW INSTRUCTION ---\n{instruction}\n\n"
        f"--- CONTENT ---\n{processed_content}"
    )
    
    log_textbox.insert(tk.END, "\n\n====================\nAsking Gemini... Please wait.\n")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(final_prompt)
        
        # Store the conversation
        conversation_manager.add_message("user", instruction)
        conversation_manager.add_message("assistant", response.text)
        
        log_textbox.insert(tk.END, "--- GEMINI RESPONSE ---\n" + response.text)
    except Exception as e:
        log_textbox.insert(tk.END, f"An error occurred with the Gemini API:\n{e}")

def send_to_gemini_threaded(instruction):
    threading.Thread(target=call_gemini, args=(instruction,), daemon=True).start()

def custom_prompt_action():
    if prompt_entry:
        instruction = prompt_entry.get()
        send_to_gemini_threaded(instruction)

# --- File Readers (Unchanged) ---
def read_image_ocr(filepath):
    return pytesseract.image_to_string(Image.open(filepath), lang='eng+hin')
def read_pdf_hybrid(filepath):
    full_text = ""
    with fitz.open(filepath) as doc:
        for page_num, page in enumerate(doc):
            full_text += page.get_text()
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                full_text += f"\n--- OCR from image on page {page_num+1} ---\n"
                full_text += pytesseract.image_to_string(image, lang='eng+hin')
    return full_text

FILE_HANDLERS = {
    '.txt': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.py': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.js': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.html': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.css': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.pdf': read_pdf_hybrid,
    '.docx': lambda p: "\n".join(para.text for para in docx.Document(p).paragraphs),
    '.msg': lambda p: f"From: {extract_msg.Message(p).sender}\nTo: {extract_msg.Message(p).to}\nSubject: {extract_msg.Message(p).subject}\nDate: {extract_msg.Message(p).date}\n\n{extract_msg.Message(p).body}",
    '.eml': lambda p: open(p, 'r', encoding='utf-8', errors='ignore').read(),
    '.png': read_image_ocr, '.jpg': read_image_ocr, '.jpeg': read_image_ocr, '.bmp': read_image_ocr, '.tiff': read_image_ocr,
}

# --- Backend Logic (Unchanged) ---
def process_path_threaded(path):
    combined_content_list = []
    successful_filenames = []
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
                        successful_filenames.append(filename)
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
                                successful_filenames.append(filename)
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
    update_queue.put(("finished", (final_content, successful_filenames)))

def check_update_queue():
    global processed_content, processed_filenames
    try:
        while not update_queue.empty():
            msg_type, data = update_queue.get_nowait()
            if msg_type == "log":
                log_textbox.insert(tk.END, data)
                log_textbox.see(tk.END)
            elif msg_type == "finished":
                processed_content, processed_filenames = data
                log_textbox.insert(tk.END, "\n--- Analysis Complete. Ready for instructions. ---\n")
                log_textbox.see(tk.END)
    finally:
        if window: window.after(100, check_update_queue)

def start_processing(path):
    global processed_content, processed_filenames
    processed_content = ""
    processed_filenames = []
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

def copy_to_clipboard():
    if log_textbox:
        window.clipboard_clear()
        window.clipboard_append(log_textbox.get("1.0", tk.END))
        messagebox.showinfo("Copied", "Log & Response copied to clipboard.")

def clear_text_area():
    global processed_content, processed_filenames, conversation_manager
    if log_textbox:
        log_textbox.delete("1.0", tk.END)
        processed_content = ""
        processed_filenames = []
        conversation_manager.clear()

# --- Window and Tray Management (Unchanged) ---
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

# --- Main UI Function (Unchanged) ---
def main():
    global window, log_textbox, prompt_entry, conversation_manager, persona_manager, current_persona
    
    # Initialize managers
    conversation_manager = ConversationManager()
    persona_manager = PersonaManager()
    current_persona = persona_manager.get_persona("default")
    
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    window = ctk.CTk()
    window.title("Gemini Copilot")
    window.geometry("1100x720")
    window.protocol("WM_DELETE_WINDOW", hide_window)
    window.grid_columnconfigure(1, weight=1)
    window.grid_rowconfigure(0, weight=1)
    nav_frame = ctk.CTkFrame(window, width=200, corner_radius=0)
    nav_frame.grid(row=0, column=0, sticky="nsew")
    nav_frame.grid_rowconfigure(4, weight=1)
    app_title = ctk.CTkLabel(nav_frame, text="Gemini Copilot", font=ctk.CTkFont(family="Segoe UI Variable", size=20, weight="bold"))
    app_title.grid(row=0, column=0, padx=20, pady=(20, 10))
    file_button = ctk.CTkButton(nav_frame, text="Choose File", command=open_file_dialog)
    file_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
    folder_button = ctk.CTkButton(nav_frame, text="Choose Folder", command=open_folder_dialog)
    folder_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
    settings_label = ctk.CTkLabel(nav_frame, text="Settings", font=ctk.CTkFont(family="Segoe UI Variable", size=14, weight="bold"))
    settings_label.grid(row=5, column=0, padx=20, pady=(20, 0))
    theme_label = ctk.CTkLabel(nav_frame, text="Appearance:")
    theme_label.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="w")
    theme_menu = ctk.CTkOptionMenu(nav_frame, values=["Dark", "Light", "System"], command=ctk.set_appearance_mode)
    theme_menu.grid(row=7, column=0, padx=20, pady=10, sticky="ew")
    
    # Add Settings button to nav_frame
    settings_button = ctk.CTkButton(
        nav_frame, 
        text="AI Personas", 
        command=lambda: PersonaDialog(window, persona_manager)
    )
    settings_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

    # Add Persona Selector
    persona_label = ctk.CTkLabel(nav_frame, text="Active Persona:")
    persona_label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="w")
    
    def on_persona_change(choice):
        global current_persona
        current_persona = persona_manager.get_persona(choice)
    
    persona_menu = ctk.CTkOptionMenu(
        nav_frame,
        values=persona_manager.list_personas(),
        command=on_persona_change
    )
    persona_menu.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
    persona_menu.set("default")

    main_content_frame = ctk.CTkFrame(window, corner_radius=8, fg_color="transparent")
    main_content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
    main_content_frame.grid_columnconfigure(0, weight=1)
    main_content_frame.grid_rowconfigure(0, weight=1)
    log_textbox = ctk.CTkTextbox(main_content_frame, font=("Segoe UI", 13), corner_radius=8)
    log_textbox.grid(row=0, column=0, columnspan=2, sticky="nsew")
    log_textbox.insert("0.0", "Welcome! I can now read text from images (PNG, JPG) and scanned PDFs.")
    prompt_entry = ctk.CTkEntry(main_content_frame, placeholder_text="Summarize the content, or type your custom instruction here...", height=35, corner_radius=8)
    prompt_entry.grid(row=1, column=0, padx=(0, 10), pady=10, sticky="ew")
    ask_button = ctk.CTkButton(main_content_frame, text="Ask Gemini", command=custom_prompt_action, height=35, corner_radius=8)
    ask_button.grid(row=1, column=1, pady=10, sticky="e")
    util_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent")
    util_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
    util_frame.grid_columnconfigure(0, weight=1)
    copy_button = ctk.CTkButton(util_frame, text="Copy Log", command=copy_to_clipboard, fg_color="gray50", hover_color="gray60")
    copy_button.grid(row=0, column=0, padx=(0, 5), sticky="e")
    clear_button = ctk.CTkButton(util_frame, text="Clear", command=clear_text_area, fg_color="gray50", hover_color="gray60")
    clear_button.grid(row=0, column=1, padx=(5, 0), sticky="w")
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