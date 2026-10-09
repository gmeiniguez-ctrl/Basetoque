/* Basetoque Studio — editor de flyers sobre <canvas>. Funciona 100% sin internet. */
"use strict";

const TAMANOS = [
  ["1080x1350", "📱 Post Instagram (4:5)"],
  ["1080x1080", "⬛ Cuadrado (1:1)"],
  ["1080x1920", "📲 Historia / Reel (9:16)"],
  ["1200x630", "🖥️ Facebook / Evento"],
  ["1920x1080", "📺 Horizontal / Pantalla"],
  ["1240x1754", "🖨️ Hoja A4 (impresión)"],
];
const FUENTES = ["Impact", "Arial", "Arial Black", "Helvetica", "Georgia", "Times New Roman", "Verdana",
  "Trebuchet MS", "Tahoma", "Courier New", "Brush Script MT", "Comic Sans MS", "Segoe UI", "system-ui"];

/* Plantillas en un lienzo base de 1080×1350; se adaptan al tamaño elegido. */
const PLANTILLAS = [
  { nombre: "Fiesta", d: { fondo: { tipo: "degradado", color: "#ff2e63", color2: "#5b0fd6", angulo: 135 }, elementos: [
    { tipo: "forma", forma: "circulo", x: 640, y: -160, ancho: 620, alto: 620, color: "#ffffff", opacidad: 0.08 },
    { tipo: "texto", texto: "SÁBADO 12 DE OCTUBRE", x: 80, y: 150, ancho: 920, tamano: 46, fuente: "Arial", negrita: true, color: "#ffe066", alineacion: "center" },
    { tipo: "texto", texto: "GRAN\nFIESTA", x: 60, y: 250, ancho: 960, tamano: 230, fuente: "Impact", color: "#ffffff", alineacion: "center", sombra: true, interlineado: 0.95 },
    { tipo: "texto", texto: "Música en vivo · DJ invitado · Barra libre hasta la 1", x: 120, y: 760, ancho: 840, tamano: 42, fuente: "Arial", color: "#ffffff", alineacion: "center" },
    { tipo: "forma", forma: "rect", x: 270, y: 960, ancho: 540, alto: 120, color: "#ffe066", radio: 60 },
    { tipo: "texto", texto: "ENTRADA $5000", x: 270, y: 990, ancho: 540, tamano: 54, fuente: "Arial Black", color: "#2b0a57", alineacion: "center" },
    { tipo: "texto", texto: "Club Luna · Av. Siempre Viva 742 · 22 h", x: 80, y: 1180, ancho: 920, tamano: 36, fuente: "Arial", color: "#ffffff", alineacion: "center" },
  ] } },
  { nombre: "Oferta", d: { fondo: { tipo: "color", color: "#ffd400" }, elementos: [
    { tipo: "forma", forma: "circulo", x: 190, y: 250, ancho: 700, alto: 700, color: "#e3262f" },
    { tipo: "texto", texto: "SÓLO ESTE FIN DE SEMANA", x: 80, y: 110, ancho: 920, tamano: 50, fuente: "Arial Black", color: "#1a1a1a", alineacion: "center" },
    { tipo: "texto", texto: "50%", x: 190, y: 380, ancho: 700, tamano: 290, fuente: "Impact", color: "#ffffff", alineacion: "center" },
    { tipo: "texto", texto: "DE DESCUENTO", x: 190, y: 700, ancho: 700, tamano: 64, fuente: "Arial Black", color: "#ffffff", alineacion: "center" },
    { tipo: "texto", texto: "En toda la tienda", x: 80, y: 1030, ancho: 920, tamano: 54, fuente: "Arial", negrita: true, color: "#1a1a1a", alineacion: "center" },
    { tipo: "texto", texto: "@tutienda", x: 80, y: 1200, ancho: 920, tamano: 40, fuente: "Arial", color: "#1a1a1a", alineacion: "center" },
  ] } },
  { nombre: "Elegante", d: { fondo: { tipo: "color", color: "#f3ede3" }, elementos: [
    { tipo: "forma", forma: "rect", x: 50, y: 50, ancho: 980, alto: 1250, color: "#00000000", radio: 0, borde: 3, colorBorde: "#a8865b" },
    { tipo: "texto", texto: "TALLER", x: 100, y: 230, ancho: 880, tamano: 44, fuente: "Georgia", color: "#a8865b", alineacion: "center", espaciado: 12 },
    { tipo: "texto", texto: "Cerámica\nde autor", x: 100, y: 320, ancho: 880, tamano: 150, fuente: "Georgia", cursiva: true, color: "#2e2a25", alineacion: "center", interlineado: 1.05 },
    { tipo: "forma", forma: "rect", x: 490, y: 700, ancho: 100, alto: 4, color: "#a8865b" },
    { tipo: "texto", texto: "Sábados de octubre · 10 a 13 h\nCupos limitados", x: 100, y: 760, ancho: 880, tamano: 44, fuente: "Georgia", color: "#2e2a25", alineacion: "center", interlineado: 1.4 },
    { tipo: "texto", texto: "Inscripciones: 11 5555-5555", x: 100, y: 1110, ancho: 880, tamano: 38, fuente: "Georgia", color: "#a8865b", alineacion: "center" },
  ] } },
  { nombre: "Con foto", d: { fondo: { tipo: "imagen", imagen: "", oscurecer: 0.45, color: "#1d2b3a", color2: "#0b0f14", angulo: 160 }, elementos: [
    { tipo: "forma", forma: "rect", x: 80, y: 820, ancho: 160, alto: 12, color: "#ffcc00" },
    { tipo: "texto", texto: "NUEVA\nTEMPORADA", x: 80, y: 860, ancho: 920, tamano: 130, fuente: "Impact", color: "#ffffff", alineacion: "left", sombra: true, interlineado: 0.95 },
    { tipo: "texto", texto: "Ya disponible en todas nuestras sucursales", x: 80, y: 1140, ancho: 920, tamano: 42, fuente: "Arial", color: "#ffffff", alineacion: "left" },
  ] } },
  { nombre: "Comunicado", d: { fondo: { tipo: "color", color: "#121417" }, elementos: [
    { tipo: "forma", forma: "rect", x: 0, y: 0, ancho: 1080, alto: 26, color: "#00c2a8" },
    { tipo: "texto", texto: "IMPORTANTE", x: 90, y: 160, ancho: 900, tamano: 54, fuente: "Arial Black", color: "#00c2a8", alineacion: "left", espaciado: 6 },
    { tipo: "texto", texto: "Cambiamos de horario", x: 90, y: 260, ancho: 900, tamano: 120, fuente: "Arial Black", color: "#ffffff", alineacion: "left", interlineado: 1.0 },
    { tipo: "texto", texto: "A partir del lunes atendemos de 9 a 18 h, de lunes a sábado. ¡Gracias por elegirnos!", x: 90, y: 620, ancho: 880, tamano: 50, fuente: "Arial", color: "#c9d1d9", alineacion: "left", interlineado: 1.35 },
    { tipo: "texto", texto: "tunegocio.com", x: 90, y: 1190, ancho: 900, tamano: 40, fuente: "Arial", negrita: true, color: "#00c2a8", alineacion: "left" },
  ] } },
  { nombre: "En blanco", d: { fondo: { tipo: "color", color: "#ffffff" }, elementos: [] } },
];

const Flyer = {
  diseno: null,
  sel: -1,
  cajas: [],
  imgs: {},
  historial: [],
  arrastre: null,

  // ---------- utilidades ----------
  copia(o) { return JSON.parse(JSON.stringify(o)); },

  imagen(src) {
    if (!src) return null;
    if (!Flyer.imgs[src]) {
      const img = new Image();
      img.onload = () => Flyer.dibujar();
      img.src = "/" + src;
      Flyer.imgs[src] = img;
    }
    const img = Flyer.imgs[src];
    return img.complete && img.naturalWidth ? img : null;
  },

  esperarImagenes() {
    const srcs = [Flyer.diseno.fondo.tipo === "imagen" ? Flyer.diseno.fondo.imagen : null,
      ...Flyer.diseno.elementos.filter((e) => e.tipo === "imagen").map((e) => e.src)].filter(Boolean);
    return Promise.all(srcs.map((s) => new Promise((ok) => {
      Flyer.imagen(s);
      const img = Flyer.imgs[s];
      if (img.complete) ok(); else { img.addEventListener("load", ok); img.addEventListener("error", ok); }
    })));
  },

  adaptar(base, W, H) {
    const d = Flyer.copia(base);
    const sx = W / 1080, sy = H / 1350, s = Math.min(sx, sy);
    d.ancho = W; d.alto = H;
    for (const e of d.elementos) {
      e.x = Math.round(e.x * sx); e.y = Math.round(e.y * sy);
      if (e.tipo === "texto") { e.ancho = Math.round(e.ancho * sx); e.tamano = Math.round(e.tamano * s); }
      else if (e.forma === "circulo") {
        const lado = Math.round(e.ancho * s);
        e.x += Math.round((e.ancho * sx - lado) / 2); e.y += Math.round((e.alto * sy - lado) / 2);
        e.ancho = e.alto = lado;
      } else { e.ancho = Math.round(e.ancho * sx); e.alto = Math.max(1, Math.round(e.alto * sy)); }
    }
    return d;
  },

  mejorFoto() {
    const fotos = App.delTipo("imagen").filter((f) => !/logo/i.test(f.nombre) && f.ruta.startsWith("media/"));
    fotos.sort((a, b) => (b.ancho || 0) * (b.alto || 0) - (a.ancho || 0) * (a.alto || 0));
    return (fotos[0] || App.delTipo("imagen")[0])?.ruta || "";
  },

  // ---------- dibujo ----------
  fuente(e) {
    return `${e.cursiva ? "italic " : ""}${e.negrita ? "bold " : ""}${e.tamano}px "${e.fuente || "Arial"}", sans-serif`;
  },

  lineasTexto(ctx, e) {
    ctx.font = Flyer.fuente(e);
    if ("letterSpacing" in ctx) ctx.letterSpacing = (e.espaciado || 0) + "px";
    const lineas = [];
    for (const parrafo of String(e.texto ?? "").split("\n")) {
      let actual = "";
      for (const palabra of parrafo.split(" ")) {
        const prueba = actual ? actual + " " + palabra : palabra;
        if (actual && ctx.measureText(prueba).width > e.ancho) { lineas.push(actual); actual = palabra; }
        else actual = prueba;
      }
      lineas.push(actual);
    }
    return lineas;
  },

  rutaRedondeada(ctx, x, y, w, h, r) {
    r = Math.max(0, Math.min(r || 0, w / 2, h / 2));
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  },

  dibujarEn(ctx, d, conSeleccion) {
    const W = d.ancho, H = d.alto, f = d.fondo || {};
    const cajas = [];
    ctx.save();
    ctx.clearRect(0, 0, W, H);
    // Fondo
    if (f.tipo === "degradado" || (f.tipo === "imagen" && !Flyer.imagen(f.imagen))) {
      const a = ((f.angulo ?? 135) - 90) * Math.PI / 180;
      const r = Math.hypot(W, H) / 2, cx = W / 2, cy = H / 2;
      const g = ctx.createLinearGradient(cx - Math.cos(a) * r, cy - Math.sin(a) * r, cx + Math.cos(a) * r, cy + Math.sin(a) * r);
      g.addColorStop(0, f.color || "#333"); g.addColorStop(1, f.color2 || f.color || "#000");
      ctx.fillStyle = g;
    } else ctx.fillStyle = f.color || "#ffffff";
    ctx.fillRect(0, 0, W, H);
    if (f.tipo === "imagen") {
      const img = Flyer.imagen(f.imagen);
      if (img) {
        const esc = Math.max(W / img.naturalWidth, H / img.naturalHeight);
        const iw = img.naturalWidth * esc, ih = img.naturalHeight * esc;
        ctx.drawImage(img, (W - iw) / 2, (H - ih) / 2, iw, ih);
      }
      if (f.oscurecer) { ctx.fillStyle = `rgba(0,0,0,${f.oscurecer})`; ctx.fillRect(0, 0, W, H); }
    }
    // Elementos
    for (const e of d.elementos) {
      ctx.save();
      ctx.globalAlpha = e.opacidad ?? 1;
      let caja;
      if (e.tipo === "texto") {
        const lineas = Flyer.lineasTexto(ctx, e);
        const lh = e.tamano * (e.interlineado || 1.15);
        const alto = Math.max(lh, lineas.length * lh);
        caja = { x: e.x, y: e.y, w: e.ancho, h: alto };
        if (e.caja) {
          const p = e.tamano * 0.3;
          ctx.fillStyle = e.caja;
          Flyer.rutaRedondeada(ctx, e.x - p, e.y - p, e.ancho + 2 * p, alto + 2 * p, p);
          ctx.fill();
        }
        ctx.textBaseline = "top";
        ctx.textAlign = e.alineacion || "left";
        const tx = e.alineacion === "center" ? e.x + e.ancho / 2 : e.alineacion === "right" ? e.x + e.ancho : e.x;
        if (e.sombra) {
          ctx.shadowColor = "rgba(0,0,0,.45)"; ctx.shadowBlur = e.tamano * 0.12; ctx.shadowOffsetY = e.tamano * 0.04;
        }
        lineas.forEach((l, i) => {
          const ty = e.y + i * lh + (lh - e.tamano) / 2;
          if (e.contorno) {
            ctx.lineWidth = e.contorno * 2; ctx.strokeStyle = e.colorContorno || "#000"; ctx.lineJoin = "round";
            ctx.strokeText(l, tx, ty);
          }
          ctx.fillStyle = e.color || "#000";
          ctx.fillText(l, tx, ty);
        });
      } else if (e.tipo === "forma") {
        caja = { x: e.x, y: e.y, w: e.ancho, h: e.alto };
        ctx.fillStyle = e.color || "#000";
        if (e.forma === "circulo") { ctx.beginPath(); ctx.ellipse(e.x + e.ancho / 2, e.y + e.alto / 2, e.ancho / 2, e.alto / 2, 0, 0, Math.PI * 2); }
        else Flyer.rutaRedondeada(ctx, e.x, e.y, e.ancho, e.alto, e.radio);
        ctx.fill();
        if (e.borde) { ctx.lineWidth = e.borde; ctx.strokeStyle = e.colorBorde || "#000"; ctx.stroke(); }
      } else if (e.tipo === "imagen") {
        caja = { x: e.x, y: e.y, w: e.ancho, h: e.alto };
        const img = Flyer.imagen(e.src);
        if (img) {
          if (e.redondeo) { Flyer.rutaRedondeada(ctx, e.x, e.y, e.ancho, e.alto, e.redondeo); ctx.clip(); }
          ctx.drawImage(img, e.x, e.y, e.ancho, e.alto);
        } else { ctx.fillStyle = "rgba(128,128,128,.3)"; ctx.fillRect(e.x, e.y, e.ancho, e.alto); }
      }
      ctx.restore();
      cajas.push(caja);
    }
    // Selección
    if (conSeleccion && cajas[Flyer.sel]) {
      const c = cajas[Flyer.sel], u = W / (Flyer.lienzo.getBoundingClientRect().width || W);
      ctx.save();
      ctx.lineWidth = 2 * u; ctx.setLineDash([8 * u, 6 * u]); ctx.strokeStyle = "#e2552b";
      ctx.strokeRect(c.x, c.y, c.w, c.h);
      ctx.setLineDash([]); ctx.fillStyle = "#fff";
      const t = 14 * u;
      ctx.fillRect(c.x + c.w - t / 2, c.y + c.h - t / 2, t, t);
      ctx.strokeRect(c.x + c.w - t / 2, c.y + c.h - t / 2, t, t);
      ctx.restore();
    }
    ctx.restore();
    return cajas;
  },

  dibujar() {
    if (!Flyer.diseno) return;
    Flyer.cajas = Flyer.dibujarEn(Flyer.ctx, Flyer.diseno, true);
  },

  // ---------- estado ----------
  guardarPaso() {
    Flyer.historial.push(JSON.stringify(Flyer.diseno));
    if (Flyer.historial.length > 60) Flyer.historial.shift();
  },
  deshacer() {
    const prev = Flyer.historial.pop();
    if (!prev) return;
    Flyer.diseno = JSON.parse(prev);
    Flyer.sel = -1;
    Flyer.refrescarTodo();
  },

  cargar(d, nombre) {
    d = Flyer.copia(d);
    d.ancho = d.ancho || 1080; d.alto = d.alto || 1350;
    d.fondo = d.fondo || { tipo: "color", color: "#ffffff" };
    d.elementos = d.elementos || [];
    Flyer.guardarPaso();
    Flyer.diseno = d;
    Flyer.sel = -1;
    if (nombre) $("#fl-nombre").value = nombre;
    $("#fl-despues").classList.add("oculto");
    Flyer.refrescarTodo();
  },

  refrescarTodo() {
    const d = Flyer.diseno;
    Flyer.lienzo.width = d.ancho; Flyer.lienzo.height = d.alto;
    const clave = `${d.ancho}x${d.alto}`;
    if (!TAMANOS.some(([k]) => k === clave)) $("#fl-tamano").insertAdjacentHTML("beforeend", `<option value="${clave}">${clave}</option>`);
    $("#fl-tamano").value = clave;
    Flyer.pintarFondo();
    Flyer.pintarProps();
    Flyer.dibujar();
  },

  agregar(e) {
    Flyer.guardarPaso();
    Flyer.diseno.elementos.push(e);
    Flyer.sel = Flyer.diseno.elementos.length - 1;
    Flyer.pintarProps(); Flyer.dibujar();
  },

  agregarTexto(titulo) {
    const d = Flyer.diseno, s = Math.min(d.ancho / 1080, d.alto / 1350);
    const tam = Math.round((titulo ? 120 : 52) * s);
    Flyer.agregar({ tipo: "texto", texto: titulo ? "TÍTULO" : "Escribe tu texto aquí", x: Math.round(d.ancho * 0.08),
      y: Math.round(d.alto * 0.4), ancho: Math.round(d.ancho * 0.84), tamano: tam, fuente: titulo ? "Impact" : "Arial",
      color: Flyer.contraste(), alineacion: "center", negrita: !titulo, sombra: titulo });
  },

  contraste() {
    const f = Flyer.diseno.fondo;
    if (f.tipo === "imagen") return "#ffffff";
    const hex = (f.color || "#ffffff").replace("#", "").slice(0, 6);
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) || 0);
    return (r * 299 + g * 587 + b * 114) / 1000 > 140 ? "#111111" : "#ffffff";
  },

  agregarForma(forma) {
    const d = Flyer.diseno, lado = Math.round(Math.min(d.ancho, d.alto) * 0.3);
    Flyer.agregar({ tipo: "forma", forma, x: Math.round((d.ancho - lado) / 2), y: Math.round((d.alto - lado) / 2),
      ancho: lado, alto: forma === "rect" ? Math.round(lado / 2.5) : lado, color: "#e2552b", radio: forma === "rect" ? 16 : 0, opacidad: 1 });
  },

  agregarImagen(ruta) {
    const f = App.info[ruta], d = Flyer.diseno;
    const w = Math.round(d.ancho * 0.4);
    const h = Math.round(w * ((f?.alto || 1) / (f?.ancho || 1)));
    Flyer.agregar({ tipo: "imagen", src: ruta, x: Math.round((d.ancho - w) / 2), y: Math.round((d.alto - h) / 2), ancho: w, alto: h, redondeo: 0 });
  },

  // ---------- paneles ----------
  pintarImagenes() {
    const imgs = App.delTipo("imagen");
    $("#fl-imagenes").innerHTML = imgs.map((f) =>
      `<div class="item" data-fl-img="${esc(f.ruta)}" title="${esc(f.ruta)}"><div class="mini" style="background-image:url('${App.miniUrl(f)}')"></div><div>${esc(f.nombre)}</div></div>`
    ).join("") || `<p class="sutil">Sube fotos o logos en “Mis archivos”.</p>`;
    App.opcionesArchivos($("#fl-musica"), ["audio"], "Sin música");
    if (Flyer.diseno) Flyer.pintarFondo();
  },

  pintarFondo() {
    const f = Flyer.diseno.fondo;
    const imgs = App.delTipo("imagen");
    $("#fl-fondo").innerHTML = `
      <label>Tipo<select data-f="tipo">
        <option value="color" ${f.tipo === "color" ? "selected" : ""}>Color liso</option>
        <option value="degradado" ${f.tipo === "degradado" ? "selected" : ""}>Degradado</option>
        <option value="imagen" ${f.tipo === "imagen" ? "selected" : ""}>Foto</option></select></label>
      ${f.tipo !== "imagen" ? `<div class="fila"><label>Color<input type="color" data-f="color" value="${esc((f.color || "#ffffff").slice(0, 7))}"></label>
        ${f.tipo === "degradado" ? `<label>Color 2<input type="color" data-f="color2" value="${esc((f.color2 || "#000000").slice(0, 7))}"></label>` : ""}</div>` : ""}
      ${f.tipo === "degradado" ? `<label>Ángulo<input type="range" min="0" max="360" data-f="angulo" value="${f.angulo ?? 135}"></label>` : ""}
      ${f.tipo === "imagen" ? `<label>Foto<select data-f="imagen"><option value="">— elige —</option>${imgs.map((i) => `<option value="${esc(i.ruta)}" ${i.ruta === f.imagen ? "selected" : ""}>${esc(i.nombre)}</option>`).join("")}</select></label>
        <label>Oscurecer (para que se lea el texto)<input type="range" min="0" max="0.85" step="0.05" data-f="oscurecer" value="${f.oscurecer ?? 0.35}"></label>` : ""}`;
  },

  pintarProps() {
    const e = Flyer.diseno?.elementos[Flyer.sel];
    $("#fl-capas").classList.toggle("oculto", !e);
    if (!e) { $("#fl-props").innerHTML = `<p class="sutil">Toca algo en el flyer para editarlo.</p>`; return; }
    const num = (k, l, extra = "") => `<label>${l}<input type="number" data-p="${k}" value="${Math.round(e[k] ?? 0)}" ${extra}></label>`;
    const col = (k, l, def) => `<label>${l}<input type="color" data-p="${k}" value="${esc((e[k] || def).slice(0, 7))}"></label>`;
    const chk = (k, l) => `<label class="check"><input type="checkbox" data-p="${k}" ${e[k] ? "checked" : ""}> ${l}</label>`;
    const opa = `<label>Opacidad<input type="range" min="0.05" max="1" step="0.05" data-p="opacidad" value="${e.opacidad ?? 1}"></label>`;
    let html = "";
    if (e.tipo === "texto") {
      html = `<label>Texto<textarea data-p="texto" rows="3">${esc(e.texto)}</textarea></label>
        <label>Letra<select data-p="fuente">${FUENTES.map((f) => `<option ${f === e.fuente ? "selected" : ""} style="font-family:'${f}'">${f}</option>`).join("")}</select></label>
        <div class="fila">${num("tamano", "Tamaño", 'min="8"')}${col("color", "Color", "#000000")}</div>
        <label>Alineación<select data-p="alineacion">${[["left", "Izquierda"], ["center", "Centro"], ["right", "Derecha"]].map(([v, t]) => `<option value="${v}" ${v === (e.alineacion || "left") ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <div class="fila">${chk("negrita", "Negrita")}${chk("cursiva", "Cursiva")}</div>
        ${chk("sombra", "Sombra")}
        <div class="fila">${num("contorno", "Contorno", 'min="0" max="30"')}${col("colorContorno", "Color contorno", "#000000")}</div>
        <label class="check"><input type="checkbox" data-p="caja" ${e.caja ? "checked" : ""}> Fondo detrás del texto</label>
        ${e.caja ? col("caja", "Color del fondo", "#000000") : ""}
        <label>Interlineado<input type="range" min="0.8" max="2" step="0.05" data-p="interlineado" value="${e.interlineado || 1.15}"></label>
        <div class="fila">${num("x", "X")}${num("y", "Y")}${num("ancho", "Ancho")}</div>${opa}`;
    } else if (e.tipo === "forma") {
      html = `${col("color", "Color", "#000000")}
        ${e.forma === "rect" ? num("radio", "Esquinas redondeadas", 'min="0"') : ""}
        <div class="fila">${num("borde", "Borde", 'min="0"')}${col("colorBorde", "Color borde", "#000000")}</div>
        <div class="fila">${num("x", "X")}${num("y", "Y")}</div><div class="fila">${num("ancho", "Ancho")}${num("alto", "Alto")}</div>${opa}`;
    } else if (e.tipo === "imagen") {
      html = `${num("redondeo", "Esquinas redondeadas", 'min="0"')}
        <div class="fila">${num("x", "X")}${num("y", "Y")}</div><div class="fila">${num("ancho", "Ancho")}${num("alto", "Alto")}</div>${opa}`;
    }
    $("#fl-props").innerHTML = html;
  },

  cambiarProp(el) {
    const e = Flyer.diseno.elementos[Flyer.sel];
    if (!e) return;
    const k = el.dataset.p;
    let v = el.type === "checkbox" ? el.checked : el.value;
    if (k === "caja") v = el.type === "checkbox" ? (el.checked ? "#000000" : "") : v;
    else if (el.type === "number" || el.type === "range") v = +v;
    if (k === "ancho" && e.tipo === "imagen" && e.alto && e.ancho) e.alto = Math.round(v * e.alto / e.ancho);
    e[k] = v;
    Flyer.dibujar();
    if (el.type === "checkbox") Flyer.pintarProps();
  },

  // ---------- ratón / dedo ----------
  punto(ev) {
    const r = Flyer.lienzo.getBoundingClientRect();
    return { x: (ev.clientX - r.left) * Flyer.diseno.ancho / r.width, y: (ev.clientY - r.top) * Flyer.diseno.alto / r.height,
      u: Flyer.diseno.ancho / r.width };
  },

  alPresionar(ev) {
    const p = Flyer.punto(ev);
    const c = Flyer.cajas[Flyer.sel];
    const t = 18 * p.u;
    let modo = null;
    if (c && Math.abs(p.x - (c.x + c.w)) < t && Math.abs(p.y - (c.y + c.h)) < t) modo = "tamano";
    else {
      Flyer.sel = -1;
      for (let i = Flyer.cajas.length - 1; i >= 0; i--) {
        const b = Flyer.cajas[i];
        if (b && p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h) { Flyer.sel = i; modo = "mover"; break; }
      }
      Flyer.pintarProps();
    }
    Flyer.dibujar();
    if (!modo) return;
    Flyer.guardarPaso();
    const e = Flyer.diseno.elementos[Flyer.sel];
    Flyer.arrastre = { modo, p0: p, e0: Flyer.copia(e), h0: Flyer.cajas[Flyer.sel].h };
    Flyer.lienzo.setPointerCapture(ev.pointerId);
  },

  alMover(ev) {
    const a = Flyer.arrastre;
    const p = Flyer.punto(ev);
    if (!a) {
      const c = Flyer.cajas[Flyer.sel], t = 18 * p.u;
      Flyer.lienzo.style.cursor = c && Math.abs(p.x - (c.x + c.w)) < t && Math.abs(p.y - (c.y + c.h)) < t ? "nwse-resize" : "default";
      return;
    }
    const e = Flyer.diseno.elementos[Flyer.sel], e0 = a.e0;
    const dx = p.x - a.p0.x, dy = p.y - a.p0.y;
    if (a.modo === "mover") {
      e.x = Math.round(e0.x + dx); e.y = Math.round(e0.y + dy);
      // Imán al centro
      const c = Flyer.cajas[Flyer.sel], W = Flyer.diseno.ancho, im = 12 * p.u;
      if (c && Math.abs(e.x + c.w / 2 - W / 2) < im) e.x = Math.round(W / 2 - c.w / 2);
    } else {
      const nuevoAncho = Math.max(20, e0.ancho + dx);
      if (e.tipo === "texto") {
        const f = nuevoAncho / e0.ancho;
        e.ancho = Math.round(nuevoAncho); e.tamano = Math.max(8, Math.round(e0.tamano * f));
      } else if (e.tipo === "imagen" || (e.tipo === "forma" && e.forma === "circulo" && !ev.shiftKey)) {
        e.ancho = Math.round(nuevoAncho); e.alto = Math.round(e0.alto * nuevoAncho / e0.ancho);
      } else {
        e.ancho = Math.round(nuevoAncho); e.alto = Math.max(2, Math.round(e0.alto + dy));
      }
    }
    Flyer.dibujar();
  },

  alSoltar() {
    if (Flyer.arrastre) { Flyer.arrastre = null; Flyer.pintarProps(); }
  },

  // ---------- acciones ----------
  async exportar() {
    await Flyer.esperarImagenes();
    const c = document.createElement("canvas");
    c.width = Flyer.diseno.ancho; c.height = Flyer.diseno.alto;
    Flyer.dibujarEn(c.getContext("2d"), Flyer.diseno, false);
    const nombre = $("#fl-nombre").value.trim() || "mi_flyer";
    const boton = $("#fl-exportar");
    boton.disabled = true;
    try {
      const r = await App.api("/api/flyer/guardar", { json: { nombre, png: c.toDataURL("image/png"), diseno: Flyer.diseno } });
      Flyer.ultimo = r.ruta;
      $("#fl-descargar").href = "/" + r.ruta;
      $("#fl-descargar").setAttribute("download", r.ruta.split("/").pop());
      $("#fl-despues").classList.remove("oculto");
      App.refrescar();
    } catch (e) { App.aviso(e.message); }
    boton.disabled = false;
  },

  async animar() {
    if (!Flyer.ultimo) return;
    try {
      Trabajos.seguir(await App.api("/api/flyer/animar", { json: {
        imagen: Flyer.ultimo, duracion: +$("#fl-duracion").value || 6, musica: $("#fl-musica").value || null } }));
    } catch (e) { App.aviso(e.message); }
  },

  mostrarPlantillas() {
    const [W, H] = $("#fl-tamano").value.split("x").map(Number);
    App.abrirModal(`<h3>Elige una plantilla</h3><p class="sutil">Después cambias textos, colores y fotos a tu gusto.</p><div class="plantillas" id="fl-lista-plantillas"></div>`);
    const caja = $("#fl-lista-plantillas");
    PLANTILLAS.forEach((pl, i) => {
      const d = Flyer.adaptar(pl.d, W, H);
      if (d.fondo.tipo === "imagen" && !d.fondo.imagen) d.fondo.imagen = Flyer.mejorFoto();
      const cv = document.createElement("canvas");
      cv.width = W; cv.height = H; cv.title = pl.nombre; cv.dataset.i = i;
      const selAnterior = Flyer.sel; Flyer.sel = -1;
      Flyer.dibujarEn(cv.getContext("2d"), d, false);
      Flyer.sel = selAnterior;
      cv.onclick = () => { Flyer.cargar(d); App.cerrarModal(); };
      caja.appendChild(cv);
    });
  },

  async abrir() {
    const lista = await App.api("/api/flyers");
    App.abrirModal(`<h3>Abrir flyer guardado</h3><div class="lista-proyectos">${
      lista.map((p) => `<button class="boton" data-abrir-flyer="${esc(p.nombre)}">🖼️ ${esc(p.nombre)}</button>`).join("")
      || `<p class="sutil">Todavía no guardaste flyers.</p>`}</div>`);
  },

  ajustarVista() { requestAnimationFrame(Flyer.dibujar); },

  iniciar() {
    Flyer.lienzo = $("#fl-lienzo");
    Flyer.ctx = Flyer.lienzo.getContext("2d");
    $("#fl-tamano").innerHTML = TAMANOS.map(([v, t]) => `<option value="${v}">${t}</option>`).join("");
    Flyer.cargar(Flyer.adaptar(PLANTILLAS[0].d, 1080, 1350));
    Flyer.historial = [];

    Flyer.lienzo.addEventListener("pointerdown", Flyer.alPresionar);
    Flyer.lienzo.addEventListener("pointermove", Flyer.alMover);
    Flyer.lienzo.addEventListener("pointerup", Flyer.alSoltar);
    Flyer.lienzo.addEventListener("dblclick", () => { const t = $("#fl-props textarea"); if (t) { t.focus(); t.select(); } });

    $("#fl-tamano").addEventListener("change", (e) => {
      const [W, H] = e.target.value.split("x").map(Number);
      const d = Flyer.diseno, sx = W / d.ancho, sy = H / d.alto, s = Math.min(sx, sy);
      Flyer.guardarPaso();
      for (const el of d.elementos) {
        el.x = Math.round(el.x * sx); el.y = Math.round(el.y * sy);
        if (el.tipo === "texto") { el.ancho = Math.round(el.ancho * sx); el.tamano = Math.round(el.tamano * s); }
        else { el.ancho = Math.round(el.ancho * s); el.alto = Math.round(el.alto * s); }
      }
      d.ancho = W; d.alto = H;
      Flyer.refrescarTodo();
    });
    $("#fl-add-titulo").onclick = () => Flyer.agregarTexto(true);
    $("#fl-add-texto").onclick = () => Flyer.agregarTexto(false);
    $("#fl-add-rect").onclick = () => Flyer.agregarForma("rect");
    $("#fl-add-circulo").onclick = () => Flyer.agregarForma("circulo");
    $("#fl-imagenes").addEventListener("click", (e) => {
      const it = e.target.closest("[data-fl-img]");
      if (it) Flyer.agregarImagen(it.dataset.flImg);
    });
    $("#fl-fondo").addEventListener("input", (e) => {
      const k = e.target.dataset.f;
      if (!k) return;
      const f = Flyer.diseno.fondo;
      f[k] = e.target.type === "range" ? +e.target.value : e.target.value;
      if (k === "tipo") {
        if (f.tipo === "imagen" && !f.imagen) f.imagen = Flyer.mejorFoto();
        if (f.tipo === "imagen" && f.oscurecer == null) f.oscurecer = 0.35;
        Flyer.pintarFondo();
      }
      Flyer.dibujar();
    });
    $("#fl-props").addEventListener("focusin", () => Flyer.guardarPaso(), { once: false });
    $("#fl-props").addEventListener("input", (e) => { if (e.target.dataset.p) Flyer.cambiarProp(e.target); });
    $("#fl-subir").onclick = () => Flyer.moverCapa(1);
    $("#fl-bajar").onclick = () => Flyer.moverCapa(-1);
    $("#fl-duplicar").onclick = () => {
      const e = Flyer.diseno.elementos[Flyer.sel];
      if (e) Flyer.agregar({ ...Flyer.copia(e), x: e.x + 30, y: e.y + 30 });
    };
    $("#fl-borrar").onclick = Flyer.borrar;
    $("#fl-exportar").onclick = Flyer.exportar;
    $("#fl-animar").onclick = Flyer.animar;
    $("#fl-plantillas").onclick = Flyer.mostrarPlantillas;
    $("#fl-abrir").onclick = Flyer.abrir;
    document.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-abrir-flyer]");
      if (!b) return;
      try { Flyer.cargar(await App.api("/api/flyers?nombre=" + encodeURIComponent(b.dataset.abrirFlyer)), b.dataset.abrirFlyer); }
      catch (err) { App.aviso(err.message); }
      App.cerrarModal();
    });
    document.addEventListener("keydown", (e) => {
      if (!$("#tab-flyers").classList.contains("activa")) return;
      if (/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
      const el = Flyer.diseno.elementos[Flyer.sel];
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); return Flyer.deshacer(); }
      if (!el) return;
      if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); return Flyer.borrar(); }
      const paso = e.shiftKey ? 20 : 2;
      const mov = { ArrowLeft: [-paso, 0], ArrowRight: [paso, 0], ArrowUp: [0, -paso], ArrowDown: [0, paso] }[e.key];
      if (mov) { e.preventDefault(); el.x += mov[0]; el.y += mov[1]; Flyer.dibujar(); Flyer.pintarProps(); }
    });
    window.addEventListener("resize", Flyer.ajustarVista);
    Flyer.pintarImagenes();
  },

  moverCapa(dir) {
    const els = Flyer.diseno.elementos, i = Flyer.sel, j = i + dir;
    if (i < 0 || j < 0 || j >= els.length) return;
    Flyer.guardarPaso();
    [els[i], els[j]] = [els[j], els[i]];
    Flyer.sel = j;
    Flyer.dibujar();
  },

  borrar() {
    if (Flyer.sel < 0) return;
    Flyer.guardarPaso();
    Flyer.diseno.elementos.splice(Flyer.sel, 1);
    Flyer.sel = -1;
    Flyer.pintarProps(); Flyer.dibujar();
  },
};

window.Flyer = Flyer;
Flyer.iniciar();
