"""Servidor local de Basetoque Studio.

Sirve la interfaz web (app/web) en http://127.0.0.1:8765 y expone una API
JSON pequeña para subir archivos, ejecutar ediciones con vedit, guardar
flyers y proyectos, y (opcionalmente) hablar con Claude.

Sólo usa la librería estándar de Python. Escucha únicamente en 127.0.0.1,
así que nadie fuera de tu computadora puede conectarse.
"""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import queue
import re
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "app" / "web"
MEDIA = ROOT / "media"
OUT = ROOT / "out"
PROYECTOS = ROOT / "proyectos"
CACHE = ROOT / ".cache"

sys.path.insert(0, str(ROOT))
import vedit  # noqa: E402

from app import asistente  # noqa: E402

# En Windows el registro puede tener tipos MIME incorrectos; fijamos los nuestros.
for _ext, _tipo in ((".js", "text/javascript"), (".css", "text/css"), (".html", "text/html"),
                    (".mp4", "video/mp4"), (".webm", "video/webm"), (".mov", "video/quicktime"),
                    (".mp3", "audio/mpeg"), (".m4a", "audio/mp4"), (".wav", "audio/wav"),
                    (".png", "image/png"), (".jpg", "image/jpeg"), (".gif", "image/gif"),
                    (".webp", "image/webp"), (".srt", "text/plain")):
    mimetypes.add_type(_tipo, _ext)

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts", ".3gp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
SUBS_EXT = {".srt", ".ass", ".vtt"}
CARPETAS = {"media": MEDIA, "out": OUT}


def asegurar_carpetas() -> None:
    for d in (MEDIA, OUT, PROYECTOS / "videos", PROYECTOS / "flyers", CACHE):
        d.mkdir(parents=True, exist_ok=True)


def tipo_archivo(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in IMAGE_EXT:
        return "imagen"
    if ext in SUBS_EXT:
        return "subtitulos"
    return "otro"


def nombre_seguro(nombre: str) -> str:
    nombre = Path(unquote(nombre or "")).name
    nombre = re.sub(r"[^\w.\- ()áéíóúÁÉÍÓÚñÑüÜ]", "_", nombre).strip(" .")
    if not nombre:
        raise ValueError("Nombre de archivo inválido")
    return nombre[:120]


def nombre_libre(carpeta: Path, nombre: str) -> Path:
    destino = carpeta / nombre
    stem, ext = destino.stem, destino.suffix
    n = 2
    while destino.exists():
        destino = carpeta / f"{stem} ({n}){ext}"
        n += 1
    return destino


def resolver(rel: str) -> Path:
    """Convierte 'media/x.mp4' u 'out/y.png' en una ruta, sin salir de esas carpetas."""
    rel = (rel or "").replace("\\", "/").lstrip("/")
    partes = rel.split("/", 1)
    if len(partes) != 2 or partes[0] not in CARPETAS:
        raise ValueError(f"Ruta no permitida: {rel}")
    base = CARPETAS[partes[0]].resolve()
    path = (base / partes[1]).resolve()
    if base not in path.parents:
        raise ValueError(f"Ruta no permitida: {rel}")
    return path


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def info_archivo(path: Path) -> dict:
    st = path.stat()
    d = {"nombre": path.name, "ruta": rel(path), "tipo": tipo_archivo(path),
         "tamano": st.st_size, "modificado": st.st_mtime}
    if d["tipo"] in ("video", "audio", "imagen"):
        try:
            p = vedit.probe(path)
            if d["tipo"] != "imagen":
                d["duracion"] = round(p.get("duration") or 0, 2)
            if p.get("width"):
                d["ancho"], d["alto"] = p["width"], p["height"]
        except Exception:
            pass
    return d


_info_cache: dict[tuple, dict] = {}


def listar(carpeta: Path) -> list[dict]:
    items = []
    for p in sorted(carpeta.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file() or p.name.startswith("."):
            continue
        key = (str(p), p.stat().st_mtime, p.stat().st_size)
        if key not in _info_cache:
            _info_cache[key] = info_archivo(p)
        items.append(_info_cache[key])
    return items


def miniatura(path: Path) -> Path:
    st = path.stat()
    clave = f"{path}|{st.st_mtime}|{st.st_size}".encode("utf-8")
    destino = CACHE / f"{hashlib.md5(clave).hexdigest()}.jpg"
    if destino.exists():
        return destino
    t = tipo_archivo(path)
    if t == "video":
        dur = vedit.probe(path)["duration"]
        vedit.ffmpeg(["-ss", f"{min(1.0, dur / 3):.2f}", "-i", str(path), "-frames:v", "1",
                      "-vf", "scale=320:-2", "-q:v", "4", str(destino)])
    elif t == "imagen":
        vedit.ffmpeg(["-i", str(path), "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "4",
                      str(destino)])
    else:
        raise ValueError("Sin miniatura para este tipo de archivo")
    return destino


# --------------------------------------------------------------------------
# Trabajos (se ejecutan de a uno, en segundo plano)
# --------------------------------------------------------------------------

TRABAJOS: dict[str, dict] = {}
COLA: "queue.Queue[str]" = queue.Queue()


def nuevo_trabajo(titulo: str, fn, salida: Path) -> dict:
    tid = uuid.uuid4().hex[:10]
    t = {"id": tid, "titulo": titulo, "estado": "en_cola", "creado": time.time(),
         "salida": rel(salida), "error": None, "_fn": fn}
    TRABAJOS[tid] = t
    COLA.put(tid)
    return publico(t)


def publico(t: dict) -> dict:
    return {k: v for k, v in t.items() if not k.startswith("_")}


def trabajador() -> None:
    while True:
        tid = COLA.get()
        t = TRABAJOS[tid]
        t["estado"] = "procesando"
        t["inicio"] = time.time()
        try:
            t["_fn"]()
            t["estado"] = "listo"
        except vedit.VEditError as e:
            t["estado"], t["error"] = "error", str(e)[-1500:]
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            t["estado"], t["error"] = "error", f"{type(e).__name__}: {e}"
        t["fin"] = time.time()


def correr_vedit(argv: list[str]) -> None:
    args = vedit.build_parser().parse_args(argv)
    vedit.ENC["crf"], vedit.ENC["preset"] = args.crf, args.x264_preset
    args.func(args)


def salida_para(entrada: Path, sufijo: str, ext: str | None = None) -> Path:
    return nombre_libre(OUT, f"{entrada.stem}_{sufijo}{ext or '.mp4'}")


def _txt(v) -> str | None:
    return None if v in (None, "") else str(v)


# Cada herramienta rápida: (sufijo de salida, extensión, constructor de argv)
def _herr_recortar(e, s, o):
    argv = ["trim", e, s, "--start", o.get("inicio") or "0"]
    if _txt(o.get("fin")):
        argv += ["--end", str(o["fin"])]
    return argv


def _herr_vertical(e, s, o):
    return ["reframe", e, s, "--aspect", o.get("formato", "9:16"),
            "--mode", o.get("modo", "blur")]


def _herr_texto(e, s, o):
    argv = ["text", e, s, o.get("texto", "Texto"), "--position", o.get("posicion", "bottom"),
            "--size", str(o.get("tamano", 64)), "--color", o.get("color", "white"),
            "--fade", "0.3"]
    if o.get("caja"):
        argv.append("--box")
    for k, flag in (("inicio", "--start"), ("fin", "--end")):
        if _txt(o.get(k)):
            argv += [flag, str(o[k])]
    return argv


def _herr_musica(e, s, o):
    argv = ["music", e, s, str(resolver(o["musica"])), "--normalize"]
    if _txt(o.get("volumen")):
        argv += ["--volume", str(o["volumen"])]
    if o.get("reemplazar"):
        argv.append("--replace")
    return argv


def _herr_logo(e, s, o):
    return ["watermark", e, s, str(resolver(o["logo"])), "--position",
            o.get("posicion", "bottom-right"), "--scale", str(o.get("escala", 0.15)),
            "--opacity", str(o.get("opacidad", 0.85))]


def _herr_subtitulos(e, s, o):
    return ["subtitles", e, s, str(resolver(o["subtitulos"]))]


HERRAMIENTAS = {
    "recortar": ("recorte", None, _herr_recortar),
    "vertical": ("vertical", None, _herr_vertical),
    "sin_silencios": ("sin_silencios", None, lambda e, s, o: [
        "silence-cut", e, s, "--noise", str(o.get("umbral", -32))]),
    "texto": ("texto", None, _herr_texto),
    "color": ("color", None, lambda e, s, o: ["color", e, s, "--preset",
                                               o.get("preset", "cinematic")]),
    "musica": ("musica", None, _herr_musica),
    "logo": ("logo", None, _herr_logo),
    "subtitulos": ("subtitulos", None, _herr_subtitulos),
    "audio": ("audio", None, lambda e, s, o: ["audio", e, s, "--denoise", "--normalize"]),
    "velocidad": ("velocidad", None, lambda e, s, o: ["speed", e, s, str(o.get("factor", 2))]),
    "estabilizar": ("estable", None, lambda e, s, o: ["stabilize", e, s]),
    "fundido": ("fundido", None, lambda e, s, o: ["fade", e, s, "--in", str(o.get("entrada", 1)),
                                                  "--out", str(o.get("salida", 1))]),
    "comprimir": ("liviano", None, lambda e, s, o: (
        ["compress", e, s, "--target-mb", str(o["mb"])] if _txt(o.get("mb"))
        else ["--crf", "27", "compress", e, s, "--max-width", "1280"])),
    "gif": ("gif", ".gif", lambda e, s, o: ["gif", e, s, "--start", str(o.get("inicio") or 0),
                                            "--duration", str(o.get("duracion") or 4)]),
    "miniatura": ("portada", ".jpg", lambda e, s, o: ["thumbnail", e, s]),
    "extraer_audio": ("audio", ".mp3", lambda e, s, o: ["extract-audio", e, s]),
    "invertir": ("reversa", None, lambda e, s, o: ["reverse", e, s]),
}


def lanzar_herramienta(datos: dict) -> dict:
    nombre = datos.get("herramienta")
    if nombre not in HERRAMIENTAS:
        raise ValueError(f"Herramienta desconocida: {nombre}")
    sufijo, ext, construir = HERRAMIENTAS[nombre]
    entrada = resolver(datos["archivo"])
    salida = salida_para(entrada, sufijo, ext)
    argv = construir(str(entrada), str(salida), datos.get("opciones") or {})
    return nuevo_trabajo(f"{nombre.replace('_', ' ').capitalize()}: {entrada.name}",
                         lambda: correr_vedit(argv), salida)


def validar_timeline(tl: dict) -> dict:
    """Revisa que el proyecto sólo use archivos de media/ u out/."""
    tl = json.loads(json.dumps(tl))  # copia profunda
    for c in tl.get("clips", []):
        if c.get("src"):
            resolver(c["src"])
    for k in ("music", "watermark"):
        if tl.get(k) and tl[k].get("src"):
            resolver(tl[k]["src"])
    if tl.get("subtitles"):
        resolver(tl["subtitles"])
    return tl


def lanzar_render(datos: dict) -> dict:
    tl = validar_timeline(datos.get("proyecto") or {})
    formato = tl.pop("formato", None)
    if formato and not (tl.get("width") and tl.get("height")):
        ancho = {"16:9": 1920}.get(formato, 1080)
        tl["width"] = ancho
        tl["height"] = vedit.even(ancho / vedit.parse_aspect(formato))
    nombre = nombre_seguro(datos.get("nombre") or "mi_video")
    salida = nombre_libre(OUT, f"{Path(nombre).stem}.mp4")
    tl.pop("output", None)
    return nuevo_trabajo(f"Video: {salida.name}",
                         lambda: vedit.render_timeline(tl, str(salida), base_dir=str(ROOT)),
                         salida)


def guardar_flyer(datos: dict) -> dict:
    nombre = Path(nombre_seguro(datos.get("nombre") or "flyer")).stem
    png = datos.get("png", "")
    if "," in png:
        png = png.split(",", 1)[1]
    salida = nombre_libre(OUT, f"{nombre}.png")
    salida.write_bytes(base64.b64decode(png))
    if datos.get("diseno"):
        (PROYECTOS / "flyers" / f"{nombre}.json").write_text(
            json.dumps(datos["diseno"], ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ruta": rel(salida)}


def animar_flyer(datos: dict) -> dict:
    imagen = resolver(datos["imagen"])
    dur = float(datos.get("duracion") or 6)
    info = vedit.probe(imagen)
    w, h = info.get("width") or 1080, info.get("height") or 1920
    escala = min(1.0, 1920 / max(w, h))
    tl = {"width": vedit.even(w * escala), "height": vedit.even(h * escala), "fps": 30,
          "clips": [{"src": str(imagen), "duration": dur, "kenburns": True, "zoom": 1.12}],
          "fade_in": 0.4, "fade_out": 0.6}
    if datos.get("musica"):
        tl["music"] = {"src": str(resolver(datos["musica"])), "replace": True, "volume": 0.9}
    salida = salida_para(imagen, "animado")
    return nuevo_trabajo(f"Flyer animado: {imagen.name}",
                         lambda: vedit.render_timeline(tl, str(salida)), salida)


def listar_proyectos(tipo: str) -> list[dict]:
    carpeta = PROYECTOS / tipo
    return [{"nombre": p.stem, "modificado": p.stat().st_mtime}
            for p in sorted(carpeta.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)]


def leer_proyecto(tipo: str, nombre: str) -> dict:
    p = PROYECTOS / tipo / f"{Path(nombre_seguro(nombre)).stem}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def guardar_proyecto(tipo: str, nombre: str, contenido: dict) -> dict:
    p = PROYECTOS / tipo / f"{Path(nombre_seguro(nombre)).stem}.json"
    p.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"nombre": p.stem}


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "BasetoqueStudio/1.0"

    def log_message(self, fmt, *args):  # silencioso salvo errores
        if os.environ.get("BASETOQUE_DEBUG"):
            super().log_message(fmt, *args)

    # ---- utilidades de respuesta ----
    def enviar_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def enviar_error(self, msg, status=400):
        self.enviar_json({"error": str(msg)}, status)

    def enviar_archivo(self, path: Path, cache=True):
        if not path.is_file():
            return self.enviar_error("No encontrado", 404)
        tipo = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        tamano = path.stat().st_size
        inicio, fin = 0, tamano - 1
        rango = self.headers.get("Range")
        status = 200
        if rango:
            m = re.match(r"bytes=(\d*)-(\d*)", rango)
            if m:
                if m.group(1):
                    inicio = int(m.group(1))
                    if m.group(2):
                        fin = min(int(m.group(2)), tamano - 1)
                elif m.group(2):
                    inicio = max(tamano - int(m.group(2)), 0)
                if inicio > fin:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{tamano}")
                    self.end_headers()
                    return
                status = 206
        largo = fin - inicio + 1
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(largo))
        if status == 206:
            self.send_header("Content-Range", f"bytes {inicio}-{fin}/{tamano}")
        self.send_header("Cache-Control", "no-cache" if cache else "no-store")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(path, "rb") as f:
            f.seek(inicio)
            restante = largo
            while restante > 0:
                trozo = f.read(min(1 << 20, restante))
                if not trozo:
                    break
                try:
                    self.wfile.write(trozo)
                except (BrokenPipeError, ConnectionResetError):
                    return
                restante -= len(trozo)

    def leer_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    # ---- rutas ----
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        ruta = unquote(url.path)
        try:
            if ruta in ("/", "/index.html"):
                return self.enviar_archivo(WEB / "index.html", cache=False)
            if ruta.startswith("/web/"):
                p = (WEB / ruta[5:]).resolve()
                if WEB.resolve() not in p.parents:
                    return self.enviar_error("No encontrado", 404)
                return self.enviar_archivo(p, cache=False)
            if ruta.startswith("/media/") or ruta.startswith("/out/"):
                return self.enviar_archivo(resolver(ruta[1:]))
            if ruta == "/api/estado":
                return self.enviar_json({
                    "version": vedit.VERSION,
                    "ffmpeg": bool(vedit.shutil.which("ffmpeg")),
                    "asistente": asistente.disponible(),
                    "asistente_detalle": asistente.estado(),
                    "presets": sorted(vedit.COLOR_PRESETS),
                    "transiciones": vedit.TRANSITIONS,
                    "carpeta": str(ROOT),
                })
            if ruta == "/api/archivos":
                return self.enviar_json({"media": listar(MEDIA), "out": listar(OUT)})
            if ruta == "/api/miniatura":
                return self.enviar_archivo(miniatura(resolver(q.get("ruta", ""))))
            if ruta == "/api/trabajos":
                lista = sorted(TRABAJOS.values(), key=lambda t: t["creado"], reverse=True)
                return self.enviar_json([publico(t) for t in lista[:30]])
            if ruta.startswith("/api/trabajos/"):
                t = TRABAJOS.get(ruta.rsplit("/", 1)[1])
                return self.enviar_json(publico(t)) if t else self.enviar_error("No existe", 404)
            if ruta in ("/api/proyectos", "/api/flyers"):
                tipo = "videos" if ruta.endswith("proyectos") else "flyers"
                if q.get("nombre"):
                    return self.enviar_json(leer_proyecto(tipo, q["nombre"]))
                return self.enviar_json(listar_proyectos(tipo))
            return self.enviar_error("No encontrado", 404)
        except (ValueError, FileNotFoundError, vedit.VEditError) as e:
            return self.enviar_error(e, 400)

    def do_POST(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        ruta = url.path
        try:
            if ruta == "/api/subir":
                destino = nombre_libre(MEDIA, nombre_seguro(q.get("nombre", "")))
                restante = int(self.headers.get("Content-Length") or 0)
                with open(destino, "wb") as f:
                    while restante > 0:
                        trozo = self.rfile.read(min(1 << 20, restante))
                        if not trozo:
                            break
                        f.write(trozo)
                        restante -= len(trozo)
                return self.enviar_json(info_archivo(destino))
            datos = self.leer_json()
            if ruta == "/api/herramienta":
                return self.enviar_json(lanzar_herramienta(datos))
            if ruta == "/api/render":
                return self.enviar_json(lanzar_render(datos))
            if ruta == "/api/flyer/guardar":
                return self.enviar_json(guardar_flyer(datos))
            if ruta == "/api/flyer/animar":
                return self.enviar_json(animar_flyer(datos))
            if ruta in ("/api/proyectos", "/api/flyers"):
                tipo = "videos" if ruta.endswith("proyectos") else "flyers"
                return self.enviar_json(guardar_proyecto(tipo, datos["nombre"], datos["contenido"]))
            if ruta == "/api/config":
                if "clave" in datos:
                    asistente.guardar_clave(datos["clave"] or "")
                return self.enviar_json({"asistente": asistente.estado()})
            if ruta == "/api/asistente":
                archivos = [f["ruta"] + f" ({f['tipo']}" +
                            (f", {f['duracion']}s" if f.get("duracion") else "") + ")"
                            for f in listar(MEDIA) + listar(OUT)]
                return self.enviar_json(asistente.preguntar(
                    datos.get("mensaje", ""), datos.get("modo", "video"),
                    datos.get("historial") or [], archivos, datos.get("actual")))
            return self.enviar_error("No encontrado", 404)
        except (ValueError, KeyError, FileNotFoundError, vedit.VEditError) as e:
            return self.enviar_error(e, 400)
        except asistente.AsistenteError as e:
            return self.enviar_error(e, 503)

    def do_DELETE(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if url.path == "/api/archivo":
                p = resolver(q.get("ruta", ""))
                if p.is_file():
                    p.unlink()
                return self.enviar_json({"ok": True})
            return self.enviar_error("No encontrado", 404)
        except ValueError as e:
            return self.enviar_error(e, 400)


def crear_servidor(puerto: int = 8765) -> ThreadingHTTPServer:
    asegurar_carpetas()
    threading.Thread(target=trabajador, daemon=True).start()
    return ThreadingHTTPServer(("127.0.0.1", puerto), Handler)


def main() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    puerto = int(os.environ.get("BASETOQUE_PUERTO", "8765"))
    if not vedit.shutil.which("ffmpeg"):
        print("\n⚠  No encontré FFmpeg. Instálalo siguiendo INSTALAR.md y vuelve a abrir.\n")
    try:
        srv = crear_servidor(puerto)
    except OSError:
        print(f"Basetoque Studio ya está abierto en http://127.0.0.1:{puerto}")
        webbrowser.open(f"http://127.0.0.1:{puerto}")
        return
    url = f"http://127.0.0.1:{puerto}"
    print(f"\n  Basetoque Studio está funcionando en {url}")
    print("  Deja esta ventana abierta mientras lo usas. Para cerrar: Ctrl+C\n")
    if not os.environ.get("BASETOQUE_NO_BROWSER"):
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nHasta luego 👋")


if __name__ == "__main__":
    main()
