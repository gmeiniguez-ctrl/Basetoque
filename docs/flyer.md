# Formato de diseño de flyer (JSON)

Basetoque Studio guarda cada flyer como `proyectos/flyers/<nombre>.json` y la imagen
final como `out/<nombre>.png`. Un JSON puesto en `proyectos/flyers/` aparece en
**Flyers → Abrir**, listo para editar y exportar.

```jsonc
{
  "ancho": 1080, "alto": 1350,            // post 1080x1350 · cuadrado 1080x1080 · historia 1080x1920
  "fondo": {
    "tipo": "color" | "degradado" | "imagen",
    "color": "#ff2e63", "color2": "#5b0fd6", "angulo": 135,   // degradado
    "imagen": "media/foto.jpg", "oscurecer": 0.35              // foto (0 = nada, 0.85 = muy oscuro)
  },
  "elementos": [                             // se dibujan en orden: el último queda arriba
    {"tipo": "texto", "texto": "GRAN\nFIESTA", "x": 60, "y": 250, "ancho": 960,
     "tamano": 230, "fuente": "Impact", "color": "#ffffff", "negrita": false, "cursiva": false,
     "alineacion": "left|center|right", "sombra": true, "contorno": 0, "colorContorno": "#000000",
     "caja": "#000000", "interlineado": 1.1, "espaciado": 0, "opacidad": 1},
    {"tipo": "forma", "forma": "rect|circulo", "x": 270, "y": 960, "ancho": 540, "alto": 120,
     "color": "#ffe066", "radio": 60, "borde": 0, "colorBorde": "#000000", "opacidad": 1},
    {"tipo": "imagen", "src": "media/logo.png", "x": 40, "y": 40, "ancho": 200, "alto": 200,
     "redondeo": 0, "opacidad": 1}
  ]
}
```

- Coordenadas en píxeles desde la esquina superior izquierda; `x, y` es la esquina
  superior izquierda de la caja del elemento.
- Los textos se ajustan solos al `ancho` (salto de línea automático); `\n` fuerza un salto.
- Fuentes seguras en Windows y Mac: Impact, Arial, Arial Black, Georgia, Verdana,
  Trebuchet MS, Tahoma, Courier New, Times New Roman.
- Desde un flyer guardado, **Animar para historias** crea un video con zoom lento y música.
