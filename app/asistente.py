"""Asistente de Claude dentro de Basetoque Studio (opcional).

Funciona sólo si está instalado el paquete `anthropic` (pip install anthropic)
y hay una clave de API guardada en la app (Ajustes) o en la variable de
entorno ANTHROPIC_API_KEY. Sin eso, el resto de la app funciona igual, offline.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.local.json"
MODELO = "claude-opus-5-5"

try:
    import anthropic
except ImportError:  # el asistente es opcional
    anthropic = None


class AsistenteError(Exception):
    pass


def _config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar_clave(clave: str) -> None:
    cfg = _config()
    cfg["anthropic_api_key"] = clave.strip()
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG, 0o600)
    except OSError:
        pass


def _clave() -> str | None:
    return _config().get("anthropic_api_key") or None


def estado() -> str:
    if anthropic is None:
        return "falta_sdk"
    if _clave() or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "listo"
    return "falta_clave"


def disponible() -> bool:
    return estado() == "listo"


SISTEMA = """Eres el asistente creativo de Basetoque Studio, una app para hacer videos y flyers.
Hablas en español, de forma breve, cálida y sin tecnicismos (el usuario no es técnico).

Cuando el usuario pida un video o un flyer, responde con:
1. Una o dos frases explicando lo que propones.
2. Un bloque ```json con el diseño completo, siguiendo EXACTAMENTE el formato del modo actual.
Si sólo conversa o pregunta algo, responde sin JSON. Usa sólo archivos de la lista disponible
(rutas tal cual, p.ej. "media/clip.mp4"). Si falta material, dilo y propone qué subir.

## Modo "video": proyecto de línea de tiempo
{
  "formato": "9:16" | "16:9" | "1:1" | "4:5",
  "clips": [
    // video: {"src": "media/x.mp4", "start": 0, "end": 5, "speed": 1, "text": [TEXTO], "transition": TRANS}
    // imagen: {"src": "media/foto.jpg", "duration": 3, "kenburns": true}
    // tarjeta: {"color": "#111111", "duration": 2, "text": [TEXTO]}
  ],
  "text": [TEXTO],                       // textos sobre todo el video (tiempos absolutos)
  "music": {"src": "media/tema.mp3", "volume": 0.25},   // opcional
  "color": {"preset": "cinematic|warm|cool|vivid|bw|vintage|dramatic|fade"},  // opcional
  "watermark": {"src": "media/logo.png", "position": "top-right", "scale": 0.12}, // opcional
  "fade_in": 0.3, "fade_out": 0.8
}
TEXTO = {"text": "...", "start": 0, "end": 3, "position": "top|center|bottom|lower-third|top-left|top-right|bottom-left|bottom-right",
         "size": 72, "color": "white", "box": true, "fade": 0.3}
TRANS = "cut" | "fade" | "fadeblack" | "slideleft" | "slideright" | "wipeleft" | "circleopen" | "dissolve"
Consejos: planos de 1.5–4 s para redes, gancho en los primeros 2 s, textos grandes y cortos,
en 9:16 evita el 15% inferior. Tiempos en segundos (números).

## Modo "flyer": diseño
{
  "ancho": 1080, "alto": 1350,
  "fondo": {"tipo": "color|degradado|imagen", "color": "#hex", "color2": "#hex", "angulo": 135,
            "imagen": "media/foto.jpg", "oscurecer": 0.35},
  "elementos": [
    {"tipo": "texto", "texto": "...", "x": 80, "y": 120, "ancho": 920, "tamano": 110,
     "fuente": "Impact|Arial|Georgia|Verdana|Trebuchet MS|Courier New|Brush Script MT",
     "color": "#ffffff", "negrita": true, "cursiva": false, "alineacion": "left|center|right",
     "sombra": true, "contorno": 0, "colorContorno": "#000000", "caja": "", "interlineado": 1.1},
    {"tipo": "forma", "forma": "rect|circulo", "x": 0, "y": 0, "ancho": 300, "alto": 100,
     "color": "#ff3366", "radio": 24, "opacidad": 1},
    {"tipo": "imagen", "src": "media/logo.png", "x": 0, "y": 0, "ancho": 300, "alto": 300, "redondeo": 0}
  ]
}
Coordenadas en píxeles desde la esquina superior izquierda. Tamaños típicos: post 1080x1350,
cuadrado 1080x1080, historia 1080x1920. Diseña con jerarquía clara (título grande, datos
medianos, detalles pequeños), buen contraste y márgenes de al menos 60 px.
"""


def _extraer_json(texto: str):
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.S)
    if not m:
        return texto.strip(), None
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return texto.strip(), None
    limpio = (texto[:m.start()] + texto[m.end():]).strip()
    return limpio, data


def preguntar(mensaje: str, modo: str, historial: list, archivos: list[str], actual=None) -> dict:
    if anthropic is None:
        raise AsistenteError("Falta instalar el asistente. Abre INSTALAR.md, paso 3.")
    if not disponible():
        raise AsistenteError("Falta tu clave de Claude. Ve a Ajustes y pégala.")
    if not mensaje.strip():
        raise AsistenteError("Escribe un mensaje.")
    client = anthropic.Anthropic(api_key=_clave()) if _clave() else anthropic.Anthropic()

    contexto = (f"Modo actual: {modo}.\nArchivos disponibles:\n"
                + ("\n".join(f"- {a}" for a in archivos) or "(ninguno todavía)"))
    if actual:
        contexto += "\n\nDiseño actual en el editor:\n" + json.dumps(actual, ensure_ascii=False)[:20000]

    mensajes = []
    for h in historial[-12:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            mensajes.append({"role": h["role"], "content": str(h["content"])})
    mensajes.append({"role": "user", "content": f"{contexto}\n\n---\n{mensaje}"})

    try:
        resp = client.beta.messages.create(
            model=MODELO,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium"},
            system=SISTEMA,
            messages=mensajes,
        )
    except anthropic.AuthenticationError:
        raise AsistenteError("La clave de Claude no es válida. Revísala en Ajustes.")
    except anthropic.PermissionDeniedError:
        raise AsistenteError("Tu clave no tiene permiso para usar este modelo.")
    except anthropic.RateLimitError:
        raise AsistenteError("Demasiadas solicitudes seguidas. Espera un minuto y vuelve a intentar.")
    except anthropic.APIConnectionError:
        raise AsistenteError("No hay conexión a internet. El asistente necesita internet; "
                             "el resto de la app funciona sin conexión.")
    except anthropic.APIStatusError as e:
        raise AsistenteError(f"Claude respondió con un error ({e.status_code}). Intenta de nuevo.")

    if resp.stop_reason == "refusal":
        return {"texto": "No puedo ayudar con ese pedido. ¿Probamos con otra idea?", "diseno": None}
    texto = "\n".join(b.text for b in resp.content if b.type == "text")
    limpio, diseno = _extraer_json(texto)
    return {"texto": limpio or "Listo, aquí tienes una propuesta.", "diseno": diseno}
