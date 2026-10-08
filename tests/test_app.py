"""Pruebas del servidor de Basetoque Studio (API local) y del asistente.

Ejecutar:  python3 -m unittest discover -s tests -v
"""
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import asistente, server  # noqa: E402


def gen(args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args, check=True)


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="basetoque_app_"))
        server.ROOT = cls.tmp
        server.MEDIA, server.OUT = cls.tmp / "media", cls.tmp / "out"
        server.PROYECTOS, server.CACHE = cls.tmp / "proyectos", cls.tmp / ".cache"
        server.CARPETAS.update(media=server.MEDIA, out=server.OUT)
        cls.srv = server.crear_servidor(0)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

        src = cls.tmp / "src"
        src.mkdir()
        gen(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=3", "-f", "lavfi", "-i", "sine=f=440:d=3",
             "-shortest", "-pix_fmt", "yuv420p", str(src / "clip.mp4")])
        gen(["-f", "lavfi", "-i", "testsrc=s=800x600", "-frames:v", "1", str(src / "foto.jpg")])
        gen(["-f", "lavfi", "-i", "sine=f=220:d=8", str(src / "tema.mp3")])
        for f in src.iterdir():
            cls.subir(f)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---- utilidades ----
    @classmethod
    def subir(cls, path: Path):
        req = urllib.request.Request(f"{cls.base}/api/subir?nombre={path.name}", data=path.read_bytes(),
                                     method="POST")
        return json.load(urllib.request.urlopen(req))

    def get(self, ruta):
        return json.load(urllib.request.urlopen(self.base + ruta))

    def post(self, ruta, data):
        req = urllib.request.Request(self.base + ruta, data=json.dumps(data).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            return 200, json.load(urllib.request.urlopen(req))
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def esperar(self, trabajo, limite=120):
        fin = time.time() + limite
        while time.time() < fin:
            t = self.get(f"/api/trabajos/{trabajo['id']}")
            if t["estado"] in ("listo", "error"):
                self.assertEqual(t["estado"], "listo", t.get("error"))
                return t
            time.sleep(0.3)
        self.fail("El trabajo no terminó a tiempo")

    # ---- pruebas ----
    def test_interfaz_y_estado(self):
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.assertIn("Basetoque", html)
        for f in ("app.js", "flyer.js", "app.css"):
            self.assertEqual(urllib.request.urlopen(f"{self.base}/web/{f}").status, 200)
        estado = self.get("/api/estado")
        self.assertTrue(estado["ffmpeg"])
        self.assertIn("cinematic", estado["presets"])

    def test_listado_miniatura_y_rangos(self):
        a = self.get("/api/archivos")
        tipos = {f["nombre"]: f["tipo"] for f in a["media"]}
        self.assertEqual(tipos["clip.mp4"], "video")
        self.assertEqual(tipos["foto.jpg"], "imagen")
        self.assertEqual(tipos["tema.mp3"], "audio")
        r = urllib.request.urlopen(f"{self.base}/api/miniatura?ruta=media/clip.mp4")
        self.assertEqual(r.headers["Content-Type"], "image/jpeg")
        req = urllib.request.Request(f"{self.base}/media/clip.mp4", headers={"Range": "bytes=0-99"})
        r = urllib.request.urlopen(req)
        self.assertEqual(r.status, 206)
        self.assertEqual(len(r.read()), 100)

    def test_rutas_fuera_de_carpetas_bloqueadas(self):
        for ruta in ("/media/../server.py", "/api/miniatura?ruta=../etc/passwd"):
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(self.base + ruta)
        code, r = self.post("/api/render", {"proyecto": {"clips": [{"src": "/etc/passwd", "duration": 1}]}})
        self.assertEqual(code, 400)
        code, r = self.post("/api/herramienta", {"herramienta": "vertical", "archivo": "../x.mp4"})
        self.assertEqual(code, 400)

    def test_herramientas_rapidas(self):
        code, t = self.post("/api/herramienta", {"herramienta": "vertical", "archivo": "media/clip.mp4",
                                                 "opciones": {"formato": "9:16", "modo": "blur"}})
        self.assertEqual(code, 200)
        t = self.esperar(t)
        info = server.vedit.probe(server.resolver(t["salida"]))
        self.assertLess(info["width"], info["height"])
        code, t = self.post("/api/herramienta", {"herramienta": "musica", "archivo": "media/clip.mp4",
                                                 "opciones": {"musica": "media/tema.mp3", "volumen": "0.2"}})
        self.esperar(t)
        code, t = self.post("/api/herramienta", {"herramienta": "texto", "archivo": "media/clip.mp4",
                                                 "opciones": {"texto": "Hola: 100% 'listo'", "caja": True}})
        self.esperar(t)
        code, r = self.post("/api/herramienta", {"herramienta": "no_existe", "archivo": "media/clip.mp4"})
        self.assertEqual(code, 400)

    def test_render_de_proyecto_con_formato(self):
        proyecto = {"formato": "1:1", "fit": "blur", "clips": [
            {"color": "#222222", "duration": 1, "text": [{"text": "TÍTULO", "size": 60}], "transition": "fade"},
            {"src": "media/clip.mp4", "start": 0.5, "end": 2.5},
            {"src": "media/foto.jpg", "duration": 1.5, "kenburns": True}],
            "music": {"src": "media/tema.mp3", "volume": 0.3}, "fade_out": 0.5}
        code, t = self.post("/api/render", {"nombre": "mi reel", "proyecto": proyecto})
        self.assertEqual(code, 200)
        t = self.esperar(t)
        info = server.vedit.probe(server.resolver(t["salida"]))
        self.assertEqual((info["width"], info["height"]), (1080, 1080))
        self.assertTrue(info["has_audio"])

    def test_proyectos_y_flyers(self):
        code, r = self.post("/api/proyectos", {"nombre": "Mi proyecto", "contenido": {"clips": []}})
        self.assertEqual(code, 200)
        self.assertIn("Mi proyecto", [p["nombre"] for p in self.get("/api/proyectos")])
        self.assertEqual(self.get("/api/proyectos?nombre=Mi%20proyecto"), {"clips": []})

        png = self.tmp / "src" / "flyer.png"
        gen(["-f", "lavfi", "-i", "color=c=red:s=540x960", "-frames:v", "1", str(png)])
        datos = "data:image/png;base64," + base64.b64encode(png.read_bytes()).decode()
        code, r = self.post("/api/flyer/guardar", {"nombre": "fiesta", "png": datos,
                                                   "diseno": {"ancho": 540, "alto": 960, "elementos": []}})
        self.assertEqual(code, 200)
        self.assertTrue(server.resolver(r["ruta"]).exists())
        self.assertEqual(self.get("/api/flyers?nombre=fiesta")["ancho"], 540)
        code, t = self.post("/api/flyer/animar", {"imagen": r["ruta"], "duracion": 2,
                                                  "musica": "media/tema.mp3"})
        t = self.esperar(t)
        info = server.vedit.probe(server.resolver(t["salida"]))
        self.assertAlmostEqual(info["duration"], 2, delta=0.3)

    def test_asistente_sin_configurar(self):
        clave_previa = asistente._clave
        asistente._clave = lambda: None
        try:
            if asistente.estado() == "listo":
                self.skipTest("Hay una clave real configurada en el entorno")
            code, r = self.post("/api/asistente", {"mensaje": "hola", "modo": "video"})
            self.assertEqual(code, 503)
        finally:
            asistente._clave = clave_previa


class AsistenteTest(unittest.TestCase):
    def test_extraer_json(self):
        texto, data = asistente._extraer_json('Te propongo esto:\n```json\n{"clips": [1]}\n```\n¿Te gusta?')
        self.assertEqual(data, {"clips": [1]})
        self.assertNotIn("```", texto)
        self.assertEqual(asistente._extraer_json("Sólo charla")[1], None)

    def test_preguntar_con_cliente_simulado(self):
        llamadas = {}

        class Resp:
            stop_reason = "end_turn"
            content = [types.SimpleNamespace(type="thinking", thinking=""),
                       types.SimpleNamespace(type="text", text='Listo:\n```json\n{"formato": "9:16", "clips": []}\n```')]

        class Mensajes:
            def create(self, **kw):
                llamadas.update(kw)
                return Resp()

        class Cliente:
            def __init__(self, **kw):
                self.beta = types.SimpleNamespace(messages=Mensajes())

        falso = types.SimpleNamespace(Anthropic=Cliente, **{n: type(n, (Exception,), {}) for n in (
            "AuthenticationError", "PermissionDeniedError", "RateLimitError", "APIConnectionError",
            "APIStatusError")})
        original, clave = asistente.anthropic, asistente._clave
        asistente.anthropic, asistente._clave = falso, (lambda: "sk-prueba")
        try:
            r = asistente.preguntar("haz un reel", "video", [{"role": "user", "content": "hola"},
                                                            {"role": "assistant", "content": "¡hola!"}],
                                    ["media/clip.mp4 (video, 3s)"])
        finally:
            asistente.anthropic, asistente._clave = original, clave
        self.assertEqual(r["diseno"], {"formato": "9:16", "clips": []})
        self.assertEqual(llamadas["model"], "claude-opus-5-5")
        self.assertEqual(llamadas["fallbacks"], "default")
        self.assertIn("media/clip.mp4", llamadas["messages"][-1]["content"])
        self.assertEqual(len(llamadas["messages"]), 3)


if __name__ == "__main__":
    unittest.main()
