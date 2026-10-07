# Formato de proyecto (línea de tiempo JSON)

`python3 vedit.py render proyecto.json [-o salida.mp4]`

Las rutas relativas se resuelven desde la carpeta del JSON. Los tiempos aceptan
segundos (`12.5`) o `mm:ss` / `hh:mm:ss.ms`.

```jsonc
{
  "output": "out/final.mp4",
  "width": 1080, "height": 1920,      // o "aspect": "9:16"; por defecto, el 1er video
  "fps": 30,
  "fit": "blur",                      // pad | crop | blur | stretch (por defecto para clips)
  "transition": {"type": "fade", "duration": 0.5},  // por defecto entre clips (opcional)
  "crf": 18,                          // calidad final (opcional)

  "clips": [
    // Tarjeta de color con título
    {"color": "black", "duration": 2,
     "text": [{"text": "MI VIAJE", "size": 110, "fade": 0.4, "start": 0, "end": 2}],
     "transition": {"type": "fadeblack", "duration": 0.5}},

    // Fragmento de video
    {"src": "media/playa.mp4", "start": "0:12", "end": "0:18",
     "speed": 1.0,                    // 2 = doble, 0.5 = cámara lenta
     "volume": 0.8, "mute": false, "reverse": false,
     "fit": "crop",                   // sobrescribe el global
     "color_grade": "warm",           // preset o {"preset":..,"contrast":..,"saturation":..}
     "text": [{"text": "Día 1", "position": "lower-third", "start": 0.5, "end": 3}],
     "fade_in": 0, "fade_out": 0,
     "transition": "slideleft"},      // transición hacia el SIGUIENTE clip

    // Imagen fija (con zoom lento opcional)
    {"src": "media/foto.jpg", "duration": 3, "kenburns": true, "zoom": 1.2}
  ],

  // Acabado global (tiempos absolutos sobre el video final)
  "text": [{"text": "@basetoque", "position": "top-right", "size": 36}],
  "color": {"preset": "cinematic"},
  "subtitles": "subs.srt",
  "watermark": {"src": "logo.png", "position": "bottom-right", "scale": 0.12, "opacity": 0.8},
  "music": {"src": "media/tema.mp3", "volume": 0.25, "duck": true, "replace": false,
            "start": "0:30", "fade_out": 2},
  "fade_in": 0.5, "fade_out": 1.0,
  "denoise": false, "volume": 1.0,
  "loudnorm": true
}
```

## Opciones de texto

| clave | por defecto | descripción |
|---|---|---|
| `text` | — | texto (usa `\n` para varias líneas) |
| `size` | 64 | tamaño en px |
| `color` | white | nombre, `#RRGGBB` o `color@alpha` |
| `position` | center | center, top, bottom, left, right, top-left, top-right, bottom-left, bottom-right, lower-third, o `"x,y"` |
| `start` / `end` | todo | intervalo visible |
| `fade` | 0 | fundido de entrada/salida (s) |
| `box` | false | `true` o un color (`"black@0.5"`) para caja de fondo |
| `outline` | 3 | grosor del contorno |
| `shadow` | false | sombra |
| `font` | DejaVu Sans Bold | ruta a .ttf/.otf o nombre de fuente |

## Transiciones

`cut`, `fade`, `fadeblack`, `fadewhite`, `dissolve`, `wipeleft`, `wiperight`, `wipeup`,
`wipedown`, `slideleft`, `slideright`, `slideup`, `slidedown`, `circleopen`,
`circleclose`, `radial`, `smoothleft`, `smoothright`, `pixelize`, `zoomin`, `distance`,
`hblur`. Una transición de duración `T` solapa los clips, así que el total se reduce en `T`.

## Presets de color

`cinematic`, `bw`, `vintage`, `warm`, `cool`, `vivid`, `dramatic`, `fade`. Además:
`brightness` (-1..1), `contrast`, `saturation`, `gamma`, `temperature` (-1..1),
`sharpen`, `denoise`, `vignette`, `lut` (archivo `.cube`).
