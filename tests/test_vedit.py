"""Pruebas de extremo a extremo de vedit con medios sintéticos.

Ejecutar:  python3 -m unittest discover -s tests -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import vedit  # noqa: E402


def gen(args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args, check=True)


class VEditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp(prefix="vedit_test_"))
        d = cls.d
        # Clip horizontal 3s con tono; clip vertical 2s; clip sin audio.
        gen(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=3",
             "-f", "lavfi", "-i", "sine=f=440:d=3", "-shortest",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "a.mp4")])
        gen(["-f", "lavfi", "-i", "smptebars=s=360x640:r=25:d=2",
             "-f", "lavfi", "-i", "sine=f=660:d=2", "-shortest",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "b.mp4")])
        gen(["-f", "lavfi", "-i", "mandelbrot=s=640x360:r=30", "-t", "2",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(d / "mudo.mp4")])
        # Voz con silencio en medio: 1s tono, 2s silencio, 1s tono.
        gen(["-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=4",
             "-f", "lavfi", "-i",
             "aevalsrc='if(between(t,1,3),0,0.5*sin(2*PI*300*t))':s=48000:d=4",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "silencio.mp4")])
        gen(["-f", "lavfi", "-i", "sine=f=220:d=10", str(d / "musica.mp3")])
        gen(["-f", "lavfi", "-i", "color=c=red:s=200x100", "-frames:v", "1", str(d / "logo.png")])
        gen(["-f", "lavfi", "-i", "testsrc=s=1200x800", "-frames:v", "1", str(d / "foto.jpg")])
        gen(["-f", "lavfi", "-i", "color=c=0x00FF00:s=640x360:r=30:d=2",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", str(d / "verde.mp4")])
        (d / "subs.srt").write_text(
            "1\n00:00:00,500 --> 00:00:02,000\nHola, mundo: ¿qué tal?\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def run_cli(self, *args):
        rc = vedit.main([str(a) for a in args])
        self.assertEqual(rc, 0, f"vedit {' '.join(map(str, args))} falló")

    def p(self, name):
        return self.d / name

    def assertDuration(self, path, expected, tol=0.25):
        info = vedit.probe(path)
        self.assertAlmostEqual(info["duration"], expected, delta=tol)
        return info

    # ------------------------------------------------------------------
    def test_parse_time(self):
        self.assertEqual(vedit.parse_time("1:30"), 90)
        self.assertEqual(vedit.parse_time("00:01:30.5"), 90.5)
        self.assertEqual(vedit.parse_time(12), 12)
        self.assertIsNone(vedit.parse_time(None))

    def test_atempo_chain(self):
        self.assertEqual(len(vedit.atempo_chain(8)), 3)
        self.assertEqual(len(vedit.atempo_chain(0.2)), 3)

    def test_trim(self):
        out = self.p("trim.mp4")
        self.run_cli("trim", self.p("a.mp4"), out, "--start", "0.5", "--end", "2")
        self.assertDuration(out, 1.5)

    def test_split(self):
        outdir = self.p("partes")
        self.run_cli("split", self.p("a.mp4"), outdir, "--every", "1")
        self.assertEqual(len(list(outdir.glob("*.mp4"))), 3)

    def test_concat_with_transition_mixed_sources(self):
        out = self.p("concat.mp4")
        self.run_cli("concat", self.p("a.mp4"), self.p("b.mp4"), self.p("mudo.mp4"),
                     "-o", out, "--transition", "fade", "--tdur", "0.5", "--fit", "blur")
        info = self.assertDuration(out, 3 + 2 + 2 - 1.0, tol=0.3)
        self.assertEqual((info["width"], info["height"]), (640, 360))
        self.assertTrue(info["has_audio"])

    def test_concat_cut(self):
        out = self.p("concat_cut.mp4")
        self.run_cli("concat", self.p("a.mp4"), self.p("b.mp4"), "-o", out)
        self.assertDuration(out, 5, tol=0.3)

    def test_reframe_vertical(self):
        out = self.p("vertical.mp4")
        self.run_cli("reframe", self.p("a.mp4"), out, "--aspect", "9:16", "--mode", "blur",
                     "--width", "360")
        info = vedit.probe(out)
        self.assertEqual((info["width"], info["height"]), (360, 640))

    def test_speed(self):
        out = self.p("rapido.mp4")
        self.run_cli("speed", self.p("a.mp4"), out, "2")
        self.assertDuration(out, 1.5)

    def test_reverse_rotate_loop(self):
        self.run_cli("reverse", self.p("b.mp4"), self.p("rev.mp4"))
        self.run_cli("rotate", self.p("a.mp4"), self.p("rot.mp4"), "90")
        info = vedit.probe(self.p("rot.mp4"))
        self.assertEqual((info["width"], info["height"]), (360, 640))
        self.run_cli("loop", self.p("b.mp4"), self.p("loop.mp4"), "3")
        self.assertDuration(self.p("loop.mp4"), 6, tol=0.3)

    def test_text_color_fade(self):
        self.run_cli("text", self.p("a.mp4"), self.p("texto.mp4"), "Título: 100% 'listo'",
                     "--start", "0.5", "--end", "2.5", "--fade", "0.3", "--box",
                     "--position", "lower-third")
        self.run_cli("color", self.p("a.mp4"), self.p("color.mp4"), "--preset", "cinematic",
                     "--saturation", "1.2", "--sharpen")
        self.run_cli("fade", self.p("a.mp4"), self.p("fade.mp4"), "--in", "0.5", "--out", "0.5")
        for f in ("texto.mp4", "color.mp4", "fade.mp4"):
            self.assertDuration(self.p(f), 3)

    def test_subtitles_watermark(self):
        self.run_cli("subtitles", self.p("a.mp4"), self.p("subs.mp4"), self.p("subs.srt"))
        self.run_cli("watermark", self.p("a.mp4"), self.p("wm.mp4"), self.p("logo.png"),
                     "--opacity", "0.5")
        self.assertDuration(self.p("wm.mp4"), 3)

    def test_music_ducking_and_replace(self):
        self.run_cli("music", self.p("a.mp4"), self.p("mus.mp4"), self.p("musica.mp3"),
                     "--normalize")
        self.assertDuration(self.p("mus.mp4"), 3)
        self.run_cli("music", self.p("mudo.mp4"), self.p("mus2.mp4"), self.p("musica.mp3"))
        self.assertTrue(vedit.probe(self.p("mus2.mp4"))["has_audio"])

    def test_audio_tools(self):
        self.run_cli("audio", self.p("a.mp4"), self.p("aud.mp4"), "--denoise", "--normalize")
        self.run_cli("audio", self.p("a.mp4"), self.p("mute.mp4"), "--mute")
        self.assertFalse(vedit.probe(self.p("mute.mp4"))["has_audio"])
        self.run_cli("extract-audio", self.p("a.mp4"), self.p("a.mp3"))
        self.assertDuration(self.p("a.mp3"), 3)

    def test_silence_cut(self):
        out = self.p("sin_silencio.mp4")
        self.run_cli("silence-cut", self.p("silencio.mp4"), out)
        info = vedit.probe(out)
        self.assertLess(info["duration"], 3.0)
        self.assertGreater(info["duration"], 1.8)

    def test_scenes(self):
        out = self.p("concat_cut_scenes.mp4")
        self.run_cli("concat", self.p("a.mp4"), self.p("b.mp4"), "-o", out)
        cuts = vedit.detect_scenes(str(out), 0.3)
        self.assertTrue(any(abs(c - 3) < 0.2 for c in cuts), cuts)

    def test_stabilize_compress_gif(self):
        self.run_cli("stabilize", self.p("b.mp4"), self.p("estable.mp4"))
        self.run_cli("compress", self.p("a.mp4"), self.p("comp.mp4"), "--target-mb", "0.2")
        self.assertLess(self.p("comp.mp4").stat().st_size, 0.3 * 1024 * 1024)
        self.run_cli("gif", self.p("a.mp4"), self.p("a.gif"), "--duration", "1", "--width", "200")
        self.assertTrue(self.p("a.gif").exists())

    def test_thumbnail_sheet_frames(self):
        self.run_cli("thumbnail", self.p("a.mp4"), self.p("thumb.jpg"), "--time", "1")
        self.run_cli("thumbnail", self.p("a.mp4"), self.p("thumb_auto.jpg"))
        self.run_cli("sheet", self.p("a.mp4"), self.p("sheet.jpg"), "--cols", "3", "--rows", "2")
        info = vedit.probe(self.p("sheet.jpg"))
        self.assertGreater(info["width"], 1000)
        self.run_cli("frames", self.p("a.mp4"), self.p("frames"), "--count", "3")
        self.assertGreaterEqual(len(list(self.p("frames").glob("*.jpg"))), 3)

    def test_pip_chromakey(self):
        self.run_cli("pip", self.p("a.mp4"), self.p("pip.mp4"), self.p("b.mp4"), "--start", "0.5")
        self.assertDuration(self.p("pip.mp4"), 3)
        self.run_cli("chromakey", self.p("verde.mp4"), self.p("key.mp4"), self.p("foto.jpg"))
        self.assertDuration(self.p("key.mp4"), 2)

    def test_slideshow(self):
        out = self.p("slides.mp4")
        self.run_cli("slideshow", self.p("foto.jpg"), self.p("foto.jpg"), "-o", out,
                     "--duration", "2", "--tdur", "0.5", "--width", "640", "--height", "360",
                     "--music", self.p("musica.mp3"))
        info = self.assertDuration(out, 3.5, tol=0.3)
        self.assertEqual((info["width"], info["height"]), (640, 360))

    def test_render_timeline(self):
        tl = {
            "output": "proyecto.mp4",
            "width": 540, "height": 960, "fps": 30, "fit": "blur",
            "clips": [
                {"color": "black", "duration": 1.5,
                 "text": [{"text": "MI VIDEO", "size": 60, "fade": 0.3, "start": 0, "end": 1.5}],
                 "transition": {"type": "fadeblack", "duration": 0.4}},
                {"src": "a.mp4", "start": 0.5, "end": 2.5, "speed": 1.5, "color_grade": "warm",
                 "transition": "slideleft"},
                {"src": "foto.jpg", "duration": 2, "kenburns": True},
                {"src": "b.mp4", "volume": 0.5, "reverse": True},
            ],
            "text": [{"text": "@basetoque", "position": "top-right", "size": 28}],
            "color": {"preset": "vivid"},
            "subtitles": "subs.srt",
            "watermark": {"src": "logo.png", "scale": 0.1},
            "music": {"src": "musica.mp3", "volume": 0.2},
            "fade_in": 0.3, "fade_out": 0.5, "loudnorm": True,
        }
        tl_path = self.p("proyecto.json")
        tl_path.write_text(json.dumps(tl), encoding="utf-8")
        self.run_cli("render", tl_path)
        expected = 1.5 + 2 / 1.5 + 2 + 2 - 0.4 - 0.5
        info = self.assertDuration(self.p("proyecto.mp4"), expected, tol=0.35)
        self.assertEqual((info["width"], info["height"]), (540, 960))
        self.assertTrue(info["has_audio"])

    def test_errors(self):
        self.assertEqual(vedit.main(["info", str(self.p("noexiste.mp4"))]), 1)
        self.assertEqual(vedit.main(["color", str(self.p("a.mp4")), str(self.p("x.mp4")),
                                     "--lut", str(self.p("noexiste.cube"))]), 1)


if __name__ == "__main__":
    unittest.main()
