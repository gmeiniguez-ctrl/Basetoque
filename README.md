# Basetoque

Editor de video por línea de comandos sobre **FFmpeg** — y un espacio de trabajo donde
Claude actúa como tu editor (ver [`CLAUDE.md`](CLAUDE.md)).

**Requisitos:** Python 3.9+ y `ffmpeg`/`ffprobe` en el PATH. Nada más.

## Cómo trabajar con Claude

1. Sube tus clips, fotos y música a `media/` (ignorado por git).
2. Pide lo que quieras en lenguaje natural, p.ej.:
   *"Haz un reel vertical de 30 s con lo mejor de estos clips, música de fondo, títulos
   y color cálido"* o *"Quita los silencios de esta entrevista y añade subtítulos"*.
3. Claude inspecciona el material (y mira los fotogramas), arma el proyecto, renderiza en
   `out/`, revisa el resultado y te lo entrega.

## Comandos

```bash
python3 vedit.py info clip.mp4                          # duración, resolución, audio…
python3 vedit.py trim in.mp4 out.mp4 -s 0:05 -e 0:20    # recortar (--copy = sin recodificar)
python3 vedit.py split in.mp4 partes/ --every 60        # dividir (o --at 0:10,0:45)
python3 vedit.py concat a.mp4 b.mp4 c.mp4 -o out.mp4 --transition fade --fit blur
python3 vedit.py reframe in.mp4 out.mp4 --aspect 9:16 --mode blur   # 16:9 → vertical
python3 vedit.py resize in.mp4 out.mp4 --width 1280
python3 vedit.py crop in.mp4 out.mp4 --width 720 --height 720
python3 vedit.py speed in.mp4 out.mp4 0.5               # cámara lenta (audio incluido)
python3 vedit.py reverse in.mp4 out.mp4
python3 vedit.py rotate in.mp4 out.mp4 90               # 90, -90, 180, hflip, vflip
python3 vedit.py loop in.mp4 out.mp4 3
python3 vedit.py text in.mp4 out.mp4 "Hola\nmundo" -p lower-third --start 1 --end 4 --fade 0.3 --box
python3 vedit.py color in.mp4 out.mp4 --preset cinematic --saturation 1.1 --sharpen
python3 vedit.py fade in.mp4 out.mp4 --in 1 --out 2
python3 vedit.py subtitles in.mp4 out.mp4 subs.srt
python3 vedit.py watermark in.mp4 out.mp4 logo.png -p top-right --opacity 0.7
python3 vedit.py music in.mp4 out.mp4 tema.mp3 --volume 0.25 --normalize   # con ducking
python3 vedit.py audio in.mp4 out.mp4 --denoise --normalize                # limpia la voz
python3 vedit.py extract-audio in.mp4 audio.mp3
python3 vedit.py silence-cut entrevista.mp4 out.mp4     # jump cuts automáticos
python3 vedit.py scenes in.mp4 --split escenas/         # detectar/exportar escenas
python3 vedit.py stabilize movido.mp4 estable.mp4
python3 vedit.py pip principal.mp4 out.mp4 camara.mp4 -p bottom-right --scale 0.3
python3 vedit.py chromakey verde.mp4 out.mp4 fondo.jpg
python3 vedit.py slideshow fotos/*.jpg -o album.mp4 --music tema.mp3
python3 vedit.py gif in.mp4 out.gif --start 2 --duration 3 --width 480
python3 vedit.py thumbnail in.mp4 portada.jpg           # automática, o --time 0:12
python3 vedit.py sheet in.mp4 hoja.jpg                  # hoja de contactos para revisar
python3 vedit.py frames in.mp4 fotogramas/ --count 10
python3 vedit.py compress in.mp4 out.mp4 --target-mb 25 # o --crf 28 --max-width 1280
python3 vedit.py render examples/reel.json              # proyecto completo (JSON)
python3 vedit.py presets                                # presets, transiciones, posiciones
```

Opciones globales (antes del comando): `-v` muestra los comandos ffmpeg, `--crf 18`
para más calidad, `--x264-preset slow` para mejor compresión.

## Proyectos JSON

Para ediciones completas (varios clips, títulos, transiciones, color, música,
subtítulos, marca de agua) se describe una línea de tiempo en JSON y se renderiza con
`render`. Formato completo en [`docs/timeline.md`](docs/timeline.md); ejemplo en
[`examples/reel.json`](examples/reel.json).

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```
