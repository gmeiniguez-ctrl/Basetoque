/* Basetoque Studio — interfaz principal (archivos, edición rápida, editor de video, asistente). */
"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ICONO = { video: "🎞️", imagen: "🖼️", audio: "🎵", subtitulos: "💬", otro: "📄" };

function fmtDur(s) {
  if (s == null || isNaN(s)) return "";
  s = Math.max(0, s);
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return `${m}:${String(r).padStart(2, "0")}`;
}
function fmtTam(b) {
  if (b > 1e9) return (b / 1e9).toFixed(1) + " GB";
  if (b > 1e6) return (b / 1e6).toFixed(1) + " MB";
  return Math.max(1, Math.round(b / 1e3)) + " KB";
}

const App = {
  estado: {},
  archivos: { media: [], out: [] },
  info: {},             // ruta -> info del archivo

  async api(ruta, opciones = {}) {
    const op = { ...opciones };
    if (op.json !== undefined) {
      op.method = op.method || "POST";
      op.headers = { "Content-Type": "application/json" };
      op.body = JSON.stringify(op.json);
      delete op.json;
    }
    const r = await fetch(ruta, op);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
    return data;
  },

  irA(tab) {
    $$("#pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.tab === tab));
    $$(".tab").forEach((t) => t.classList.toggle("activa", t.id === "tab-" + tab));
    window.scrollTo(0, 0);
    if (tab === "flyers" && window.Flyer) Flyer.ajustarVista();
    App.refrescar();
  },

  aviso(msg) { alert(msg); },

  miniUrl(f) {
    return (f.tipo === "video" || f.tipo === "imagen")
      ? `/api/miniatura?ruta=${encodeURIComponent(f.ruta)}&v=${Math.round(f.modificado)}` : null;
  },

  delTipo(...tipos) {
    return [...App.archivos.media, ...App.archivos.out].filter((f) => tipos.includes(f.tipo));
  },

  opcionesArchivos(select, tipos, vacio) {
    const actual = select.value;
    const lista = App.delTipo(...tipos);
    select.innerHTML = (vacio ? `<option value="">${esc(vacio)}</option>` : "") +
      lista.map((f) => `<option value="${esc(f.ruta)}">${esc(f.ruta)}</option>`).join("");
    if (actual && lista.some((f) => f.ruta === actual)) select.value = actual;
  },

  async refrescar() {
    try {
      const a = await App.api("/api/archivos");
      const firma = JSON.stringify(a);
      if (firma === App._firma) return;
      App._firma = firma;
      App.archivos = a;
      App.info = {};
      [...a.media, ...a.out].forEach((f) => (App.info[f.ruta] = f));
      Archivos.pintar();
      Rapido.pintarArchivos();
      Editor.pintarBiblioteca();
      if (window.Flyer) Flyer.pintarImagenes();
    } catch (e) { console.warn(e); }
  },

  // ---------- modal ----------
  abrirModal(html) {
    $("#modal-contenido").innerHTML = html;
    $("#modal").classList.remove("oculto");
  },
  cerrarModal() {
    $("#modal").classList.add("oculto");
    $("#modal-contenido").innerHTML = "";
  },
  verArchivo(ruta) {
    const f = App.info[ruta] || { ruta, tipo: "otro", nombre: ruta };
    const url = "/" + f.ruta;
    let medio = `<p>${ICONO[f.tipo] || "📄"} ${esc(f.nombre)}</p>`;
    if (f.tipo === "video") medio = `<video src="${url}" controls autoplay playsinline></video>`;
    if (f.tipo === "imagen") medio = `<img src="${url}?v=${Math.round(f.modificado || 0)}" alt="">`;
    if (f.tipo === "audio") medio = `<audio src="${url}" controls autoplay style="width:100%"></audio>`;
    App.abrirModal(`<h3>${esc(f.nombre)}</h3>${medio}
      <div class="botones-fila"><a class="boton primario" href="${url}" download="${esc(f.nombre)}">⬇ Descargar</a></div>`);
  },
};

// ======================================================================
// Trabajos en segundo plano
// ======================================================================
const Trabajos = {
  vistos: new Map(),
  ocultos: new Set(),   // trabajos que siguen en marcha pero el usuario ocultó
  _timer: null,

  seguir(t) {
    Trabajos.vistos.set(t.id, t);
    Trabajos.pintar();
    Trabajos.consultar();
  },

  async consultar() {
    clearTimeout(Trabajos._timer);
    const activos = [...Trabajos.vistos.values()].filter((t) => ["en_cola", "procesando"].includes(t.estado));
    if (!activos.length) return;
    for (const t of activos) {
      try {
        const n = await App.api("/api/trabajos/" + t.id);
        if (n.estado !== t.estado && n.estado === "listo") {
          App.refrescar();
          // Se cierra solo; el resultado queda en "Mis archivos"
          setTimeout(() => { Trabajos.vistos.delete(n.id); Trabajos.pintar(); }, 20000);
        }
        Trabajos.vistos.set(t.id, n);
      } catch (e) { /* servidor reiniciado */ }
    }
    Trabajos.pintar();
    Trabajos._timer = setTimeout(Trabajos.consultar, 1200);
  },

  pintar() {
    const caja = $("#trabajos");
    caja.innerHTML = [...Trabajos.vistos.values()].slice(-4).reverse().map((t) => {
      const seg = t.inicio ? Math.round((t.fin || Date.now() / 1000) - t.inicio) : 0;
      const estado = {
        en_cola: "⏳ En espera…",
        procesando: `<span class="girando"></span> Trabajando… ${seg}s`,
        listo: `✅ ¡Listo! (${seg}s)`,
        error: "❌ No se pudo completar",
      }[t.estado];
      const nombre = t.salida.split("/").pop();
      return `<div class="trabajo ${t.estado}">
        <div class="t-titulo">${esc(t.titulo)}</div>
        <div class="t-estado">${estado}</div>
        ${t.error ? `<div class="t-error">${esc(t.error)}</div>` : ""}
        <div class="t-acciones">
          ${t.estado === "listo" ? `<button class="boton primario" data-ver="${esc(t.salida)}">▶ Ver</button>
            <a class="boton" href="/${esc(t.salida)}" download="${esc(nombre)}">⬇ Descargar</a>` : ""}
          <button class="boton" data-cerrar="${t.id}">${["listo", "error"].includes(t.estado) ? "Cerrar" : "Ocultar"}</button>
        </div></div>`;
    }).join("");
  },
};

// ======================================================================
// Mis archivos
// ======================================================================
const Archivos = {
  tarjeta(f, borrar = true) {
    const mini = App.miniUrl(f);
    return `<div class="archivo">
      <div class="mini" data-ver="${esc(f.ruta)}" style="${mini ? `background-image:url('${mini}')` : ""}">
        ${mini ? "" : ICONO[f.tipo] || "📄"}
        ${f.duracion ? `<span class="dur">${fmtDur(f.duracion)}</span>` : ""}
      </div>
      <div class="info">
        <div class="nombre" title="${esc(f.nombre)}">${esc(f.nombre)}</div>
        <div class="sutil">${ICONO[f.tipo] || ""} ${fmtTam(f.tamano)}${f.ancho ? ` · ${f.ancho}×${f.alto}` : ""}</div>
        <div class="acciones">
          <a class="boton" href="/${esc(f.ruta)}" download="${esc(f.nombre)}" title="Descargar">⬇</a>
          ${borrar ? `<button class="boton peligro" data-borrar="${esc(f.ruta)}" title="Borrar">🗑</button>` : ""}
        </div>
      </div></div>`;
  },

  pintar() {
    const { media, out } = App.archivos;
    $("#lista-media").innerHTML = media.map((f) => Archivos.tarjeta(f)).join("") ||
      `<div class="vacio">Todavía no subiste nada. Arrastra tus archivos arriba.</div>`;
    $("#lista-out").innerHTML = out.map((f) => Archivos.tarjeta(f)).join("") ||
      `<div class="vacio">Aquí aparecerán tus videos y flyers terminados.</div>`;
    $("#inicio-resultados").innerHTML = out.slice(0, 6).map((f) => Archivos.tarjeta(f, false)).join("") ||
      `<div class="vacio">Aún no hay resultados. ¡Empieza subiendo tus archivos!</div>`;
  },

  subir(archivos) {
    const caja = $("#progreso-subida");
    [...archivos].forEach((archivo) => {
      const fila = document.createElement("div");
      fila.innerHTML = `<div class="sutil">Subiendo ${esc(archivo.name)}…</div><div class="barra-progreso"><div></div></div>`;
      caja.appendChild(fila);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/subir?nombre=" + encodeURIComponent(archivo.name));
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) fila.querySelector(".barra-progreso div").style.width = (e.loaded / e.total * 100) + "%";
      };
      xhr.onload = () => {
        if (xhr.status === 200) fila.remove();
        else fila.innerHTML = `<div class="estado-mal">No se pudo subir ${esc(archivo.name)}</div>`;
        App.refrescar();
      };
      xhr.onerror = () => { fila.innerHTML = `<div class="estado-mal">Error subiendo ${esc(archivo.name)}</div>`; };
      xhr.send(archivo);
    });
  },

  async borrar(ruta) {
    if (!confirm(`¿Borrar ${ruta.split("/").pop()}? No se puede deshacer.`)) return;
    await App.api("/api/archivo?ruta=" + encodeURIComponent(ruta), { method: "DELETE" });
    App.refrescar();
  },

  iniciar() {
    const zona = $("#zona-subida");
    $("#input-subida").addEventListener("change", (e) => { Archivos.subir(e.target.files); e.target.value = ""; });
    ["dragenter", "dragover"].forEach((ev) => zona.addEventListener(ev, (e) => { e.preventDefault(); zona.classList.add("encima"); }));
    ["dragleave", "drop"].forEach((ev) => zona.addEventListener(ev, (e) => { e.preventDefault(); zona.classList.remove("encima"); }));
    zona.addEventListener("drop", (e) => Archivos.subir(e.dataTransfer.files));
    // Soltar archivos en cualquier parte de la página también los sube
    document.addEventListener("dragover", (e) => e.preventDefault());
    document.addEventListener("drop", (e) => {
      if (!zona.contains(e.target) && e.dataTransfer.files.length) { e.preventDefault(); Archivos.subir(e.dataTransfer.files); App.irA("archivos"); }
    });
  },
};

// ======================================================================
// Edición rápida
// ======================================================================
const HERRAMIENTAS = [
  { id: "vertical", icono: "📱", titulo: "Pasar a vertical", desc: "Para Reels, TikTok y Shorts", campos: [
    { k: "formato", l: "Formato", t: "select", o: [["9:16", "Vertical 9:16"], ["1:1", "Cuadrado 1:1"], ["4:5", "Post 4:5"], ["16:9", "Horizontal 16:9"]] },
    { k: "modo", l: "Relleno", t: "select", o: [["blur", "Fondo desenfocado (recomendado)"], ["crop", "Recortar (llenar la pantalla)"], ["pad", "Barras negras"]] }] },
  { id: "recortar", icono: "✂️", titulo: "Recortar", desc: "Quedarte con una parte", campos: [
    { k: "inicio", l: "Desde (ej. 0:05)", t: "text", d: "0" }, { k: "fin", l: "Hasta (ej. 0:20)", t: "text" }] },
  { id: "sin_silencios", icono: "🤐", titulo: "Quitar silencios", desc: "Ideal para entrevistas y charlas", campos: [
    { k: "umbral", l: "Sensibilidad", t: "select", o: [["auto", "Automática (recomendada)"], ["-40", "Suave (corta menos)"], ["-26", "Fuerte (corta más)"]] }] },
  { id: "texto", icono: "🔤", titulo: "Agregar texto", desc: "Título o frase sobre el video", campos: [
    { k: "texto", l: "Texto", t: "text", d: "¡Hola!" },
    { k: "posicion", l: "Dónde", t: "select", o: [["top", "Arriba"], ["center", "Centro"], ["bottom", "Abajo"], ["lower-third", "Tercio inferior"]] },
    { k: "tamano", l: "Tamaño", t: "number", d: 72 }, { k: "color", l: "Color", t: "color", d: "#ffffff" },
    { k: "caja", l: "Fondo detrás del texto", t: "check", d: true },
    { k: "inicio", l: "Aparece en (s, opcional)", t: "text" }, { k: "fin", l: "Desaparece en (s, opcional)", t: "text" }] },
  { id: "musica", icono: "🎵", titulo: "Agregar música", desc: "Baja sola cuando alguien habla", campos: [
    { k: "musica", l: "Canción", t: "archivo", tipos: ["audio"] },
    { k: "volumen", l: "Volumen de la música", t: "select", o: [["0.15", "Bajito"], ["0.25", "Normal"], ["0.45", "Alto"]] },
    { k: "reemplazar", l: "Quitar el sonido original", t: "check" }] },
  { id: "color", icono: "🎨", titulo: "Mejorar el color", desc: "Estilos tipo película", campos: [
    { k: "preset", l: "Estilo", t: "select", o: [["cinematic", "Cinematográfico"], ["warm", "Cálido"], ["cool", "Frío"], ["vivid", "Vivo"], ["bw", "Blanco y negro"], ["vintage", "Vintage"], ["dramatic", "Dramático"], ["fade", "Suave / pastel"]] }] },
  { id: "logo", icono: "🏷️", titulo: "Poner mi logo", desc: "Marca de agua", campos: [
    { k: "logo", l: "Logo (imagen)", t: "archivo", tipos: ["imagen"] },
    { k: "posicion", l: "Dónde", t: "select", o: [["bottom-right", "Abajo derecha"], ["bottom-left", "Abajo izquierda"], ["top-right", "Arriba derecha"], ["top-left", "Arriba izquierda"]] },
    { k: "escala", l: "Tamaño", t: "select", o: [["0.12", "Chico"], ["0.18", "Mediano"], ["0.25", "Grande"]] }] },
  { id: "subtitulos", icono: "💬", titulo: "Subtítulos", desc: "Quema un archivo .srt", campos: [
    { k: "subtitulos", l: "Archivo de subtítulos", t: "archivo", tipos: ["subtitulos"] }] },
  { id: "audio", icono: "🎙️", titulo: "Limpiar la voz", desc: "Quita ruido y empareja el volumen", campos: [] },
  { id: "velocidad", icono: "⏩", titulo: "Velocidad", desc: "Cámara lenta o rápida", campos: [
    { k: "factor", l: "Velocidad", t: "select", o: [["0.5", "Cámara lenta (x0.5)"], ["0.75", "Un poco lento"], ["1.5", "Rápido (x1.5)"], ["2", "Muy rápido (x2)"], ["4", "Timelapse (x4)"]] }] },
  { id: "estabilizar", icono: "🤳", titulo: "Estabilizar", desc: "Para videos movidos", campos: [] },
  { id: "fundido", icono: "🌗", titulo: "Fundidos", desc: "Entrada y salida suave", campos: [
    { k: "entrada", l: "Fundido al inicio (s)", t: "number", d: 1 }, { k: "salida", l: "Fundido al final (s)", t: "number", d: 1.5 }] },
  { id: "comprimir", icono: "🗜️", titulo: "Hacerlo más liviano", desc: "Para enviar por WhatsApp o mail", campos: [
    { k: "mb", l: "Tamaño máximo en MB (vacío = automático)", t: "number" }] },
  { id: "gif", icono: "🌀", titulo: "Convertir en GIF", desc: "Animación corta", campos: [
    { k: "inicio", l: "Desde (s)", t: "text", d: "0" }, { k: "duracion", l: "Duración (s)", t: "number", d: 4 }] },
  { id: "miniatura", icono: "📸", titulo: "Sacar portada", desc: "La mejor imagen del video", campos: [] },
  { id: "extraer_audio", icono: "🎧", titulo: "Sacar el audio", desc: "Guardar como MP3", campos: [] },
  { id: "invertir", icono: "⏪", titulo: "Al revés", desc: "Reproducir hacia atrás", campos: [] },
];

const Rapido = {
  sel: null,

  pintarArchivos() {
    App.opcionesArchivos($("#rapido-archivo"), ["video"], "— elige un video —");
    $$("#rapido-opciones select[data-archivo]").forEach((s) => App.opcionesArchivos(s, s.dataset.archivo.split(","), "— elige —"));
  },

  pintarOpciones() {
    const h = Rapido.sel;
    $("#rapido-opciones-caja").classList.toggle("oculto", !h);
    if (!h) return;
    $("#rapido-opciones").innerHTML = h.campos.map((c) => {
      if (c.t === "select") return `<label>${esc(c.l)}<select data-k="${c.k}">${c.o.map(([v, t]) => `<option value="${esc(v)}">${esc(t)}</option>`).join("")}</select></label>`;
      if (c.t === "archivo") return `<label>${esc(c.l)}<select data-k="${c.k}" data-archivo="${c.tipos.join(",")}"></select>
        <span class="sutil">¿No aparece? Súbelo en “Mis archivos”.</span></label>`;
      if (c.t === "check") return `<label class="check"><input type="checkbox" data-k="${c.k}" ${c.d ? "checked" : ""}> ${esc(c.l)}</label>`;
      return `<label>${esc(c.l)}<input type="${c.t}" data-k="${c.k}" value="${esc(c.d ?? "")}"></label>`;
    }).join("") || `<p class="sutil">No hace falta configurar nada.</p>`;
    Rapido.pintarArchivos();
  },

  async ejecutar() {
    const archivo = $("#rapido-archivo").value;
    if (!archivo) return App.aviso("Primero elige un video.");
    const opciones = {};
    $$("#rapido-opciones [data-k]").forEach((el) => {
      opciones[el.dataset.k] = el.type === "checkbox" ? el.checked : el.value;
    });
    for (const c of Rapido.sel.campos) {
      if (c.t === "archivo" && !opciones[c.k]) return App.aviso(`Falta elegir: ${c.l}`);
    }
    const boton = $("#rapido-ejecutar");
    boton.disabled = true;
    try {
      Trabajos.seguir(await App.api("/api/herramienta", { json: { herramienta: Rapido.sel.id, archivo, opciones } }));
    } catch (e) { App.aviso(e.message); }
    boton.disabled = false;
  },

  iniciar() {
    $("#rapido-herramientas").innerHTML = HERRAMIENTAS.map((h) =>
      `<button class="herramienta" data-h="${h.id}"><b>${h.icono} ${esc(h.titulo)}</b><small>${esc(h.desc)}</small></button>`).join("");
    $("#rapido-herramientas").addEventListener("click", (e) => {
      const b = e.target.closest("[data-h]");
      if (!b) return;
      Rapido.sel = HERRAMIENTAS.find((h) => h.id === b.dataset.h);
      $$(".herramienta").forEach((x) => x.classList.toggle("activa", x === b));
      Rapido.pintarOpciones();
    });
    $("#rapido-ejecutar").addEventListener("click", Rapido.ejecutar);
  },
};

// ======================================================================
// Editor de video (proyecto)
// ======================================================================
const ALTO_SALIDA = { "9:16": 1920, "16:9": 1080, "1:1": 1080, "4:5": 1350 };

const Editor = {
  clips: [],
  extraTextos: [],   // textos globales que vengan del asistente o de proyectos
  sel: -1,

  nuevo() {
    Editor.clips = [];
    Editor.extraTextos = [];
    Editor.sel = -1;
    $("#ed-nombre").value = "mi_video";
    $("#ed-musica").value = ""; $("#ed-logo").value = ""; $("#ed-subs").value = "";
    $("#ed-color").value = ""; $("#ed-firma").value = ""; $("#ed-transicion").value = "cut";
    Editor.pintar();
  },

  agregar(ruta) {
    const f = App.info[ruta];
    if (!f) return;
    if (f.tipo === "video") Editor.clips.push({ src: ruta, start: 0, end: +(f.duracion || 0).toFixed(2) });
    else if (f.tipo === "imagen") Editor.clips.push({ src: ruta, duration: 3, kenburns: true });
    else if (f.tipo === "audio") { $("#ed-musica").value = ruta; return; }
    else if (f.tipo === "subtitulos") { $("#ed-subs").value = ruta; return; }
    Editor.seleccionar(Editor.clips.length - 1);
  },

  agregarTarjeta() {
    Editor.clips.push({ color: "#111111", duration: 2, text: [{ text: "TU TÍTULO", position: "center" }], transition: "fadeblack" });
    Editor.seleccionar(Editor.clips.length - 1);
  },

  duracionClip(c) {
    if (c.src && App.info[c.src]?.tipo === "video") {
      const total = App.info[c.src].duracion || 0;
      const fin = c.end != null && c.end !== "" ? +c.end : total;
      return Math.max(0, (fin - (+c.start || 0)) / (+c.speed || 1));
    }
    return +c.duration || 0;
  },

  seleccionar(i) {
    Editor.sel = i;
    Editor.pintar();
    const c = Editor.clips[i];
    const video = $("#ed-visor"), img = $("#ed-visor-img");
    $("#ed-visor-vacio").classList.toggle("oculto", !!c);
    video.classList.add("oculto"); img.classList.add("oculto");
    $("#ed-marcas").classList.add("oculto");
    if (!c) return;
    const tipo = c.src ? App.info[c.src]?.tipo : "color";
    if (tipo === "video") {
      video.classList.remove("oculto");
      if (video.dataset.src !== c.src) { video.src = "/" + c.src; video.dataset.src = c.src; }
      video.currentTime = +c.start || 0;
      $("#ed-marcas").classList.remove("oculto");
      Editor.pintarRango();
    } else if (tipo === "imagen") {
      img.classList.remove("oculto"); img.src = "/" + c.src;
      video.pause();
    } else {
      video.pause();
      $("#ed-visor-vacio").classList.remove("oculto");
      $("#ed-visor-vacio").textContent = "🟦 Tarjeta de título: " + (c.text?.[0]?.text || "");
    }
  },

  pintarRango() {
    const c = Editor.clips[Editor.sel];
    if (c) $("#ed-rango").textContent = `Usando de ${fmtDur(+c.start || 0)} a ${fmtDur(c.end ?? App.info[c.src]?.duracion)}`;
  },

  marcar(cual) {
    const c = Editor.clips[Editor.sel];
    const t = +$("#ed-visor").currentTime.toFixed(2);
    if (!c) return;
    if (cual === "inicio") { c.start = t; if (c.end != null && c.end <= t) c.end = null; }
    else { if (t <= (+c.start || 0)) return App.aviso("El fin tiene que ser después del inicio."); c.end = t; }
    Editor.pintar(); Editor.pintarRango();
  },

  opcionesTransicion(valor, conDefecto) {
    const nombres = { cut: "Corte directo", fade: "Fundido", fadeblack: "Fundido a negro", fadewhite: "Fundido a blanco",
      dissolve: "Disolver", slideleft: "Deslizar ←", slideright: "Deslizar →", slideup: "Deslizar ↑", wipeleft: "Barrido ←",
      wiperight: "Barrido →", circleopen: "Círculo", zoomin: "Zoom", pixelize: "Pixelado", radial: "Radial", smoothleft: "Suave ←" };
    const lista = ["cut", ...(App.estado.transiciones || Object.keys(nombres)).filter((t) => nombres[t])];
    return (conDefecto ? `<option value="">(como el resto)</option>` : "") +
      [...new Set(lista)].map((t) => `<option value="${t}" ${t === valor ? "selected" : ""}>${nombres[t] || t}</option>`).join("");
  },

  pintar() {
    const total = Editor.clips.reduce((s, c) => s + Editor.duracionClip(c), 0);
    $("#ed-duracion").textContent = Editor.clips.length ? `· ${Editor.clips.length} partes · ~${fmtDur(total)}` : "";
    $("#ed-clips").innerHTML = Editor.clips.map((c, i) => {
      const f = c.src ? App.info[c.src] : null;
      const tipo = f?.tipo || (c.src ? "falta" : "color");
      const mini = f ? App.miniUrl(f) : null;
      const texto = c.text?.[0]?.text || "";
      let campos = "";
      if (tipo === "video") {
        campos = `<label>Desde (s)<input type="number" step="0.1" min="0" data-c="start" value="${c.start ?? 0}"></label>
          <label>Hasta (s)<input type="number" step="0.1" min="0" data-c="end" value="${c.end ?? ""}"></label>
          <label>Velocidad<select data-c="speed">${[0.5, 0.75, 1, 1.25, 1.5, 2].map((v) => `<option ${(+c.speed || 1) === v ? "selected" : ""}>${v}</option>`).join("")}</select></label>
          <label class="check"><input type="checkbox" data-c="mute" ${c.mute ? "checked" : ""}> Sin sonido</label>`;
      } else if (tipo === "imagen") {
        campos = `<label>Duración (s)<input type="number" step="0.5" min="0.5" data-c="duration" value="${c.duration ?? 3}"></label>
          <label class="check"><input type="checkbox" data-c="kenburns" ${c.kenburns ? "checked" : ""}> Zoom lento</label>`;
      } else if (tipo === "color") {
        campos = `<label>Color<input type="color" data-c="color" value="${esc(c.color || "#111111")}"></label>
          <label>Duración (s)<input type="number" step="0.5" min="0.5" data-c="duration" value="${c.duration ?? 2}"></label>`;
      } else {
        campos = `<span class="estado-mal">Falta el archivo ${esc(c.src)}</span>`;
      }
      const pos = c.text?.[0]?.position || c._pos || "center";
      return `<div class="clip ${i === Editor.sel ? "sel" : ""}" data-i="${i}">
        <div class="num">${i + 1}</div>
        <div class="mini" data-sel="${i}" style="${mini ? `background-image:url('${mini}')` : `background:${esc(c.color || "#333")}`}">${mini ? "" : esc(texto || "Tarjeta")}</div>
        <div class="campos">${campos}
          <label class="texto-clip">Texto en pantalla<input data-c="texto" value="${esc(texto)}" placeholder="opcional"></label>
          <label>Texto en<select data-c="posicion">${[["top", "Arriba"], ["center", "Centro"], ["bottom", "Abajo"]].map(([v, t]) => `<option value="${v}" ${v === pos ? "selected" : ""}>${t}</option>`).join("")}</select></label>
          ${i < Editor.clips.length - 1 ? `<label>Paso al siguiente<select data-c="transition">${Editor.opcionesTransicion(typeof c.transition === "object" ? c.transition?.type : c.transition, true)}</select></label>` : ""}
          <span class="sutil">${fmtDur(Editor.duracionClip(c))}</span>
        </div>
        <div class="ctrl">
          <button class="boton" data-mover="-1" title="Subir">↑</button>
          <button class="boton" data-mover="1" title="Bajar">↓</button>
          <button class="boton peligro" data-quitar title="Quitar">✕</button>
        </div></div>`;
    }).join("") || `<div class="vacio">Tu video está vacío. Toca tus clips o fotos a la izquierda para agregarlos en orden.</div>`;
  },

  cambiarCampo(i, campo, el) {
    const c = Editor.clips[i];
    const v = el.type === "checkbox" ? el.checked : el.value;
    if (campo === "texto") {
      if (!v) delete c.text;
      else { c.text = c.text?.length ? c.text : [{}]; c.text[0].text = v; }
    } else if (campo === "posicion") {
      if (c.text?.length) c.text[0].position = v;
      else c._pos = v;
    } else if (campo === "transition") {
      if (v) c.transition = v; else delete c.transition;
    } else if (["start", "end", "duration", "speed"].includes(campo)) {
      c[campo] = v === "" ? null : +v;
    } else {
      c[campo] = v;
    }
    if (campo === "texto" && c._pos && c.text) { c.text[0].position = c._pos; delete c._pos; }
    Editor.pintar();
    if (campo === "start" || campo === "end") Editor.pintarRango();
  },

  pintarBiblioteca() {
    const lista = App.delTipo("video", "imagen");
    $("#ed-biblioteca").innerHTML = lista.map((f) => {
      const mini = App.miniUrl(f);
      return `<div class="item" data-agregar="${esc(f.ruta)}" title="${esc(f.ruta)}">
        <div class="mini" style="${mini ? `background-image:url('${mini}')` : ""}">${mini ? "" : ICONO[f.tipo]}</div>
        <div>${esc(f.nombre)}</div></div>`;
    }).join("") || `<p class="sutil">Sube videos o fotos en “Mis archivos”.</p>`;
    App.opcionesArchivos($("#ed-musica"), ["audio"], "Sin música");
    App.opcionesArchivos($("#ed-logo"), ["imagen"], "Sin logo");
    App.opcionesArchivos($("#ed-subs"), ["subtitulos"], "Sin subtítulos");
    Editor.pintar();
  },

  timeline() {
    const formato = $("#ed-formato").value;
    const H = ALTO_SALIDA[formato] || 1080;
    const clips = Editor.clips.map((c) => {
      const k = JSON.parse(JSON.stringify(c));
      delete k._pos;
      if (k.end === null) delete k.end;
      if (k.speed === 1 || k.speed === "1") delete k.speed;
      (k.text || []).forEach((t) => {
        const tarjeta = !k.src;
        t.position = t.position || "center";
        t.size = t.size || Math.round(H * (tarjeta ? 0.065 : 0.042));
        if (!tarjeta && t.box === undefined) t.box = true;
        if (t.fade === undefined) t.fade = 0.3;
      });
      return k;
    });
    const tl = { formato, fit: "blur", clips, text: [...Editor.extraTextos] };
    const tr = $("#ed-transicion").value;
    if (tr && tr !== "cut") tl.transition = { type: tr, duration: 0.5 };
    const firma = $("#ed-firma").value.trim();
    if (firma) tl.text.push({ text: firma, position: "top-right", size: Math.round(H * 0.022), outline: 2, _firma: true });
    if ($("#ed-musica").value) tl.music = { src: $("#ed-musica").value, volume: +$("#ed-volumen").value };
    if ($("#ed-color").value) tl.color = { preset: $("#ed-color").value };
    if ($("#ed-logo").value) tl.watermark = { src: $("#ed-logo").value, position: $("#ed-logo-pos").value, scale: 0.12, opacity: 0.85 };
    if ($("#ed-subs").value) tl.subtitles = $("#ed-subs").value;
    if ($("#ed-fundidos").checked) { tl.fade_in = 0.3; tl.fade_out = 0.8; }
    if ($("#ed-normalizar").checked) tl.loudnorm = true;
    return tl;
  },

  cargar(tl, nombre) {
    tl = JSON.parse(JSON.stringify(tl || {}));
    if (nombre) $("#ed-nombre").value = nombre;
    if (tl.formato || tl.aspect) $("#ed-formato").value = tl.formato || tl.aspect;
    Editor.clips = (tl.clips || []).map((c) => {
      if (c.transition && typeof c.transition === "object") c.transition = c.transition.type;
      return c;
    });
    Editor.extraTextos = (tl.text || []).filter((t) => !t._firma);
    $("#ed-firma").value = (tl.text || []).find((t) => t._firma)?.text || "";
    const tr = typeof tl.transition === "object" ? tl.transition?.type : tl.transition;
    $("#ed-transicion").value = tr || "cut";
    $("#ed-musica").value = tl.music?.src || "";
    if (tl.music?.volume) $("#ed-volumen").value = tl.music.volume;
    $("#ed-color").value = (typeof tl.color === "string" ? tl.color : tl.color?.preset) || "";
    $("#ed-logo").value = tl.watermark?.src || "";
    if (tl.watermark?.position) $("#ed-logo-pos").value = tl.watermark.position;
    $("#ed-subs").value = tl.subtitles || "";
    $("#ed-fundidos").checked = !!(tl.fade_in || tl.fade_out);
    $("#ed-normalizar").checked = tl.loudnorm !== false;
    Editor.sel = -1;
    Editor.pintar();
    if (Editor.clips.length) Editor.seleccionar(0);
  },

  async render() {
    if (!Editor.clips.length) return App.aviso("Agrega al menos un clip, foto o tarjeta.");
    const faltan = Editor.clips.filter((c) => c.src && !App.info[c.src]);
    if (faltan.length) return App.aviso("Faltan archivos: " + faltan.map((c) => c.src).join(", "));
    const boton = $("#ed-render");
    boton.disabled = true;
    try {
      await Editor.guardar(true);
      Trabajos.seguir(await App.api("/api/render", { json: { nombre: $("#ed-nombre").value, proyecto: Editor.timeline() } }));
    } catch (e) { App.aviso(e.message); }
    boton.disabled = false;
  },

  async guardar(silencioso) {
    const nombre = $("#ed-nombre").value.trim() || "mi_video";
    await App.api("/api/proyectos", { json: { nombre, contenido: Editor.timeline() } });
    if (silencioso !== true) App.aviso("Proyecto guardado ✔");
  },

  async abrir() {
    const lista = await App.api("/api/proyectos");
    App.abrirModal(`<h3>Abrir proyecto de video</h3><div class="lista-proyectos">${
      lista.map((p) => `<button class="boton" data-abrir-proyecto="${esc(p.nombre)}">🎞️ ${esc(p.nombre)}
        <span class="sutil">${new Date(p.modificado * 1000).toLocaleString()}</span></button>`).join("")
      || `<p class="sutil">No hay proyectos guardados todavía.</p>`}</div>`);
  },

  iniciar() {
    $("#ed-color").innerHTML = `<option value="">Natural</option>` + [["cinematic", "Cinematográfico"], ["warm", "Cálido"], ["cool", "Frío"],
      ["vivid", "Vivo"], ["bw", "Blanco y negro"], ["vintage", "Vintage"], ["dramatic", "Dramático"], ["fade", "Suave / pastel"]]
      .map(([v, t]) => `<option value="${v}">${t}</option>`).join("");
    $("#ed-transicion").innerHTML = Editor.opcionesTransicion("cut");
    $("#ed-biblioteca").addEventListener("click", (e) => {
      const it = e.target.closest("[data-agregar]");
      if (it) Editor.agregar(it.dataset.agregar);
    });
    $("#ed-tarjeta").addEventListener("click", Editor.agregarTarjeta);
    $("#ed-clips").addEventListener("click", (e) => {
      const fila = e.target.closest(".clip");
      if (!fila) return;
      const i = +fila.dataset.i;
      if (e.target.closest("[data-sel]")) return Editor.seleccionar(i);
      const mover = e.target.closest("[data-mover]");
      if (mover) {
        const j = i + +mover.dataset.mover;
        if (j < 0 || j >= Editor.clips.length) return;
        [Editor.clips[i], Editor.clips[j]] = [Editor.clips[j], Editor.clips[i]];
        Editor.sel = j;
        return Editor.pintar();
      }
      if (e.target.closest("[data-quitar]")) {
        Editor.clips.splice(i, 1);
        return Editor.seleccionar(Math.min(i, Editor.clips.length - 1));
      }
      if (Editor.sel !== i && !e.target.closest("input,select")) Editor.seleccionar(i);
    });
    $("#ed-clips").addEventListener("change", (e) => {
      const el = e.target.closest("[data-c]");
      if (el) Editor.cambiarCampo(+el.closest(".clip").dataset.i, el.dataset.c, el);
    });
    $("#ed-marcar-inicio").addEventListener("click", () => Editor.marcar("inicio"));
    $("#ed-marcar-fin").addEventListener("click", () => Editor.marcar("fin"));
    $("#ed-render").addEventListener("click", Editor.render);
    $("#ed-guardar").addEventListener("click", Editor.guardar);
    $("#ed-abrir").addEventListener("click", Editor.abrir);
    $("#ed-nuevo").addEventListener("click", () => { if (!Editor.clips.length || confirm("¿Empezar un video nuevo?")) Editor.nuevo(); });
    Editor.pintar();
  },
};

// ======================================================================
// Asistente
// ======================================================================
const Asistente = {
  historial: [],
  modo() { return $("input[name=modo]:checked").value; },

  agregar(clase, html) {
    const div = document.createElement("div");
    div.className = "msg " + clase;
    div.innerHTML = html;
    $("#chat").appendChild(div);
    $("#chat").scrollTop = $("#chat").scrollHeight;
    return div;
  },

  async enviar(e) {
    e.preventDefault();
    const texto = $("#chat-texto").value.trim();
    if (!texto) return;
    if (!App.estado.asistente) {
      Asistente.agregar("claude error", "Todavía no estoy conectado dentro de la app. Mira el panel de la derecha: puedes pegar una clave (Opción A) o hablarme desde Claude Code (Opción B).");
      return;
    }
    const modo = Asistente.modo();
    $("#chat-texto").value = "";
    Asistente.agregar("yo", esc(texto));
    const pensando = Asistente.agregar("claude", `<span class="girando"></span> Pensando…`);
    $("#chat-enviar").disabled = true;
    try {
      const actual = modo === "flyer" ? (window.Flyer ? Flyer.diseno : null) : (Editor.clips.length ? Editor.timeline() : null);
      const r = await App.api("/api/asistente", { json: { mensaje: texto, modo, historial: Asistente.historial, actual } });
      Asistente.historial.push({ role: "user", content: texto });
      Asistente.historial.push({ role: "assistant", content: r.texto + (r.diseno ? "\n```json\n" + JSON.stringify(r.diseno) + "\n```" : "") });
      pensando.innerHTML = esc(r.texto);
      if (r.diseno) {
        const b = document.createElement("button");
        b.className = "boton primario";
        b.textContent = modo === "flyer" ? "🖼️ Abrir en el editor de flyers" : "🎞️ Abrir en el editor de video";
        b.onclick = () => {
          if (modo === "flyer") { Flyer.cargar(r.diseno); App.irA("flyers"); }
          else { Editor.cargar(r.diseno); App.irA("editor"); }
        };
        pensando.appendChild(document.createElement("br"));
        pensando.appendChild(b);
      }
    } catch (err) {
      pensando.classList.add("error");
      pensando.textContent = err.message;
    }
    $("#chat-enviar").disabled = false;
  },

  pintarEstado() {
    const est = App.estado.asistente_detalle;
    $("#asis-estado").innerHTML = {
      listo: `<p class="estado-ok">✔ Claude está conectado dentro de la app.</p>`,
      falta_clave: `<p class="estado-mal">Claude todavía no está conectado dentro de la app.</p>`,
      falta_sdk: `<p class="estado-mal">Falta instalar el asistente (INSTALAR.md, paso 3).</p>`,
    }[est] || "";
    $("#asis-carpeta").textContent = App.estado.carpeta || "";
  },

  iniciar() {
    $("#chat-form").addEventListener("submit", Asistente.enviar);
    $("#chat-texto").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#chat-form").requestSubmit(); }
    });
    $("#asis-guardar").addEventListener("click", async () => {
      const clave = $("#asis-clave").value.trim();
      if (!clave) return App.aviso("Pega tu clave primero.");
      const r = await App.api("/api/config", { json: { clave } });
      $("#asis-clave").value = "";
      App.estado.asistente = r.asistente === "listo";
      App.estado.asistente_detalle = r.asistente;
      Asistente.pintarEstado();
    });
  },
};

// ======================================================================
// Arranque
// ======================================================================
document.addEventListener("click", async (e) => {
  const t = e.target;
  const ir = t.closest("[data-ir]"); if (ir) return App.irA(ir.dataset.ir);
  const tab = t.closest("#pestanas [data-tab]"); if (tab) return App.irA(tab.dataset.tab);
  const ver = t.closest("[data-ver]"); if (ver) return App.verArchivo(ver.dataset.ver);
  const borrar = t.closest("[data-borrar]"); if (borrar) return Archivos.borrar(borrar.dataset.borrar);
  const cerrar = t.closest("[data-cerrar]");
  if (cerrar) {
    const id = cerrar.dataset.cerrar, tr = Trabajos.vistos.get(id);
    Trabajos.vistos.delete(id);
    if (tr && !["listo", "error"].includes(tr.estado)) Trabajos.ocultos.add(id);
    return Trabajos.pintar();
  }
  const proy = t.closest("[data-abrir-proyecto]");
  if (proy) {
    try { Editor.cargar(await App.api("/api/proyectos?nombre=" + encodeURIComponent(proy.dataset.abrirProyecto)), proy.dataset.abrirProyecto); }
    catch (err) { App.aviso(err.message); }
    return App.cerrarModal();
  }
  if (t.id === "modal-cerrar" || t.id === "modal") App.cerrarModal();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") App.cerrarModal(); });

(async function iniciar() {
  Archivos.iniciar();
  Rapido.iniciar();
  Editor.iniciar();
  Asistente.iniciar();
  try {
    App.estado = await App.api("/api/estado");
    $("#aviso-ffmpeg").classList.toggle("oculto", App.estado.ffmpeg);
    $("#ed-transicion").innerHTML = Editor.opcionesTransicion("cut");
    Asistente.pintarEstado();
  } catch (e) {
    document.body.insertAdjacentHTML("afterbegin", `<div class="aviso">No me puedo comunicar con el programa. ¿Cerraste la ventana negra? Vuelve a abrir Basetoque.</div>`);
  }
  await App.refrescar();
  try {
    const trabajos = await App.api("/api/trabajos");
    trabajos.filter((t) => ["en_cola", "procesando"].includes(t.estado) && !Trabajos.ocultos.has(t.id)).forEach(Trabajos.seguir);
  } catch (e) { /* nada */ }
  setInterval(() => { if (!document.hidden) App.refrescar(); }, 6000);
  window.addEventListener("focus", App.refrescar);
})();
