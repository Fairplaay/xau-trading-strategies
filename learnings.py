# -*- coding: utf-8 -*-
"""
Gestión de learnings.json - Aprendizaje permanente.
Nunca se borra, se acumula día tras día.
"""

import json
import os
from datetime import datetime
from typing import List


LEARNINGS_FILE = "learnings.json"


class Learnings:
    """Gestor del learnings.json (aprendizaje permanente)"""
    
    def __init__(self, file_path: str = LEARNINGS_FILE):
        self.file_path = file_path
        self.items: List[str] = []
        self.load()
    
    def load(self):
        """Carga learnings desde archivo."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    self.items = json.load(f)
            except:
                self.items = []
        else:
            self.items = []
    
    def save(self):
        """Guarda learnings en archivo."""
        with open(self.file_path, "w") as f:
            json.dump(self.items, f, indent=2)
    
    def add(self, text: str):
        """
        Agrega aprendizaje.
        Formato: fecha + aprendizaje corto.
        """
        date = datetime.now().strftime("%d/%m")
        item = f"{date}: {text}"
        
        # Evitar duplicados
        if item not in self.items:
            self.items.append(item)
            self.save()
    
    def get_context(self) -> str:
        """Retorna learnings formateado para la IA."""
        if not self.items:
            return "Sin aprendizajes registrados."
        
        return "## Aprendizajes acumulados:\n" + "\n".join(self.items)
    
    def __len__(self):
        return len(self.items)
    
    def __repr__(self):
        return f"Learnings({len(self.items)} items)"