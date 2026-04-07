# -*- coding: utf-8 -*-
"""Módulo de memoria para guardar operaciones."""

import json
import os
from datetime import datetime

class Memory:
    def __init__(self, file_path: str = "operaciones.json"):
        self.file_path = file_path
        self.operaciones = []
        self._cargar()
    
    def _cargar(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self.operaciones = json.load(f)
            except:
                self.operaciones = []
    
    def _guardar(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.operaciones, f, indent=2)
    
    def add_operation(self, direction: str, symbol: str, pnl: str = "pendiente"):
        self.operaciones.append({
            "time": datetime.now().isoformat(),
            "direction": direction,
            "symbol": symbol,
            "pnl": pnl
        })
        self._guardar()
