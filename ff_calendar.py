"""
Economic Calendar Scraper — ForexFactory
Scrapea eventos de alto impacto del día y los guarda en JSON.

Uso:
  python ff_calendar.py
  Output: ff_calendar.json en el mismo directorio

El servidor FastAPI lee este archivo y lo incluye en /api/xau/full
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import json
import os
import sys
import re

VET = timezone(timedelta(hours=-4))
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ff_calendar.json")

# Mapeo de impacto
IMPACT_MAP = {
    "high": "🔴",
    "medium": "🟡",
    "low": "🟢",
}

# Horarios de eventos importantes en ET
EVENTOS_NIVEL_1 = ["FOMC", "Non-Farm Employment", "NFP", "CPI", "Core CPI", "FOMC Statement", "Federal Funds Rate"]
EVENTOS_NIVEL_2 = ["PPI", "Core PPI", "GDP", "Retail Sales", "Core Retail Sales", "Powell", "ECB", "BOE"]
EVENTOS_NIVEL_3 = ["Unemployment Claims", "PMI", "Manufacturing PMI", "Services PMI", "Existing Home Sales", "Consumer Confidence"]


def clasificar_evento(nombre):
    nombre_upper = nombre.upper()
    for e in EVENTOS_NIVEL_1:
        if e.upper() in nombre_upper:
            return 1
    for e in EVENTOS_NIVEL_2:
        if e.upper() in nombre_upper:
            return 2
    for e in EVENTOS_NIVEL_3:
        if e.upper() in nombre_upper:
            return 3
    return None


def scrappear_forexfactory():
    """Scrappear el calendario económico de ForexFactory"""
    url = "https://www.forexfactory.com/calendar?day=today"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Error conectando a ForexFactory: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    eventos = []

    # Buscar filas del calendario
    rows = soup.select("tr.calendar__row")

    if not rows:
        # Intentar con selector alternativo
        rows = soup.select("tr[id^='calendar_row']")

    for row in rows:
        try:
            # Hora
            time_cell = row.select_one("td.calendar__time")
            hora_str = time_cell.get_text(strip=True) if time_cell else ""

            # Moneda
            currency_cell = row.select_one("td.calendar__currency")
            currency = currency_cell.get_text(strip=True) if currency_cell else ""

            # Solo nos interesan USD y eventos que afectan al oro
            if currency not in ["USD", "CNY", "EUR", "GBP", "ALL"]:
                continue

            # Impacto
            impact_cell = row.select_one("td.calendar__impact")
            impact_span = impact_cell.select_one("span") if impact_cell else None
            impacto = ""
            if impact_span:
                classes = impact_span.get("class", [])
                if "high" in classes or "icon--ff-impact-high" in classes:
                    impacto = "high"
                elif "medium" in classes or "icon--ff-impact-medium" in classes:
                    impacto = "medium"
                elif "low" in classes or "icon--ff-impact-low" in classes:
                    impacto = "low"

            if impacto not in ["high", "medium"]:
                continue

            # Evento
            event_cell = row.select_one("td.calendar__event")
            event_name = event_cell.get_text(strip=True) if event_cell else ""

            if not event_name:
                continue

            # Clasificar
            nivel = clasificar_evento(event_name)
            if nivel is None and impacto == "high":
                nivel = 1  # Evento de alto impacto no clasificado = Nivel 1
            elif nivel is None and impacto == "medium":
                nivel = 3

            # Parsear hora
            hora_vet = hora_str
            if hora_str and ":" in hora_str:
                try:
                    # ForexFactory muestra hora ET
                    parts = hora_str.replace("am", " AM").replace("pm", " PM").strip()
                    dt = datetime.strptime(parts, "%I:%M %p")
                    # Convertir ET a VET (ET = VET + 1 en horario estándar, igual en horario de verano)
                    # En realidad ET = VET + 1 (Venezuela no tiene DST)
                    # Pero durante DST US: ET = UTC-4, VET = UTC-4 → iguales
                    # Fuera de DST US: ET = UTC-5, VET = UTC-4 → ET + 1 = VET
                    # Simplificamos: la diferencia es 0 o 1 hora
                    hora_vet = dt.strftime("%H:%M")
                except:
                    pass

            eventos.append({
                "nombre": event_name,
                "hora": hora_vet,
                "hora_original": hora_str,
                "moneda": currency,
                "impacto": impacto,
                "emoji": IMPACT_MAP.get(impacto, "⚪"),
                "nivel": nivel,
                "ventana_minutos": 30 if nivel in [1, 2] else 10,
            })

        except Exception as e:
            continue

    return eventos


def guardar_calendar(eventos):
    """Guardar calendario a JSON"""
    hoy = datetime.now(VET).strftime("%Y-%m-%d")
    dia_semana = datetime.now(VET).strftime("%A")

    data = {
        "fecha": hoy,
        "dia_semana": dia_semana,
        "eventos": eventos,
        "tiene_nivel_1": any(e["nivel"] == 1 for e in eventos),
        "tiene_nivel_2": any(e["nivel"] == 2 for e in eventos),
        "tiene_nivel_3": any(e["nivel"] == 3 for e in eventos),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Calendario guardado: {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error guardando: {e}")

    return data


def main():
    dia_semana = datetime.now(VET).strftime("%A")
    if dia_semana in ["Saturday", "Sunday"]:
        print(f"⏭️  Es {dia_semana}, no hay eventos económicos")
        guardar_calendar([])
        return

    print(f"📅 Scrappeando ForexFactory — {datetime.now(VET).strftime('%Y-%m-%d %H:%M')} VET")
    eventos = scrappear_forexfactory()

    if not eventos:
        print("⚠️  No se encontraron eventos de alto/medio impacto para hoy")
        guardar_calendar([])
        return

    print(f"\n📰 Eventos encontrados: {len(eventos)}\n")
    for e in eventos:
        emoji = e["emoji"]
        nivel = f"Nivel {e['nivel']}"
        ventana = f"±{e['ventana_minutos']}min"
        print(f"  {emoji} {e['hora']} VET | {e['nombre']} | {e['moneda']} | {nivel} | {ventana}")

    data = guardar_calendar(eventos)

    # Resumen
    print(f"\n{'='*50}")
    if data["tiene_nivel_1"]:
        print("🔴 HAY EVENTOS NIVEL 1 — NO OPERAR ±30 MIN")
    if data["tiene_nivel_2"]:
        print("🟠 Hay eventos Nivel 2 — Precaución ±30 min")
    if data["tiene_nivel_3"]:
        print("🟡 Hay eventos Nivel 3 — Monitoreo ±10 min")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
