#!/usr/bin/env python3
"""vedit — editor de video por línea de comandos construido sobre FFmpeg.

Sin dependencias de Python más allá de la librería estándar. Requiere
`ffmpeg` y `ffprobe` en el PATH.

Ejemplos rápidos:
    python3 vedit.py info clip.mp4
    python3 vedit.py trim clip.mp4 corto.mp4 --start 0:05 --end 0:20
    python3 vedit.py concat a.mp4 b.mp4 c.mp4 -o final.mp4 --transition fade
    python3 vedit.py reframe horizontal.mp4 vertical.mp4 --aspect 9:16 --mode blur
    python3 vedit.py render proyecto.json

Ejecuta `python3 vedit.py <comando> -h` para ver las opciones de cada comando.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

VERSION = "1.0.0"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

TRANSITIONS = [
    "fade", "fadeblack", "fadewhite", "dissolve", "wipeleft", "wiperight",
    "wipeup", "wipedown", "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose", "radial", "smoothleft", "smoothright",
    "pixelize", "zoomin", "distance", "hblur",
]

COLOR_PRESETS = {
    "cinematic": ["eq=contrast=1.08:saturation=0.9",
                  "colorbalance=rs=-0.04:bs=0.06:rh=0.06:bh=-0.05",
                  "vignette=PI/5"],
    "bw": ["hue=s=0", "eq=contrast=1.15"],
    "vintage": ["curves=preset=vintage", "vignette=PI/4"],
    "warm": ["colorbalance=rs=0.08:gs=0.02:bs=-0.08:rm=0.04:bm=-0.04"],
    "cool": ["colorbalance=rs=-0.06:bs=0.08:rm=-0.03:bm=0.04"],
    "vivid": ["eq=saturation=1.35:contrast=1.06"],
    "dramatic": ["eq=contrast=1.3:saturation=0.85:gamma=0.95", "vignette=PI/4"],
    "fade": ["curves=all='0/0.08 1/0.92'", "eq=saturation=0.85"],
}

ENC = {"crf": 20, "preset": "medium"}
VERBOSE = False


class VEditError(Exception):
    pass


# --------------------------------------------------------------------------
# Utilidades básicas
# --------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def parse_time(value) -> float | None:
    """Acepta 90, '90', '1:30', '00:01:30.5' y devuelve segundos."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    parts = str(value).strip().split(":")
    try:
        secs = 0.0
        for p in parts:
            secs = secs * 60 + float(p)
    except ValueError:
        raise VEditError(f"Tiempo inválido: {value!r}")
    return secs


def fmt_time(secs: float) -> str:
    h, rem = divmod(max(secs, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def ffpath(path) -> str:
    """Escapa una ruta para usarla dentro de un filtro de FFmpeg (p.ej. C:\\x en Windows)."""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "'\\\\\\''")


def even(n: float) -> int:
    n = int(round(n))
    return n if n % 2 == 0 else n + 1


def ffmpeg(args: list[str], capture_log: bool = False) -> str:
    level = "info" if capture_log else "error"
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", level] + args
    if VERBOSE:
        log("$ " + " ".join(shlex.quote(c) for c in cmd))
    p = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, errors="replace")
    if p.returncode != 0:
        raise VEditError("ffmpeg falló:\n" + p.stderr[-4000:])
    return p.stderr


def probe(path) -> dict:
    path = str(path)
    if not os.path.exists(path):
        raise VEditError(f"No existe el archivo: {path}")
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True)
    if p.returncode != 0:
        raise VEditError(f"ffprobe no pudo leer {path}: {p.stderr.strip()}")
    data = json.loads(p.stdout)
    fmt = data.get("format", {})
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    info = {
        "path": path,
        "duration": float(fmt.get("duration") or (v or {}).get("duration") or 0),
        "size_bytes": int(fmt.get("size") or 0),
        "bitrate": int(fmt.get("bit_rate") or 0),
        "format": fmt.get("format_name"),
        "has_video": v is not None,
        "has_audio": a is not None,
    }
    if v:
        w, h = int(v.get("width", 0)), int(v.get("height", 0))
        rotation = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rotation = int(sd["rotation"])
        rotation = int(v.get("tags", {}).get("rotate", rotation))
        if abs(rotation) % 180 == 90:
            w, h = h, w
        rate = v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"
        try:
            fps = float(Fraction(rate)) if rate != "0/0" else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0
        info.update(width=w, height=h, fps=round(fps, 3), vcodec=v.get("codec_name"),
                    pix_fmt=v.get("pix_fmt"), rotation=rotation)
    if a:
        info.update(acodec=a.get("codec_name"), sample_rate=int(a.get("sample_rate") or 0),
                    channels=a.get("channels"))
    return info


def is_image(path) -> bool:
    return Path(str(path)).suffix.lower() in IMAGE_EXTS


def default_font() -> str | None:
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return f
    return None


def out_codecs(output: str, crf: int | None = None, audio: bool = True) -> list[str]:
    ext = Path(output).suffix.lower()
    crf = crf if crf is not None else ENC["crf"]
    if ext == ".webm":
        v = ["-c:v", "libvpx-vp9", "-crf", str(crf + 12), "-b:v", "0", "-row-mt", "1"]
        a = ["-c:a", "libopus", "-b:a", "160k"]
    else:
        v = ["-c:v", "libx264", "-preset", ENC["preset"], "-crf", str(crf),
             "-pix_fmt", "yuv420p"]
        a = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
        if ext in (".mp4", ".mov", ".m4v"):
            v += ["-movflags", "+faststart"]
    return v + (a if audio else ["-an"])


def atempo_chain(factor: float) -> list[str]:
    parts = []
    while factor > 2.0:
        parts.append("atempo=2.0")
        factor /= 2.0
    while factor < 0.5:
        parts.append("atempo=0.5")
        factor /= 0.5
    parts.append(f"atempo={factor:.6f}")
    return parts


class TempDir:
    def __init__(self):
        self.path = Path(tempfile.mkdtemp(prefix="vedit_"))
        self._n = 0

    def file(self, suffix: str) -> str:
        self._n += 1
        return str(self.path / f"f{self._n:04d}{suffix}")

    def write(self, content: str, suffix: str = ".txt") -> str:
        p = self.file(suffix)
        Path(p).write_text(content, encoding="utf-8")
        return p

    def copy(self, src: str) -> str:
        if not os.path.exists(src):
            raise VEditError(f"No existe el archivo: {src}")
        p = self.file(Path(src).suffix)
        shutil.copy(src, p)
        return p

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if os.environ.get("VEDIT_KEEP_TEMP"):
            log(f"(temporales conservados en {self.path})")
        else:
            shutil.rmtree(self.path, ignore_errors=True)


# --------------------------------------------------------------------------
# Constructores de filtros
# --------------------------------------------------------------------------

def position_xy(position: str, kind: str = "text", margin: float = 0.05) -> tuple[str, str]:
    """Devuelve expresiones x,y para drawtext ('text') u overlay ('overlay')."""
    if kind == "text":
        W, H, w, h = "w", "h", "text_w", "text_h"
    else:
        W, H, w, h = "main_w", "main_h", "overlay_w", "overlay_h"
    position = (position or "center").lower()
    m = re.fullmatch(r"\s*(center|-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", position)
    if m:  # "x,y" en píxeles; x puede ser "center" para centrar horizontalmente
        return (f"({W}-{w})/2" if m.group(1) == "center" else m.group(1)), m.group(2)
    mx, my = f"{W}*{margin}", f"{H}*{margin}"
    cx, cy = f"({W}-{w})/2", f"({H}-{h})/2"
    left, right = mx, f"{W}-{w}-{mx}"
    top, bottom = my, f"{H}-{h}-{H}*{margin * 1.4:.3f}"
    table = {
        "center": (cx, cy), "top": (cx, top), "bottom": (cx, bottom),
        "left": (left, cy), "right": (right, cy),
        "top-left": (left, top), "top-right": (right, top),
        "bottom-left": (left, bottom), "bottom-right": (right, bottom),
        "lower-third": (left, f"{H}*0.72"),
    }
    if position not in table:
        raise VEditError(f"Posición desconocida: {position}. Usa una de {sorted(table)} o 'x,y'.")
    return table[position]


def drawtext_filter(spec: dict, tmp: TempDir, expand: bool = False) -> str:
    """Construye un filtro drawtext a partir de un dict de texto."""
    text = str(spec.get("text", ""))
    path = tmp.write(text)
    size = spec.get("size", 64)
    color = spec.get("color", "white")
    x, y = position_xy(spec.get("position", "center"), "text")
    font = spec.get("font")
    opts = [f"textfile='{ffpath(path)}'", f"expansion={'normal' if expand else 'none'}"]
    if font and os.path.exists(font):
        opts.append(f"fontfile='{ffpath(font)}'")
    elif font:
        opts.append(f"font='{font}'")
    elif default_font():
        opts.append(f"fontfile='{ffpath(default_font())}'")
    opts += [f"fontsize={size}", f"fontcolor={color}", f"x={x}", f"y={y}", "line_spacing=10"]
    outline = spec.get("outline", 3)
    if outline:
        opts += [f"borderw={outline}", f"bordercolor={spec.get('outline_color', 'black@0.7')}"]
    if spec.get("shadow", False):
        opts += ["shadowx=3", "shadowy=3", "shadowcolor=black@0.6"]
    if spec.get("box"):
        box_color = spec["box"] if isinstance(spec["box"], str) else "black@0.55"
        opts += ["box=1", f"boxcolor={box_color}", f"boxborderw={int(int(size) * 0.4)}"]
    start = parse_time(spec.get("start"))
    end = parse_time(spec.get("end"))
    if start is not None or end is not None:
        s = start or 0.0
        cond = f"between(t,{s},{end})" if end is not None else f"gte(t,{s})"
        opts.append(f"enable='{cond}'")
        fade = float(spec.get("fade", 0) or 0)
        if fade > 0:
            if end is not None:
                alpha = f"if(lt(t,{s + fade}),(t-{s})/{fade},if(gt(t,{end - fade}),({end}-t)/{fade},1))"
            else:
                alpha = f"if(lt(t,{s + fade}),(t-{s})/{fade},1)"
            opts.append(f"alpha='{alpha}'")
    return "drawtext=" + ":".join(opts)


def color_filters(spec, tmp: TempDir) -> list[str]:
    """spec puede ser un nombre de preset o un dict con preset/brightness/...."""
    if not spec:
        return []
    if isinstance(spec, str):
        spec = {"preset": spec}
    filters: list[str] = []
    preset = spec.get("preset")
    if preset:
        if preset not in COLOR_PRESETS:
            raise VEditError(f"Preset de color desconocido: {preset}. Opciones: {sorted(COLOR_PRESETS)}")
        filters += COLOR_PRESETS[preset]
    eq = []
    for key in ("brightness", "contrast", "saturation", "gamma"):
        if spec.get(key) is not None:
            eq.append(f"{key}={float(spec[key])}")
    if eq:
        filters.append("eq=" + ":".join(eq))
    if spec.get("temperature") is not None:
        t = float(spec["temperature"])  # -1 (frío) .. 1 (cálido)
        filters.append(f"colorbalance=rs={0.1 * t:.3f}:bs={-0.1 * t:.3f}")
    if spec.get("sharpen"):
        filters.append("unsharp=5:5:0.8:3:3:0.4")
    if spec.get("denoise"):
        filters.append("hqdn3d=3:3:6:6")
    if spec.get("vignette"):
        filters.append("vignette=PI/5")
    if spec.get("lut"):
        filters.append(f"lut3d=file='{ffpath(tmp.copy(spec['lut']))}'")
    return filters


def fit_graph(src: str, dst: str, W: int, H: int, mode: str) -> str:
    """Encaja [src] en un lienzo WxH: pad (barras), crop (recorta) o blur (fondo desenfocado)."""
    if mode == "crop":
        return (f"[{src}]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},setsar=1[{dst}]")
    if mode == "stretch":
        return f"[{src}]scale={W}:{H},setsar=1[{dst}]"
    if mode == "blur":
        return (f"[{src}]split=2[{dst}_a][{dst}_b];"
                f"[{dst}_a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=luma_radius=min(h\\,w)/20:luma_power=2[{dst}_bg];"
                f"[{dst}_b]scale={W}:{H}:force_original_aspect_ratio=decrease[{dst}_fg];"
                f"[{dst}_bg][{dst}_fg]overlay=(W-w)/2:(H-h)/2,setsar=1[{dst}]")
    if mode == "pad":
        return (f"[{src}]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[{dst}]")
    raise VEditError(f"Modo de encuadre desconocido: {mode} (usa pad, crop, blur o stretch)")


def parse_aspect(aspect: str) -> float:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[:/x]\s*(\d+(?:\.\d+)?)\s*", aspect)
    if m:
        return float(m.group(1)) / float(m.group(2))
    return float(aspect)


# --------------------------------------------------------------------------
# Post-proceso: una sola pasada que aplica color, textos, subtítulos,
# fundidos, marca de agua, música y audio. La usan varios comandos.
# --------------------------------------------------------------------------

def post_process(src: str, output: str, opts: dict, crf: int | None = None) -> None:
    info = probe(src)
    L = info["duration"]
    with TempDir() as tmp:
        inputs = ["-i", src]
        n_in = 1
        graph: list[str] = []
        vf: list[str] = []

        vf += color_filters(opts.get("color"), tmp)
        for t in opts.get("text", []) or []:
            vf.append(drawtext_filter(t, tmp))
        if opts.get("subtitles"):
            sub = tmp.copy(opts["subtitles"])
            style = opts.get("subtitle_style")
            if style is None:
                style = "FontName=DejaVu Sans,FontSize=18,Bold=1,Outline=2,Shadow=0,MarginV=30"
            vf.append(f"subtitles='{ffpath(sub)}'" + (f":force_style='{style}'" if style else ""))
        fi, fo = float(opts.get("fade_in") or 0), float(opts.get("fade_out") or 0)
        if fi > 0:
            vf.append(f"fade=t=in:st=0:d={fi}")
        if fo > 0:
            vf.append(f"fade=t=out:st={max(L - fo, 0):.3f}:d={fo}")
        graph.append(f"[0:v]{','.join(vf) if vf else 'null'}[vb]")

        wm = opts.get("watermark")
        if wm:
            inputs += ["-i", wm["src"]]
            idx = n_in
            n_in += 1
            width = even(info["width"] * float(wm.get("scale", 0.15)))
            opacity = float(wm.get("opacity", 0.8))
            x, y = position_xy(wm.get("position", "bottom-right"), "overlay", 0.03)
            graph.append(f"[{idx}:v]scale={width}:-2,format=rgba,"
                         f"colorchannelmixer=aa={opacity}[wm]")
            graph.append(f"[vb][wm]overlay=x={x}:y={y}:eof_action=repeat[v]")
        else:
            graph.append("[vb]null[v]")

        # ---------------- audio ----------------
        music = opts.get("music")
        af: list[str] = []
        if opts.get("denoise"):
            af += ["highpass=f=80", "afftdn=nf=-25"]
        if opts.get("volume") is not None:
            af.append(f"volume={float(opts['volume'])}")
        if fi > 0:
            af.append(f"afade=t=in:st=0:d={fi}")
        if fo > 0:
            af.append(f"afade=t=out:st={max(L - fo, 0):.3f}:d={fo}")
        keep_original = info["has_audio"] and not (music and music.get("replace"))
        audio_label = None
        if keep_original:
            graph.append(f"[0:a]{','.join(af) if af else 'anull'}[ab]")
            audio_label = "ab"
        if music:
            inputs += ["-stream_loop", "-1", "-i", music["src"]]
            idx = n_in
            n_in += 1
            replace = bool(music.get("replace")) or not keep_original
            vol = music.get("volume")
            vol = float(vol if vol is not None else (1.0 if replace else 0.25))
            mstart = parse_time(music.get("start")) or 0.0
            mfade = music.get("fade_out")
            mfade = float(mfade if mfade is not None else 2.0)
            chain = [f"atrim=start={mstart}:duration={L:.3f}", "asetpts=PTS-STARTPTS",
                     "aresample=48000", "aformat=channel_layouts=stereo", f"volume={vol}"]
            if mfade > 0:
                chain.append(f"afade=t=out:st={max(L - mfade, 0):.3f}:d={mfade}")
            if replace and fi > 0:
                chain.append(f"afade=t=in:st=0:d={fi}")
            graph.append(f"[{idx}:a]{','.join(chain)}[mus]")
            if replace:
                audio_label = "mus"
            elif music.get("duck", True):
                graph.append("[ab]asplit=2[voz][sc]")
                graph.append("[mus][sc]sidechaincompress=threshold=0.02:ratio=10:"
                             "attack=15:release=500:makeup=1[musd]")
                graph.append("[voz][musd]amix=inputs=2:duration=first:normalize=0[amix]")
                audio_label = "amix"
            else:
                graph.append("[ab][mus]amix=inputs=2:duration=first:normalize=0[amix]")
                audio_label = "amix"
        if audio_label and opts.get("loudnorm"):
            graph.append(f"[{audio_label}]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[an]")
            audio_label = "an"

        args = inputs + ["-filter_complex", ";".join(graph), "-map", "[v]"]
        if audio_label:
            args += ["-map", f"[{audio_label}]"]
        args += ["-t", f"{L:.3f}"] + out_codecs(output, crf, audio=bool(audio_label)) + [output]
        ffmpeg(args)


# --------------------------------------------------------------------------
# Render de línea de tiempo (JSON)
# --------------------------------------------------------------------------

def _clip_duration(clip: dict, info: dict | None) -> float:
    start = parse_time(clip.get("start")) or 0.0
    end = parse_time(clip.get("end"))
    if clip.get("duration") is not None:
        return float(parse_time(clip["duration"]))
    if end is not None:
        return end - start
    if info and info["duration"]:
        return info["duration"] - start
    raise VEditError(f"El clip {clip.get('src') or clip} necesita 'duration'.")


def render_segment(clip: dict, out: str, W: int, H: int, fps: float, tmp: TempDir) -> float:
    """Normaliza un clip (video, imagen o color) a WxH@fps con audio estéreo 48k."""
    speed = float(clip.get("speed", 1.0))
    fit = clip.get("fit", "pad")
    src = clip.get("src")
    inputs: list[str] = []
    graph: list[str] = []
    vpre: list[str] = []
    has_audio = False

    if src is None and clip.get("color"):
        dur = float(parse_time(clip.get("duration", 3)))
        inputs += ["-f", "lavfi", "-i", f"color=c={clip['color']}:s={W}x{H}:r={fps}:d={dur:.3f}"]
        out_dur = dur
        graph.append("[0:v]null[fit]")
    elif src and is_image(src):
        dur = float(parse_time(clip.get("duration", 4)))
        out_dur = dur
        if clip.get("kenburns"):
            frames = max(int(round(dur * fps)), 1)
            zoom = float(clip.get("zoom", 1.25))
            step = (zoom - 1.0) / frames
            inputs += ["-i", src]
            # Escalar primero a 2x evita el temblor típico de zoompan.
            graph.append(
                f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
                f"crop={W * 2}:{H * 2},"
                f"zoompan=z='min(1+{step:.6f}*on,{zoom})':d={frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={fps},setsar=1[fit]")
        else:
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", src]
            graph.append(fit_graph("0:v", "fit", W, H, fit))
    else:
        info = probe(src)
        start = parse_time(clip.get("start")) or 0.0
        dur = _clip_duration(clip, info)
        if dur <= 0:
            raise VEditError(f"Duración no válida para {src} (start={start}, dur={dur}).")
        out_dur = dur / speed
        inputs += ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src]
        has_audio = info["has_audio"] and not clip.get("mute")
        if clip.get("reverse"):
            vpre.append("reverse")
        if speed != 1.0:
            vpre.append(f"setpts=PTS/{speed}")
        zoom = float(clip.get("zoom") or 1.0)
        if zoom > 1.0:  # acercamiento, centrado un poco arriba (donde suele estar la cara)
            vpre.append(f"crop=trunc(iw/{zoom}/2)*2:trunc(ih/{zoom}/2)*2:(iw-ow)/2:(ih-oh)*0.4")
        graph.append(f"[0:v]{','.join(vpre) if vpre else 'null'}[pre]")
        graph.append(fit_graph("pre", "fit", W, H, fit))

    post = [f"fps={fps}", "format=yuv420p"]
    post += color_filters(clip.get("color_grade"), tmp)
    for t in clip.get("text", []) or []:
        post.append(drawtext_filter(t, tmp))
    for kind in ("fade_in", "fade_out"):
        d = float(clip.get(kind) or 0)
        if d > 0:
            st = 0 if kind == "fade_in" else max(out_dur - d, 0)
            post.append(f"fade=t={kind[5:]}:st={st:.3f}:d={d}")
    graph.append(f"[fit]{','.join(post)}[v]")

    if has_audio:
        achain = ["aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo"]
        if clip.get("reverse"):
            achain.append("areverse")
        if speed != 1.0:
            achain += atempo_chain(speed)
        if clip.get("volume") is not None:
            achain.append(f"volume={float(clip['volume'])}")
        achain.append("apad")
        graph.append(f"[0:a]{','.join(achain)}[a]")
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        graph.append("[1:a]anull[a]")

    ffmpeg(inputs + ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]",
                     "-t", f"{out_dur:.3f}", "-r", str(fps),
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
                     "-ar", "48000", "-ac", "2", out])
    return out_dur


def assemble(segments: list[str], durations: list[float], transitions: list[dict | None],
             out: str, fps: float) -> float:
    """Une segmentos normalizados. transitions[i] es la transición entre i e i+1."""
    if len(segments) == 1:
        shutil.copy(segments[0], out)
        return durations[0]
    inputs: list[str] = []
    for s in segments:
        inputs += ["-i", s]
    graph = []
    for i in range(len(segments)):
        graph.append(f"[{i}:v]fps={fps},settb=AVTB,format=yuv420p,setsar=1[v{i}]")
        graph.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")
    cur_v, cur_a, L = "v0", "a0", durations[0]
    for i in range(1, len(segments)):
        tr = transitions[i - 1]
        nv, na = f"xv{i}", f"xa{i}"
        if tr and tr.get("type", "fade") != "cut" and float(tr.get("duration", 0.5)) > 0:
            T = min(float(tr.get("duration", 0.5)), durations[i - 1] * 0.45, durations[i] * 0.45)
            kind = tr.get("type", "fade")
            if kind not in TRANSITIONS:
                raise VEditError(f"Transición desconocida: {kind}. Opciones: {TRANSITIONS}")
            graph.append(f"[{cur_v}][v{i}]xfade=transition={kind}:duration={T:.3f}:"
                         f"offset={L - T:.3f}[{nv}]")
            graph.append(f"[{cur_a}][a{i}]acrossfade=d={T:.3f}[{na}]")
            L += durations[i] - T
        else:
            graph.append(f"[{cur_v}][{cur_a}][v{i}][a{i}]concat=n=2:v=1:a=1[{nv}][{na}]")
            L += durations[i]
        cur_v, cur_a = nv, na
    ffmpeg(inputs + ["-filter_complex", ";".join(graph), "-map", f"[{cur_v}]",
                     "-map", f"[{cur_a}]", "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", out])
    return L


def render_timeline(tl: dict, output: str | None = None, base_dir: str | None = None) -> str:
    base = Path(base_dir or ".")

    def resolve(p):
        if p is None:
            return None
        pp = Path(p).expanduser()
        if pp.is_absolute():
            return str(pp)
        # Relativa al JSON; si no existe ahí, a la carpeta actual o a la del proyecto Basetoque
        for raiz in (base, Path.cwd(), Path(__file__).resolve().parent):
            if (raiz / pp).exists():
                return str(raiz / pp)
        return str(base / pp)

    clips = [dict(c) for c in tl.get("clips", [])]
    if not clips:
        raise VEditError("La línea de tiempo no tiene clips.")
    for c in clips:
        c["src"] = resolve(c.get("src"))
    output = output or resolve(tl.get("output", "salida.mp4"))

    first_video = next((c["src"] for c in clips if c.get("src") and not is_image(c["src"])), None)
    ref = probe(first_video) if first_video else {}
    W = even(tl.get("width") or ref.get("width") or 1920)
    H = even(tl.get("height") or ref.get("height") or 1080)
    if tl.get("aspect") and not (tl.get("width") and tl.get("height")):
        ar = parse_aspect(tl["aspect"])
        if ar < 1:
            W, H = even(tl.get("width") or 1080), even((tl.get("width") or 1080) / ar)
        else:
            W, H = even(tl.get("width") or 1920), even((tl.get("width") or 1920) / ar)
    fps = float(tl.get("fps") or (ref.get("fps") if ref.get("fps", 0) > 0 else 30))
    fps = round(fps, 3)
    default_fit = tl.get("fit", "pad")
    default_tr = tl.get("transition")

    with TempDir() as tmp:
        segs, durs, trs = [], [], []
        for i, c in enumerate(clips):
            c.setdefault("fit", default_fit)
            log(f"[{i + 1}/{len(clips)}] preparando {c.get('src') or c.get('color')}")
            seg = tmp.file(".mp4")
            durs.append(render_segment(c, seg, W, H, fps, tmp))
            segs.append(seg)
            tr = c.get("transition", default_tr)
            if isinstance(tr, str):
                tr = {"type": tr, "duration": 0.5}
            trs.append(tr)
        joined = tmp.file(".mp4")
        log("uniendo clips…")
        total = assemble(segs, durs, trs, joined, fps)

        post = {k: tl.get(k) for k in ("color", "text", "subtitles", "fade_in", "fade_out",
                                       "loudnorm", "denoise", "volume")}
        post["subtitles"] = resolve(post["subtitles"])
        if tl.get("watermark"):
            post["watermark"] = dict(tl["watermark"], src=resolve(tl["watermark"]["src"]))
        if tl.get("music"):
            post["music"] = dict(tl["music"], src=resolve(tl["music"]["src"]))
        log("aplicando acabado final…")
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        post_process(joined, output, post, crf=tl.get("crf"))
    log(f"✔ {output} ({fmt_time(total)}, {W}x{H} @ {fps}fps)")
    return output


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------

def cmd_info(a):
    for path in a.inputs:
        info = probe(path)
        if a.json:
            print(json.dumps(info, indent=2, ensure_ascii=False))
            continue
        print(f"{path}")
        print(f"  duración : {fmt_time(info['duration'])} ({info['duration']:.2f}s)")
        if info["has_video"]:
            print(f"  video    : {info['width']}x{info['height']} @ {info['fps']}fps "
                  f"({info['vcodec']}, {info['pix_fmt']})")
        print(f"  audio    : " + (f"{info['acodec']} {info['sample_rate']}Hz {info['channels']}ch"
                                  if info["has_audio"] else "sin audio"))
        print(f"  tamaño   : {info['size_bytes'] / 1e6:.2f} MB, {info['bitrate'] / 1000:.0f} kb/s")


def cmd_trim(a):
    start = parse_time(a.start) or 0.0
    end = parse_time(a.end)
    dur = parse_time(a.duration)
    if dur is None and end is not None:
        dur = end - start
    args = ["-ss", f"{start:.3f}"] + (["-t", f"{dur:.3f}"] if dur else []) + ["-i", a.input]
    if a.copy:
        args += ["-c", "copy", "-avoid_negative_ts", "make_zero", a.output]
    else:
        args += out_codecs(a.output) + [a.output]
    ffmpeg(args)


def cmd_split(a):
    info = probe(a.input)
    if a.at:
        cuts = sorted(parse_time(t) for t in a.at.split(","))
    else:
        every = parse_time(a.every)
        cuts = [every * k for k in range(1, int(info["duration"] // every) + 1)]
    bounds = [0.0] + [c for c in cuts if 0 < c < info["duration"]] + [info["duration"]]
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem, ext = Path(a.input).stem, Path(a.input).suffix or ".mp4"
    for i, (s, e) in enumerate(zip(bounds, bounds[1:]), 1):
        if e - s < 0.05:
            continue
        out = str(out_dir / f"{stem}_{i:03d}{ext}")
        ffmpeg(["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", a.input] + out_codecs(out) + [out])
        print(out)


def cmd_concat(a):
    clips = [{"src": p, "fit": a.fit} for p in a.inputs]
    tl = {"clips": clips, "fps": a.fps, "width": a.width, "height": a.height}
    if a.transition and a.transition != "cut":
        tl["transition"] = {"type": a.transition, "duration": a.tdur}
    render_timeline(tl, a.output)


def cmd_reframe(a):
    info = probe(a.input)
    ar = parse_aspect(a.aspect)
    if a.width:
        W = even(a.width)
    elif ar < 1:
        W = even(min(info["height"], 1920) * ar) if info["height"] else 1080
    else:
        W = even(info["width"] or 1920)
    H = even(W / ar)
    graph = fit_graph("0:v", "v", W, H, a.mode)
    args = ["-i", a.input, "-filter_complex", graph, "-map", "[v]"]
    if info["has_audio"]:
        args += ["-map", "0:a"]
    ffmpeg(args + out_codecs(a.output, audio=info["has_audio"]) + [a.output])


def cmd_resize(a):
    info = probe(a.input)
    w = a.width or -2
    h = a.height or -2
    vf = f"scale={w}:{h}:flags=lanczos"
    if a.fps:
        vf += f",fps={a.fps}"
    ffmpeg(["-i", a.input, "-vf", vf] + out_codecs(a.output, audio=info["has_audio"]) + [a.output])


def cmd_crop(a):
    info = probe(a.input)
    x = a.x if a.x is not None else "(in_w-out_w)/2"
    y = a.y if a.y is not None else "(in_h-out_h)/2"
    ffmpeg(["-i", a.input, "-vf", f"crop={a.width}:{a.height}:{x}:{y}"]
           + out_codecs(a.output, audio=info["has_audio"]) + [a.output])


def cmd_speed(a):
    info = probe(a.input)
    f = float(a.factor)
    args = ["-i", a.input, "-vf", f"setpts=PTS/{f}"]
    if info["has_audio"] and not a.mute:
        args += ["-af", ",".join(atempo_chain(f))]
    ffmpeg(args + out_codecs(a.output, audio=info["has_audio"] and not a.mute) + [a.output])


def cmd_reverse(a):
    info = probe(a.input)
    args = ["-i", a.input, "-vf", "reverse"]
    if info["has_audio"]:
        args += ["-af", "areverse"]
    ffmpeg(args + out_codecs(a.output, audio=info["has_audio"]) + [a.output])


def cmd_rotate(a):
    info = probe(a.input)
    filters = {"90": "transpose=1", "-90": "transpose=2", "270": "transpose=2",
               "180": "hflip,vflip", "hflip": "hflip", "vflip": "vflip"}
    ffmpeg(["-i", a.input, "-vf", filters[a.how]]
           + out_codecs(a.output, audio=info["has_audio"]) + [a.output])


def cmd_loop(a):
    info = probe(a.input)
    ffmpeg(["-stream_loop", str(a.times - 1), "-i", a.input]
           + out_codecs(a.output, audio=info["has_audio"]) + [a.output])


def cmd_text(a):
    spec = {"text": a.text.replace("\\n", "\n"), "size": a.size, "color": a.color,
            "position": a.position, "start": a.start, "end": a.end, "fade": a.fade,
            "box": a.box, "font": a.font, "outline": a.outline}
    post_process(a.input, a.output, {"text": [spec]})


def cmd_color(a):
    spec = {"preset": a.preset, "brightness": a.brightness, "contrast": a.contrast,
            "saturation": a.saturation, "gamma": a.gamma, "temperature": a.temperature,
            "sharpen": a.sharpen, "denoise": a.denoise, "vignette": a.vignette, "lut": a.lut}
    post_process(a.input, a.output, {"color": spec})


def cmd_fade(a):
    post_process(a.input, a.output, {"fade_in": a.fade_in, "fade_out": a.fade_out})


def cmd_subtitles(a):
    post_process(a.input, a.output, {"subtitles": a.subs, "subtitle_style": a.style})


def cmd_watermark(a):
    post_process(a.input, a.output, {"watermark": {"src": a.image, "position": a.position,
                                                   "scale": a.scale, "opacity": a.opacity}})


def cmd_music(a):
    post_process(a.input, a.output, {"music": {
        "src": a.music, "volume": a.volume, "duck": not a.no_duck, "replace": a.replace,
        "start": a.music_start, "fade_out": a.fade_out}, "loudnorm": a.normalize})


def cmd_audio(a):
    info = probe(a.input)
    if a.mute:
        ffmpeg(["-i", a.input, "-c:v", "copy", "-an", a.output])
        return
    if not info["has_audio"]:
        raise VEditError("El video no tiene audio.")
    post_process(a.input, a.output, {"volume": a.volume, "denoise": a.denoise,
                                     "loudnorm": a.normalize})


def cmd_extract_audio(a):
    ext = Path(a.output).suffix.lower()
    codec = {".mp3": ["-c:a", "libmp3lame", "-q:a", "2"], ".wav": ["-c:a", "pcm_s16le"],
             ".m4a": ["-c:a", "aac", "-b:a", "192k"], ".opus": ["-c:a", "libopus"],
             ".flac": ["-c:a", "flac"]}.get(ext, [])
    ffmpeg(["-i", a.input, "-vn"] + codec + [a.output])


def detect_silences(path: str, noise_db: float, min_dur: float) -> list[tuple[float, float]]:
    log_text = ffmpeg(["-i", path, "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}",
                       "-vn", "-f", "null", "-"], capture_log=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log_text)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", log_text)]
    total = probe(path)["duration"]
    if len(ends) < len(starts):
        ends.append(total)
    return list(zip(starts, ends))


def detect_pauses(path: str, min_dur: float, margin_db: float = 4.0,
                  window: float = 0.1) -> list[tuple[float, float]]:
    """Detecta pausas comparando el volumen medio (RMS) con el ruido de fondo del propio video.

    Funciona aunque haya ruido constante (auto, viento, ventilador), donde silencedetect falla.
    """
    rate = 16000
    n = int(rate * window)
    log_text = ffmpeg(["-i", path, "-vn", "-af",
                       f"aresample={rate},pan=mono|c0=c0,highpass=f=150,lowpass=f=4000,"
                       f"asetnsamples=n={n}:p=0,astats=metadata=1:reset=1,"
                       "ametadata=print:key=lavfi.astats.Overall.RMS_level",
                       "-f", "null", "-"], capture_log=True)
    niveles = []
    for m in re.finditer(r"RMS_level=(-?[\d.]+|-inf)", log_text):
        v = m.group(1)
        niveles.append(-120.0 if v == "-inf" else float(v))
    if not niveles:
        return []
    ordenados = sorted(niveles)
    piso = ordenados[int(len(ordenados) * 0.1)]
    techo = ordenados[int(len(ordenados) * 0.9)]
    if techo - piso < 6:  # casi no hay diferencia entre voz y fondo: no cortar nada
        return []
    umbral = piso + max(margin_db, (techo - piso) * 0.25)
    pausas, inicio = [], None
    for i, v in enumerate(niveles + [0.0]):
        if v < umbral and inicio is None:
            inicio = i
        elif v >= umbral and inicio is not None:
            if (i - inicio) * window >= min_dur:
                pausas.append((inicio * window, i * window))
            inicio = None
    return pausas


def cmd_silence_cut(a):
    info = probe(a.input)
    if not info["has_audio"]:
        raise VEditError("El video no tiene audio; no hay silencios que detectar.")
    if a.noise is None:
        silences = detect_pauses(a.input, a.min_silence)
    else:
        silences = detect_silences(a.input, a.noise, a.min_silence)
    keep, cursor = [], 0.0
    for s, e in silences:
        s_cut, e_cut = s + a.padding, e - a.padding
        if e_cut - s_cut <= 0.05:
            continue
        if s_cut > cursor:
            keep.append((cursor, s_cut))
        cursor = e_cut
    if cursor < info["duration"]:
        keep.append((cursor, info["duration"]))
    keep = [(s, e) for s, e in keep if e - s > 0.05]
    removed = info["duration"] - sum(e - s for s, e in keep)
    log(f"{len(silences)} silencios detectados; se eliminan {removed:.1f}s "
        f"({removed / max(info['duration'], 1e-6) * 100:.0f}%).")
    if not keep:
        raise VEditError("Todo el audio parece silencio; ajusta --noise.")
    expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in keep)
    with TempDir() as tmp:
        script = tmp.write(f"[0:v]select='{expr}',setpts=N/FRAME_RATE/TB[v];"
                           f"[0:a]aselect='{expr}',asetpts=N/SR/TB[a]")
        ffmpeg(["-i", a.input, "-filter_complex_script", script, "-map", "[v]", "-map", "[a]"]
               + out_codecs(a.output) + [a.output])


def detect_scenes(path: str, threshold: float) -> list[float]:
    log_text = ffmpeg(["-i", path, "-vf", f"select='gt(scene,{threshold})',showinfo",
                       "-an", "-f", "null", "-"], capture_log=True)
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", log_text)]


def cmd_scenes(a):
    cuts = detect_scenes(a.input, a.threshold)
    info = probe(a.input)
    bounds = [0.0] + cuts + [info["duration"]]
    scenes = [{"scene": i, "start": round(s, 3), "end": round(e, 3), "duration": round(e - s, 3)}
              for i, (s, e) in enumerate(zip(bounds, bounds[1:]), 1)]
    if a.json:
        print(json.dumps(scenes, indent=2))
    else:
        for sc in scenes:
            print(f"escena {sc['scene']:3d}: {fmt_time(sc['start'])} → {fmt_time(sc['end'])} "
                  f"({sc['duration']:.2f}s)")
    if a.split:
        out_dir = Path(a.split)
        out_dir.mkdir(parents=True, exist_ok=True)
        for sc in scenes:
            out = str(out_dir / f"escena_{sc['scene']:03d}.mp4")
            ffmpeg(["-ss", str(sc["start"]), "-t", str(sc["duration"]), "-i", a.input]
                   + out_codecs(out, audio=info["has_audio"]) + [out])


def cmd_stabilize(a):
    info = probe(a.input)
    with TempDir() as tmp:
        trf = str(tmp.path / "transforms.trf")
        ffmpeg(["-i", a.input, "-vf", f"vidstabdetect=shakiness={a.shakiness}:accuracy=15:"
                f"result='{ffpath(trf)}'", "-f", "null", "-"])
        ffmpeg(["-i", a.input, "-vf", f"vidstabtransform=input='{ffpath(trf)}':smoothing={a.smoothing}:"
                "zoom=0:optzoom=1,unsharp=5:5:0.8:3:3:0.4"]
               + out_codecs(a.output, audio=info["has_audio"]) + [a.output])


def cmd_gif(a):
    start = parse_time(a.start) or 0.0
    dur = parse_time(a.duration)
    args = ["-ss", f"{start:.3f}"] + (["-t", f"{dur:.3f}"] if dur else []) + ["-i", a.input]
    vf = (f"fps={a.fps},scale={a.width}:-1:flags=lanczos,split[a][b];"
          f"[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4")
    ffmpeg(args + ["-filter_complex", vf, "-loop", "0", a.output])


def cmd_thumbnail(a):
    if a.time is not None:
        ffmpeg(["-ss", f"{parse_time(a.time):.3f}", "-i", a.input, "-frames:v", "1",
                "-q:v", "2", a.output])
    else:  # elige automáticamente un fotograma representativo
        ffmpeg(["-i", a.input, "-vf", "thumbnail=300", "-frames:v", "1", "-q:v", "2", a.output])


def cmd_sheet(a):
    """Hoja de contactos: cuadrícula de fotogramas con marca de tiempo."""
    info = probe(a.input)
    n = a.cols * a.rows
    rate = n / max(info["duration"], 0.01)
    with TempDir() as tmp:
        stamp = drawtext_filter({"text": "%{pts:hms}", "size": 22, "position": "bottom-left",
                                 "box": "black@0.6", "outline": 0}, tmp, expand=True)
        vf = (f"fps={rate:.6f},scale={a.thumb_width}:-2,{stamp},"
              f"tile={a.cols}x{a.rows}:padding=4:margin=4:color=0x111111")
        ffmpeg(["-i", a.input, "-vf", vf, "-frames:v", "1", "-q:v", "3", a.output])


def cmd_frames(a):
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = probe(a.input)
    rate = a.count / max(info["duration"], 0.01) if a.count else a.fps
    ffmpeg(["-i", a.input, "-vf", f"fps={rate}", "-q:v", "2", str(out_dir / "frame_%04d.jpg")])
    print(out_dir)


def cmd_pip(a):
    main = probe(a.input)
    w = even(main["width"] * a.scale)
    x, y = position_xy(a.position, "overlay", 0.03)
    start = parse_time(a.start) or 0.0
    graph = (f"[1:v]setpts=PTS-STARTPTS+{start}/TB,scale={w}:-2,"
             f"pad=iw+{a.border * 2}:ih+{a.border * 2}:{a.border}:{a.border}:color=white[pip];"
             f"[0:v][pip]overlay=x={x}:y={y}:eof_action=pass[v]")
    args = ["-i", a.input, "-i", a.overlay, "-filter_complex", graph, "-map", "[v]"]
    if main["has_audio"]:
        args += ["-map", "0:a"]
    ffmpeg(args + out_codecs(a.output, audio=main["has_audio"]) + [a.output])


def cmd_chromakey(a):
    fg = probe(a.input)
    W, H = fg["width"], fg["height"]
    bg_in = (["-loop", "1", "-i", a.background] if is_image(a.background)
             else ["-stream_loop", "-1", "-i", a.background])
    graph = (f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[bg];"
             f"[0:v]chromakey={a.color}:{a.similarity}:{a.blend},despill=type=green[fg];"
             f"[bg][fg]overlay=shortest=1,format=yuv420p[v]")
    args = ["-i", a.input] + bg_in + ["-filter_complex", graph, "-map", "[v]"]
    if fg["has_audio"]:
        args += ["-map", "0:a"]
    ffmpeg(args + ["-t", f"{fg['duration']:.3f}"]
           + out_codecs(a.output, audio=fg["has_audio"]) + [a.output])


def cmd_compress(a):
    info = probe(a.input)
    vf = [f"scale='min({a.max_width},iw)':-2"] if a.max_width else []
    vf_args = ["-vf", ",".join(vf)] if vf else []
    if a.target_mb:
        audio_kbps = 128 if info["has_audio"] else 0
        total_kbps = a.target_mb * 8192 / max(info["duration"], 0.1)
        v_kbps = int(total_kbps * 0.97 - audio_kbps)
        if v_kbps < 100:
            raise VEditError(f"{a.target_mb} MB es demasiado poco para {info['duration']:.0f}s de video.")
        with TempDir() as tmp:
            passlog = str(tmp.path / "pass")
            common = ["-i", a.input] + vf_args + ["-c:v", "libx264", "-preset", ENC["preset"],
                                                  "-b:v", f"{v_kbps}k", "-pix_fmt", "yuv420p",
                                                  "-passlogfile", passlog]
            ffmpeg(common + ["-pass", "1", "-an", "-f", "null", "-"])
            audio = ["-c:a", "aac", "-b:a", f"{audio_kbps}k"] if audio_kbps else ["-an"]
            ffmpeg(common + ["-pass", "2", "-movflags", "+faststart"] + audio + [a.output])
    else:
        ffmpeg(["-i", a.input] + vf_args + out_codecs(a.output, crf=a.crf, audio=info["has_audio"])
               + [a.output])
    before, after = info["size_bytes"], os.path.getsize(a.output)
    log(f"{before / 1e6:.2f} MB → {after / 1e6:.2f} MB ({after / max(before, 1) * 100:.0f}%)")


def cmd_slideshow(a):
    clips = [{"src": p, "duration": a.duration, "kenburns": not a.no_kenburns, "fit": a.fit}
             for p in a.images]
    tl = {"clips": clips, "fps": a.fps, "width": a.width, "height": a.height,
          "transition": {"type": a.transition, "duration": a.tdur} if a.transition != "cut" else None,
          "fade_in": 0.5, "fade_out": 1.0}
    if a.music:
        tl["music"] = {"src": a.music, "replace": True, "volume": 1.0}
    render_timeline(tl, a.output)


def cmd_render(a):
    path = Path(a.timeline)
    tl = json.loads(path.read_text(encoding="utf-8"))
    render_timeline(tl, a.output, base_dir=str(path.parent))


def cmd_presets(a):
    print("Presets de color:", ", ".join(sorted(COLOR_PRESETS)))
    print("Transiciones   :", ", ".join(TRANSITIONS))
    print("Posiciones     : center, top, bottom, left, right, top-left, top-right, "
          "bottom-left, bottom-right, lower-third, o 'x,y'")
    print("Encuadres      : pad, crop, blur, stretch")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vedit", description="Editor de video sobre FFmpeg.")
    p.add_argument("--version", action="version", version=f"vedit {VERSION}")
    p.add_argument("-v", "--verbose", action="store_true", help="muestra los comandos ffmpeg")
    p.add_argument("--crf", type=int, default=20, help="calidad x264 (menor = mejor). Def: 20")
    p.add_argument("--x264-preset", default="medium", help="velocidad x264 (ultrafast…veryslow)")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="comando")

    def add(name, func, help_, io=True):
        sp = sub.add_parser(name, help=help_, description=help_)
        if io:
            sp.add_argument("input")
            sp.add_argument("output")
        sp.set_defaults(func=func)
        return sp

    sp = add("info", cmd_info, "Muestra información de uno o más archivos", io=False)
    sp.add_argument("inputs", nargs="+")
    sp.add_argument("--json", action="store_true")

    sp = add("trim", cmd_trim, "Recorta un fragmento")
    sp.add_argument("--start", "-s")
    sp.add_argument("--end", "-e")
    sp.add_argument("--duration", "-d")
    sp.add_argument("--copy", action="store_true", help="sin recodificar (rápido, corta en keyframes)")

    sp = add("split", cmd_split, "Divide en partes", io=False)
    sp.add_argument("input")
    sp.add_argument("out_dir")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--every", help="duración de cada parte (p.ej. 60 o 1:00)")
    g.add_argument("--at", help="tiempos de corte separados por coma (p.ej. 0:10,0:45)")

    sp = add("concat", cmd_concat, "Une varios clips (normaliza tamaño/fps) con transiciones", io=False)
    sp.add_argument("inputs", nargs="+")
    sp.add_argument("-o", "--output", required=True)
    sp.add_argument("--transition", "-t", default="cut", help="cut o " + ", ".join(TRANSITIONS[:6]) + "…")
    sp.add_argument("--tdur", type=float, default=0.5, help="duración de la transición (s)")
    sp.add_argument("--fit", default="pad", choices=["pad", "crop", "blur", "stretch"])
    sp.add_argument("--width", type=int)
    sp.add_argument("--height", type=int)
    sp.add_argument("--fps", type=float)

    sp = add("reframe", cmd_reframe, "Cambia la relación de aspecto (9:16, 1:1, 16:9…)")
    sp.add_argument("--aspect", "-a", default="9:16")
    sp.add_argument("--mode", "-m", default="blur", choices=["blur", "crop", "pad", "stretch"])
    sp.add_argument("--width", type=int, help="ancho de salida (alto se calcula)")

    sp = add("resize", cmd_resize, "Escala el video")
    sp.add_argument("--width", type=int)
    sp.add_argument("--height", type=int)
    sp.add_argument("--fps", type=float)

    sp = add("crop", cmd_crop, "Recorta una región del cuadro")
    sp.add_argument("--width", required=True)
    sp.add_argument("--height", required=True)
    sp.add_argument("--x")
    sp.add_argument("--y")

    sp = add("speed", cmd_speed, "Cambia la velocidad (2 = doble, 0.5 = cámara lenta)")
    sp.add_argument("factor", type=float)
    sp.add_argument("--mute", action="store_true")

    add("reverse", cmd_reverse, "Reproduce al revés")

    sp = add("rotate", cmd_rotate, "Rota o voltea")
    sp.add_argument("how", choices=["90", "-90", "180", "270", "hflip", "vflip"])

    sp = add("loop", cmd_loop, "Repite el video N veces")
    sp.add_argument("times", type=int)

    sp = add("text", cmd_text, "Agrega un texto/título")
    sp.add_argument("text", help="usa \\n para saltos de línea")
    sp.add_argument("--size", type=int, default=64)
    sp.add_argument("--color", default="white")
    sp.add_argument("--position", "-p", default="center")
    sp.add_argument("--start")
    sp.add_argument("--end")
    sp.add_argument("--fade", type=float, default=0.0)
    sp.add_argument("--box", action="store_true", help="caja semitransparente detrás")
    sp.add_argument("--font")
    sp.add_argument("--outline", type=int, default=3)

    sp = add("color", cmd_color, "Corrección / gradación de color")
    sp.add_argument("--preset", choices=sorted(COLOR_PRESETS))
    sp.add_argument("--brightness", type=float, help="-1..1 (0 = igual)")
    sp.add_argument("--contrast", type=float, help="1 = igual")
    sp.add_argument("--saturation", type=float, help="1 = igual, 0 = B/N")
    sp.add_argument("--gamma", type=float)
    sp.add_argument("--temperature", type=float, help="-1 frío … 1 cálido")
    sp.add_argument("--sharpen", action="store_true")
    sp.add_argument("--denoise", action="store_true")
    sp.add_argument("--vignette", action="store_true")
    sp.add_argument("--lut", help="archivo .cube")

    sp = add("fade", cmd_fade, "Fundido de entrada/salida (video y audio)")
    sp.add_argument("--in", dest="fade_in", type=float, default=1.0)
    sp.add_argument("--out", dest="fade_out", type=float, default=1.0)

    sp = add("subtitles", cmd_subtitles, "Quema subtítulos .srt/.ass en el video")
    sp.add_argument("subs")
    sp.add_argument("--style", help="estilo ASS, p.ej. 'FontSize=24,PrimaryColour=&H00FFFF&'")

    sp = add("watermark", cmd_watermark, "Superpone un logo/imagen")
    sp.add_argument("image")
    sp.add_argument("--position", "-p", default="bottom-right")
    sp.add_argument("--scale", type=float, default=0.15, help="ancho relativo al video")
    sp.add_argument("--opacity", type=float, default=0.8)

    sp = add("music", cmd_music, "Agrega música de fondo (con ducking automático bajo la voz)")
    sp.add_argument("music")
    sp.add_argument("--volume", type=float)
    sp.add_argument("--replace", action="store_true", help="reemplaza el audio original")
    sp.add_argument("--no-duck", action="store_true", help="no bajar la música cuando hay voz")
    sp.add_argument("--music-start", help="desde qué punto de la canción empezar")
    sp.add_argument("--fade-out", type=float, default=2.0)
    sp.add_argument("--normalize", action="store_true", help="normaliza sonoridad (-14 LUFS)")

    sp = add("audio", cmd_audio, "Ajusta el audio: volumen, limpieza de ruido, normalización, mute")
    sp.add_argument("--volume", type=float)
    sp.add_argument("--denoise", action="store_true")
    sp.add_argument("--normalize", action="store_true")
    sp.add_argument("--mute", action="store_true")

    add("extract-audio", cmd_extract_audio, "Extrae el audio (mp3, wav, m4a, flac…)")

    sp = add("silence-cut", cmd_silence_cut, "Elimina automáticamente los silencios (jump cuts)")
    sp.add_argument("--noise", type=float, default=None,
                    help="umbral fijo en dB (por defecto se calcula solo según el ruido de fondo)")
    sp.add_argument("--min-silence", type=float, default=0.6, help="silencio mínimo a cortar (s)")
    sp.add_argument("--padding", type=float, default=0.12, help="margen que se deja (s)")

    sp = add("scenes", cmd_scenes, "Detecta cambios de escena", io=False)
    sp.add_argument("input")
    sp.add_argument("--threshold", type=float, default=0.35)
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--split", metavar="DIR", help="además exporta cada escena a DIR")

    sp = add("stabilize", cmd_stabilize, "Estabiliza video movido (2 pasadas vid.stab)")
    sp.add_argument("--shakiness", type=int, default=6)
    sp.add_argument("--smoothing", type=int, default=20)

    sp = add("gif", cmd_gif, "Convierte a GIF de alta calidad")
    sp.add_argument("--start")
    sp.add_argument("--duration")
    sp.add_argument("--fps", type=int, default=15)
    sp.add_argument("--width", type=int, default=480)

    sp = add("thumbnail", cmd_thumbnail, "Extrae una miniatura (auto o en un tiempo dado)")
    sp.add_argument("--time")

    sp = add("sheet", cmd_sheet, "Hoja de contactos (cuadrícula de fotogramas) para revisar")
    sp.add_argument("--cols", type=int, default=4)
    sp.add_argument("--rows", type=int, default=4)
    sp.add_argument("--thumb-width", type=int, default=360)

    sp = add("frames", cmd_frames, "Exporta fotogramas como JPG", io=False)
    sp.add_argument("input")
    sp.add_argument("out_dir")
    sp.add_argument("--count", type=int, help="número total de fotogramas repartidos")
    sp.add_argument("--fps", type=float, default=1.0)

    sp = add("pip", cmd_pip, "Picture-in-picture: un video sobre otro")
    sp.add_argument("overlay")
    sp.add_argument("--position", "-p", default="bottom-right")
    sp.add_argument("--scale", type=float, default=0.3)
    sp.add_argument("--start", help="cuándo aparece el PiP")
    sp.add_argument("--border", type=int, default=4)

    sp = add("chromakey", cmd_chromakey, "Pantalla verde: reemplaza el fondo")
    sp.add_argument("background", help="imagen o video de fondo")
    sp.add_argument("--color", default="0x00FF00")
    sp.add_argument("--similarity", type=float, default=0.15)
    sp.add_argument("--blend", type=float, default=0.08)

    sp = add("compress", cmd_compress, "Reduce el tamaño (por CRF o tamaño objetivo)")
    sp.add_argument("--target-mb", type=float, help="tamaño objetivo en MB (2 pasadas)")
    sp.add_argument("--max-width", type=int)

    sp = add("slideshow", cmd_slideshow, "Crea un video a partir de imágenes (Ken Burns)", io=False)
    sp.add_argument("images", nargs="+")
    sp.add_argument("-o", "--output", required=True)
    sp.add_argument("--duration", type=float, default=4.0)
    sp.add_argument("--transition", default="fade")
    sp.add_argument("--tdur", type=float, default=0.8)
    sp.add_argument("--music")
    sp.add_argument("--no-kenburns", action="store_true")
    sp.add_argument("--fit", default="crop", choices=["pad", "crop", "blur", "stretch"])
    sp.add_argument("--width", type=int, default=1920)
    sp.add_argument("--height", type=int, default=1080)
    sp.add_argument("--fps", type=float, default=30)

    sp = add("render", cmd_render, "Renderiza un proyecto JSON (línea de tiempo completa)", io=False)
    sp.add_argument("timeline")
    sp.add_argument("-o", "--output", help="sobrescribe 'output' del JSON")

    add("presets", cmd_presets, "Lista presets, transiciones y posiciones", io=False)
    return p


def main(argv=None) -> int:
    global VERBOSE
    args = build_parser().parse_args(argv)
    VERBOSE = args.verbose
    ENC["crf"], ENC["preset"] = args.crf, args.x264_preset
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        log("Error: se necesitan ffmpeg y ffprobe en el PATH.")
        return 2
    try:
        args.func(args)
    except VEditError as e:
        log(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
