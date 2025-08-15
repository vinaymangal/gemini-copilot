from tkinter import Tk, Text, Button, Frame, Scrollbar, END, messagebox

class GeminiUI:
    def __init__(self, master):
        self.master = master
        master.title("Gemini Copilot")
        master.geometry("400x300")

        self.frame = Frame(master)
        self.frame.pack(pady=10)

        self.text_area = Text(self.frame, wrap='word', height=10, width=50)
        self.text_area.pack(side='left', fill='both', expand=True)

        self.scrollbar = Scrollbar(self.frame, command=self.text_area.yview)
        self.scrollbar.pack(side='right', fill='y')

        self.text_area.config(yscrollcommand=self.scrollbar.set)

        self.send_button = Button(master, text="Send", command=self.send_text)
        self.send_button.pack(pady=5)

        self.quit_button = Button(master, text="Quit", command=master.quit)
        self.quit_button.pack(pady=5)

    def send_text(self):
        user_input = self.text_area.get("1.0", END).strip()
        if user_input:
            # Here you would typically send the input to the API
            messagebox.showinfo("Info", f"Sending: {user_input}")
            self.text_area.delete("1.0", END)
        else:
            messagebox.showwarning("Warning", "Please enter some text.")

def main():
    root = Tk()
    app = GeminiUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()