import customtkinter as ctk
from typing import Optional
from persona_manager import PersonaManager, AIPersona

class PersonaDialog(ctk.CTkToplevel):
    def __init__(self, parent, persona_manager: PersonaManager):
        super().__init__(parent)
        
        self.title("Manage AI Personas")
        self.geometry("600x400")
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        
        self.persona_manager = persona_manager
        self.selected_persona: Optional[AIPersona] = None
        
        self._create_widgets()
        self._load_personas()

    def _create_widgets(self):
        # Left side - Persona List
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(side="left", fill="y", padx=10, pady=10)
        
        self.persona_list = ctk.CTkTextbox(list_frame, width=200)
        self.persona_list.pack(fill="both", expand=True)
        
        # Right side - Editing
        edit_frame = ctk.CTkFrame(self)
        edit_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Persona Details
        ctk.CTkLabel(edit_frame, text="Name:").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(edit_frame)
        self.name_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(edit_frame, text="Description:").pack(anchor="w")
        self.desc_entry = ctk.CTkEntry(edit_frame)
        self.desc_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(edit_frame, text="System Prompt:").pack(anchor="w")
        self.prompt_text = ctk.CTkTextbox(edit_frame, height=100)
        self.prompt_text.pack(fill="x", pady=(0, 10))
        
        # Buttons
        btn_frame = ctk.CTkFrame(edit_frame)
        btn_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_frame, text="New", command=self._new_persona).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Save", command=self._save_persona).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Delete", command=self._delete_persona).pack(side="left", padx=5)

    def _load_personas(self):
        self.persona_list.delete("1.0", "end")
        for name in self.persona_manager.list_personas():
            self.persona_list.insert("end", f"{name}\n")

    def _new_persona(self):
        self.name_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")
        self.prompt_text.delete("1.0", "end")

    def _save_persona(self):
        name = self.name_entry.get()
        if name:
            persona = AIPersona(
                name=name,
                description=self.desc_entry.get(),
                system_prompt=self.prompt_text.get("1.0", "end").strip(),
                instruction_template="{instruction}"
            )
            self.persona_manager.add_persona(persona)
            self._load_personas()

    def _delete_persona(self):
        name = self.name_entry.get()
        if name in self.persona_manager.personas:
            del self.persona_manager.personas[name]
            self.persona_manager.save_personas()
            self._load_personas()