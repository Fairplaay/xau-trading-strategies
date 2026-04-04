"""
XAU/USD Data Server para Kilito — FastAPI v2 (Plan B)
Lee datos de un archivo JSON escrito por el EA de MT5.
Sin HTTP, sin problemas de red de Wine.

Uso:
  python xau_data_server.py
  Docs: http://localhost:5555/docs

El EA de MT5 escribe a: MQL5/Files/xau_data.json
El servidor lee ese archivo cada vez que Kilito consulta.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel
import json
import os
import glob

# ============== CONFIG ==============
VET = timezone(timedelta(hours=-4))
SESSION_START = 8
SESSION_END = 16
CALENDAR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ff_calendar.json")

# Ruta del archivo JSON del EA
# Wine guarda archivos de MT5 en ~/.wine/drive_c/users/.../MQL5/Files/
# Buscamos automáticamente
EA_FILENAME = "xau_data.json"

def find_data_file():
    """Buscar el archivo xau_data.json en el Wine prefix"""
    # Rutas comunes donde MT5/Wine guarda archivos
    home = os.path.expanduser("~")
    search_paths = [
        os.path.join(home, ".wine", "drive_c", "users", "**", "AppData", "Roaming", "MetaQuotes", "Terminal", "**", "MQL5", "Files", EA_FILENAME),
        os.path.join(home, ".wine", "drive_c", "Program Files", "MetaTrader 5", "MQL5", "Files", EA_FILENAME),
    ]

    for pattern in search_paths:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]

    # Buscar en todo el Wine prefix (más lento pero más seguro)
    wine_root = os.path.join(home, ".wine", "drive_c")
    if os.path.exists(wine_root):
        for root, dirs, files in os.walk(wine_root):
            if EA_FILENAME in files:
                return os.path.join(root, EA_FILENAME)

    return None


# ============== MODELOS ==============
class Vela(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float

class Senal(BaseModel):
    tipo: str
    precio: float
    ema50: float
    ema200: float
    rsi: float
    sl: float
    tp: float
    distancia_ema50: float
    patrones: Optional[list[str]] = None
    confirmada: bool
    razon: str
    timestamp: str

class FullResponse(BaseModel):
    status: dict
    precio: Optional[dict] = None
    indicadores: Optional[dict] = None
    ultimas_velas_m1: Optional[list[Vela]] = None
    senal: Optional[Senal] = None
    ultima_actualizacion: Optional[str] = None
    archivo_mtime: Optional[str] = None
    ventana_operativa: bool
    noticia_activa: Optional[dict] = None
    calendario: Optional[dict] = None
    hora_vet: str
    timestamp: str

# ============== DETECCIÓN SEÑALES ==============
def detectar_patrones(velas):
    if len(velas) < 3:
        return None
    ult = velas[-1]
    ant = velas[-2]
    o, c, h, l = ult['o'], ult['c'], ult['h'], ult['l']
    cuerpo = abs(c - o)
    rango = h - l
    if rango == 0 or cuerpo == 0:
        return None
    ms = h - max(o, c)
    mi = min(o, c) - l
    p = []
    if mi > cuerpo * 2 and ms < cuerpo * 0.5 and c > o:
        p.append("martillo_alcista")
    if ms > cuerpo * 2 and mi < cuerpo * 0.5 and c < o:
        p.append("estrella_fugaz")
    if ant['c'] < ant['o'] and c > o and c > ant['o'] and o < ant['c']:
        p.append("envolvente_alcista")
    if ant['c'] > ant['o'] and c < o and c < ant['o'] and o > ant['c']:
        p.append("envolvente_bajista")
    if mi > cuerpo * 3 and c > o:
        p.append("pin_bar_alcista")
    if ms > cuerpo * 3 and c < o:
        p.append("pin_bar_bajista")
    return p if p else None

def detectar_senal(data):
    if not data or len(data.get("velas", [])) < 200:
        return None
    velas = data["velas"]
    precio = data["bid"]
    ema50 = data["ema50"]
    ema200 = data["ema200"]
    rsi = data["rsi14"]

    pat = detectar_patrones(velas)
    dist = abs(precio - ema50)
    cerca = dist < precio * 0.0008
    hay_alc = pat and any(p in pat for p in ['martillo_alcista','envolvente_alcista','pin_bar_alcista'])
    hay_baj = pat and any(p in pat for p in ['estrella_fugaz','envolvente_bajista','pin_bar_bajista'])

    def razon(tipo):
        r = f"${precio:.2f} {'sobre' if tipo=='BUY' else 'bajo'} EMA200 ${ema200:.2f} | EMA50 ${ema50:.2f} | RSI {rsi:.1f}"
        if pat: r += f" | Patrón: {', '.join(pat)}"
        return r

    now = datetime.now(VET).strftime('%H:%M:%S')

    if precio > ema200 and cerca and 48 < rsi < 65:
        return {
            'tipo': 'BUY', 'precio': precio, 'ema50': ema50, 'ema200': ema200,
            'rsi': rsi, 'sl': round(precio - 0.35, 2), 'tp': round(precio + 0.70, 2),
            'distancia_ema50': round(dist, 2), 'patrones': pat,
            'confirmada': bool(hay_alc), 'razon': razon('BUY'), 'timestamp': now
        }

    if precio < ema200 and cerca and 35 < rsi < 52:
        return {
            'tipo': 'SELL', 'precio': precio, 'ema50': ema50, 'ema200': ema200,
            'rsi': rsi, 'sl': round(precio + 0.35, 2), 'tp': round(precio - 0.70, 2),
            'distancia_ema50': round(dist, 2), 'patrones': pat,
            'confirmada': bool(hay_baj), 'razon': razon('SELL'), 'timestamp': now
        }
    return None

def en_ventana():
    return SESSION_START <= datetime.now(VET).hour < SESSION_END

# ============== CALENDARIO ECONÓMICO ==============
def read_calendar():
    """Leer calendario de ForexFactory"""
    try:
        if os.path.exists(CALENDAR_FILE):
            with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return None

def en_ventana_noticia():
    """Verificar si estamos dentro de una ventana de noticia de alto impacto"""
    cal = read_calendar()
    if not cal:
        return None

    ahora = datetime.now(VET)
    ahora_min = ahora.hour * 60 + ahora.minute

    for evento in cal.get("eventos", []):
        nivel = evento.get("nivel")
        hora_str = evento.get("hora", "")
        ventana = evento.get("ventana_minutos", 30)

        if not hora_str or ":" not in hora_str:
            continue

        try:
            h, m = map(int, hora_str.split(":"))
            evento_min = h * 60 + m

            if abs(ahora_min - evento_min) <= ventana:
                return {
                    "bloqueado": nivel in [1, 2],
                    "nivel": nivel,
                    "evento": evento["nombre"],
                    "hora": hora_str,
                    "ventana": ventana,
                    "emoji": evento.get("emoji", ""),
                }
        except:
            continue

    return None

# ============== LIFESPAN ==============
data_file_path = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global data_file_path
    data_file_path = find_data_file()

    if data_file_path:
        print(f"✅ Archivo encontrado: {data_file_path}")
    else:
        print(f"⚠️  No se encontró {EA_FILENAME}")
        print(f"   Asegúrate de tener el EA corriendo en MT5")
        print(f"   El servidor igual arranca, buscará el archivo cuando consultes")

    yield

app = FastAPI(title="XAU/USD Data Server", version="2.0-planB", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ============== LEER ARCHIVO ==============
def read_data():
    global data_file_path

    # Re-buscar si no se encontró antes
    if not data_file_path:
        data_file_path = find_data_file()
        if not data_file_path:
            return None, None

    try:
        mtime = os.path.getmtime(data_file_path)
        with open(data_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            data = json.loads(content)
            return data, mtime
    except Exception as e:
        print(f"⚠️ Error leyendo archivo: {e}")
        return None, None

# ============== ENDPOINTS ==============

@app.get("/")
async def root():
    return {
        "service": "XAU/USD Data Server v2 (Plan B — archivo)",
        "data_file": data_file_path,
        "docs": "/docs",
        "endpoints": {
            "GET /api/xau/full": "Kilito consulta datos aquí",
            "GET /api/xau/status": "Estado del servidor",
            "GET /api/xau/find": "Buscar archivo de datos",
        },
    }


@app.get("/api/xau/find")
async def find_file():
    """Buscar el archivo de datos del EA"""
    global data_file_path
    data_file_path = find_data_file()
    return {
        "found": data_file_path is not None,
        "path": data_file_path,
    }


@app.get("/api/xau/full", response_model=FullResponse)
async def get_full():
    """Endpoint principal para Kilito"""
    data, mtime = read_data()

    if data is None:
        raise HTTPException(404, f"No se encontró {EA_FILENAME}. Asegúrate de tener el EA corriendo en MT5.")

    # Status
    status_data = {
        "server": data.get("server"),
        "account": data.get("account"),
        "mt5_connected": True,
    }

    # Precio
    precio_data = {
        "bid": data["bid"],
        "ask": data["ask"],
        "mid": data["mid"],
        "spread": data["spread"],
    }

    # Indicadores
    indicadores = {
        "rsi14": data["rsi14"],
        "ema50": data["ema50"],
        "ema200": data["ema200"],
        "atr14": data.get("atr14", 0),
    }

    # Velas
    velas_m1 = [
        {"time": v["t"], "open": v["o"], "high": v["h"], "low": v["l"], "close": v["c"]}
        for v in data.get("velas", [])
    ]

    # Señal
    senal = None
    if en_ventana():
        s = detectar_senal(data)
        if s:
            senal = Senal(**s)

    return {
        "status": status_data,
        "precio": precio_data,
        "indicadores": indicadores,
        "ultimas_velas_m1": velas_m1,
        "senal": senal,
        "ultima_actualizacion": data.get("timestamp"),
        "archivo_mtime": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat() if mtime else None,
        "ventana_operativa": en_ventana(),
        "noticia_activa": en_ventana_noticia(),
        "calendario": read_calendar(),
        "hora_vet": datetime.now(VET).strftime('%H:%M:%S'),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/xau/status")
async def get_status():
    data, mtime = read_data()
    return {
        "server_running": True,
        "data_file": data_file_path,
        "has_data": data is not None,
        "last_timestamp": data.get("timestamp") if data else None,
        "file_mtime": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat() if mtime else None,
        "ventana_operativa": en_ventana(),
        "hora_vet": datetime.now(VET).strftime('%H:%M:%S'),
        "senal": detectar_senal(data) if data and en_ventana() else None,
    }


# ============== MAIN ==============
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🤖 XAU/USD Data Server v2 (Plan B)")
    print("   Lee archivo JSON del EA de MT5")
    print("=" * 50)
    print()
    print("Docs: http://localhost:5555/docs")
    print("Principal: http://localhost:5555/api/xau/full")
    print()

    uvicorn.run(app, host="0.0.0.0", port=5555)
