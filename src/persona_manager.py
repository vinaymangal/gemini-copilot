from dataclasses import dataclass
import json
import os
from typing import Dict, List, Optional

@dataclass
class AIPersona:
    name: str
    description: str
    system_prompt: str
    instruction_template: str

class PersonaManager:
    def __init__(self):
        self.personas: Dict[str, AIPersona] = {}
        self.config_path = os.path.join(os.path.dirname(__file__), "personas.json")
        self._load_default_personas()
        self.load_personas()

    def _load_default_personas(self):
        self.personas = {
            "default": AIPersona(
                name="Default Copilot",
                description="General purpose AI assistant",
                system_prompt="You are Vinay's Windows Copilot. Be concise and clear.",
                instruction_template="{instruction}"
            ),
            "code_reviewer": AIPersona(
                name="Code Reviewer",
                description="Reviews code for bugs and improvements",
                system_prompt="You are an expert programmer. Focus on code quality, bugs, and performance.",
                instruction_template="Review this code:\n{instruction}"
            ),
            "translator": AIPersona(
                name="Translator",
                description="Translates content between languages",
                system_prompt="You are a language expert. Maintain context and nuance in translations.",
                instruction_template="Translate to {language}:\n{instruction}"
            )
        }

    def save_personas(self):
        data = {name: vars(persona) for name, persona in self.personas.items()}
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_personas(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.personas.update({
                    name: AIPersona(**details) for name, details in data.items()
                })

    def add_persona(self, persona: AIPersona) -> None:
        self.personas[persona.name.lower()] = persona
        self.save_personas()

    def get_persona(self, name: str) -> Optional[AIPersona]:
        return self.personas.get(name.lower())

    def list_personas(self) -> List[str]:
        return list(self.personas.keys())