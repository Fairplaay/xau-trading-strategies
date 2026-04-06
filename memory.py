# -*- coding: utf-8 -*-
"""
Gestión de memory.json - Contexto de operaciones (circular, 50 items).
Se carga al iniciar y se actualiza durante el día.
"""

import json
import os
from datetime import datetime
from typing import List, Dict

MEMORY_FILE = "memory.json"
MAX_ITEMS = 50


class Memory:
    """Gestor del memory.json"""
    
    def __init__(self, file_path: str = MEMORY_FILE):
        self.file_path = file_path
        self.items: List[str] = []
        self.load()
    
    def load(self):
        """Carga memory desde archivo."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    self.items = json.load(f)
            except:
                self.items = []
        else:
            self.items = []
    
    def save(self):
        """Guarda memory en archivo."""
        with open(self.file_path, "w") as f:
            json.dump(self.items, f, indent=2)
    
    def add(self, text: str):
        """
        Agrega item al memory.
        Si supera 50 items, reemplaza el más antiguo.
        """
        # Timestamp + texto corto
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        item = f"{timestamp} {text}"
        
        self.items.append(item)
        
        # Si supera 50, quitar el más antiguo
        if len(self.items) > MAX_ITEMS:
            self.items.pop(0)
        
        self.save()
    
    def add_operation(self, direction: str, symbol: str, pnl: str):
        """Agrega operación al memory."""
        self.add(f"{direction} {symbol} {pnl}")
    
    def add_note(self, note: str):
        """Agrega nota al memory."""
        self.add(f"NOTE: {note}")
    
    def get_context(self) -> str:
        """Retorna el memory formateado para la IA."""
        if not self.items:
            return "Sin historial reciente."
        
        # Últimos 20 items para el contexto
        recent = self.items[-20:]
        return "## Historial reciente:\n" + "\n".join(recent)
    
    def __len__(self):
        return len(self.items)
    
    def __repr__(self):
        return f"Memory({len(self.items)} items)"