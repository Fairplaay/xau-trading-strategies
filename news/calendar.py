# -*- coding: utf-8 -*-
"""
Módulo de noticias - Calendario ForexFactory
Carga y filtra eventos económicos.
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ImpactLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class NewsEvent:
    """Evento económico del calendario."""
    title: str
    date: datetime
    impact: ImpactLevel
    currency: str
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


class NewsCalendar:
    """Gestor del calendario de noticias."""
    
    def __init__(self, url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"):
        self.url = url
        self.events: List[NewsEvent] = []
        self._loaded = False
    
    def load(self) -> bool:
        """Carga el calendario de la semana desde ForexFactory."""
        import time
        import os
        
        # Intentar hasta 3 veces con delay
        for attempt in range(3):
            try:
                # Verificar cache local (archivo json en directorio del proyecto)
                cache_file = os.path.join(os.path.dirname(__file__), "..", "cache", "news_cache.json")
                if os.path.exists(cache_file):
                    age = time.time() - os.path.getmtime(cache_file)
                    if age < 3600:  # Cache válido por 1 hora
                        with open(cache_file, "r") as f:
                            data = json.load(f)
                            self.events = self._parse_events(data)
                            self._loaded = True
                            print(f"📰 Calendario cargado desde cache: {len(self.events)} eventos")
                            return True
                
                response = requests.get(self.url, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                self.events = self._parse_events(data)
                self._loaded = True
                
                # Guardar cache
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, "w") as f:
                    json.dump(data, f)
                
                print(f"📰 Calendario cargado: {len(self.events)} eventos")
                return True
                
            except Exception as e:
                if attempt < 2:
                    print(f"⚠️ Intento {attempt+1} falló, reintentando en 2s...")
                    time.sleep(2)
                else:
                    print(f"❌ Error cargando calendario: {e}")
        return False
    
    def _parse_events(self, data: List[Dict]) -> List[NewsEvent]:
        """Parsea los eventos del JSON de ForexFactory."""
        events = []
        for item in data:
            try:
                # ForexFactory usa format como "Apr 05, 2025 08:30am EST"
                date_str = item.get("date", "")
                if not date_str:
                    continue
                
                # Parsear fecha (ej: "Apr 05, 2025 08:30am EST")
                dt = self._parse_date(date_str)
                if dt is None:
                    continue
                
                # Determinar impacto
                impact_str = item.get("impact", "").lower()
                impact = ImpactLevel.HIGH if impact_str == "high" else \
                         ImpactLevel.MEDIUM if impact_str == "medium" else \
                         ImpactLevel.LOW
                
                event = NewsEvent(
                    title=item.get("title", "Unknown"),
                    date=dt,
                    impact=impact,
                    currency=item.get("currency", "").upper(),
                    actual=item.get("actual"),
                    forecast=item.get("forecast"),
                    previous=item.get("previous")
                )
                events.append(event)
            except Exception:
                continue
        
        return events
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsea string de fecha de ForexFactory."""
        try:
            # Nuevo formato ISO: "2026-04-05T05:15:00-04:00"
            if "T" in date_str and "-" in date_str:
                # Parsear ISO 8601 y convertir a timezone naive (UTC)
                dt = datetime.fromisoformat(date_str.replace("-04:00", "+00:00").replace("-05:00", "+00:00"))
                return dt
            
            # Formato antiguo: "Apr 05, 2025 08:30am EST"
            date_str = date_str.replace(" EST", "").replace(" EDT", "")
            dt = datetime.strptime(date_str, "%b %d, %Y %I:%M%p")
            # Asumir timezone EST/EDT (UTC-5/UTC-4)
            return dt
        except Exception:
            return None
    
    def get_upcoming(self, minutes: int = 30, currencies: List[str] = None) -> List[NewsEvent]:
        """Retorna eventos en los próximos X minutos."""
        if not self._loaded:
            return []
        
        now = datetime.now(timezone.utc)
        future = now + timedelta(minutes=minutes)
        
        upcoming = []
        for event in self.events:
            if now <= event.date <= future:
                if currencies is None or event.currency in currencies:
                    upcoming.append(event)
        
        return upcoming
    
    def is_blocked(self, minutes_ahead: int = 30) -> bool:
        """Verifica si hay noticias de alto impacto proximas."""
        high_impact = self.get_upcoming(minutes_ahead, currencies=["USD", "EUR", "GBP"])
        return any(e.impact == ImpactLevel.HIGH for e in high_impact)
    
    def get_block_status(self) -> Dict:
        """Retorna el estado de bloqueo por noticias."""
        now = datetime.now(timezone.utc)
        
        # Alta impacto en próximas 30 min
        high = self.get_upcoming(30, currencies=["USD", "EUR", "GBP"])
        high_blocked = any(e.impact == ImpactLevel.HIGH for e in high)
        
        # Medio impacto en próximos 10 min
        medium = self.get_upcoming(10, currencies=["USD", "EUR", "GBP"])
        medium_blocked = any(e.impact == ImpactLevel.MEDIUM for e in medium)
        
        return {
            "high_impact_blocked": high_blocked,
            "medium_impact_blocked": medium_blocked,
            "upcoming_high": [e.title for e in high if e.impact == ImpactLevel.HIGH],
            "upcoming_medium": [e.title for e in medium if e.impact == ImpactLevel.MEDIUM]
        }
    
    def __len__(self):
        return len(self.events)
    
    def __repr__(self):
        return f"NewsCalendar({len(self.events)} events, loaded={self._loaded})"