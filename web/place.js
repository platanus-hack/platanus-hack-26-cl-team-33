/* Aterriza: coloca un data center y sigue a sus vecinos. Usa los utilitarios de story.js
   ($, fmt, esc, reduced, ST, DC_INK, METRICS, ramp, mix, MID, BETTER, WORSE, dcStyle). */
"use strict";

const PL = { meta: null, map: null, site: null, marker: null, rings: null, probeLayer: null,
  canvas: null, dots: [], res: null, frame: 0, view: "value", playing: null, timer: null, diffMax: 1 };
// de abajo hacia arriba en el gráfico de estados; tonos validados contra daltonismo (pares vecinos)
const PSTATUS = [
  { k: ST.OPER, label: "Operando", c: "#8a2b6f" },
  { k: ST.BUILD, label: "En obra", c: "#e099c4" },
  { k: ST.LITIG, label: "En tribunales", c: "#e0622a" },
  { k: ST.PERMIT, label: "En trámite", c: "#2a78d6" },
  { k: ST.WAIT, label: "Esperando red", c: "#eda100" },
  { k: ST.CANCEL, label: "Desistió", c: "#6250d6" },
];
const PCOL = { with: "#e0622a", without: "#4f63b0" };
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"];
const ymLabel = (s) => { const [y, m] = s.split("-").map(Number); return `${MESES[m - 1]} ${y}`; };
const pc = (x, d = 0) => `${fmt(100 * x, d)}%`;
const REAL_CODE = { operando: ST.OPER, construccion: ST.BUILD, tramitacion: ST.PERMIT, lista_espera: ST.WAIT };
const SVGNS = "http://www.w3.org/2000/svg";

// ---------------------------------------------------------------- arranque (lo llama story.js)
function initPlace(meta) {
  PL.meta = meta;
  const pm = meta.place;
  document.querySelectorAll("[data-place-n]").forEach((el) => { el.textContent = pm.n; });
  $("#placeYear").innerHTML = pm.years.map((y) => `<option value="${y}">${y}</option>`).join("");
  $("#placeRule").innerHTML = pm.rules.map((r) => `<option value="${esc(r.id)}">${esc(r.name)}</option>`).join("");
  $("#placeRun").textContent = `Simular ${pm.n} futuros`;

  const map = PL.map = L.map("placeMap", { scrollWheelZoom: false, zoomControl: false }).setView([-33.39, -70.76], 11);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 17, className: "base-tiles",
  }).addTo(map);
  const key = L.control({ position: "topleft" });
  key.onAdd = () => { const d = L.DomUtil.create("div", "map-key"); d.id = "placeKey"; d.hidden = true; L.DomEvent.disableClickPropagation(d); return d; };
  key.addTo(map);
  // zonas donde el modelo tiene hogares: más oscuro = más denso
  const areas = L.layerGroup().addTo(map);
  pm.areas.forEach(([la, lo, r, d]) => L.circle([la, lo], { radius: r * 1000, stroke: false, fillColor: "#545b67",
    fillOpacity: Math.min(0.26, 0.05 + d / 25000), interactive: false }).addTo(areas));
  // data centers reales, con su estado a noviembre de 2026
  const real = L.layerGroup().addTo(map);
  meta.projects.forEach((p) => {
    const code = p.pre_existing ? ST.OPER : REAL_CODE[p.real_status];
    if (code === undefined) return;
    const st = dcStyle(code, p.it_mw);
    st.radius = 2.5 + 0.7 * Math.sqrt(p.it_mw);
    L.circleMarker([p.lat, p.lon], st).bindTooltip(`<b>${esc(p.name)}</b> · ${fmt(p.it_mw)} MW<br>${esc(meta.status_labels[code])} (nov-2026)`).addTo(real);
  });
  PL.canvas = L.canvas({ padding: 0.3 });
  PL.probeLayer = L.layerGroup().addTo(map);
  PL.rings = L.layerGroup().addTo(map);
  map.on("click", (e) => placeAt(e.latlng.lat, e.latlng.lng));

  document.querySelectorAll(".place-examples [data-ll]").forEach((b) => b.addEventListener("click", () => {
    const [la, lo, z] = b.dataset.ll.split(",").map(Number);
    map.setView([la, lo], z);
    placeAt(la, lo);
  }));
  $("#placeForm").addEventListener("submit", (e) => { e.preventDefault(); runPlace(); });
  $("#placeForm").addEventListener("change", (e) => { if (e.target.name && PL.res) markStale(); });
  document.querySelectorAll("[data-pview]").forEach((b) => b.addEventListener("click", () => setPView(b.dataset.pview)));
  $("#placeFrame").addEventListener("input", (e) => { stopPPlay(); PL.frame = Number(e.target.value); updateFrame(); });
  $("#placePlay").addEventListener("click", () => (PL.playing ? stopPPlay() : startPPlay()));
  let rt;
  addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => PL.res && renderCharts(), 150); });
  const io2 = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) { setTimeout(() => map.invalidateSize(), 50); io2.disconnect(); }
  }), { threshold: 0.1 });
  io2.observe($(".place-card"));
}

// ---------------------------------------------------------------- elegir el sitio
const youIcon = L.divIcon({ className: "you-icon", html: "<i></i>", iconSize: [22, 22], iconAnchor: [11, 11] });

function placeAt(lat, lon) {
  if (PL.busy) return;
  if (!PL.marker) {
    PL.marker = L.marker([lat, lon], { icon: youIcon, draggable: true, keyboard: false, zIndexOffset: 1000 }).addTo(PL.map);
    PL.marker.on("dragend", () => { const ll = PL.marker.getLatLng(); placeAt(ll.lat, ll.lng); });
    PL.marker.bindTooltip("Tu data center. Arrástralo para moverlo.");
  } else {
    PL.marker.setLatLng([lat, lon]);
  }
  PL.rings.clearLayers();
  [0.5, 3].forEach((km) => L.circle([lat, lon], { radius: km * 1000, color: DC_INK, weight: 1, opacity: 0.7, fill: false, interactive: false }).addTo(PL.rings));
  clearResults();
  PL.site = null;
  $("#placeRun").disabled = true;
  $("#placeSite").textContent = "Buscando la comuna, la red y los vecinos…";
  const q = new URLSearchParams({ lat: lat.toFixed(5), lon: lon.toFixed(5) });
  fetch(`/api/place/site?${q}`).then((r) => r.json()).then((s) => {
    PL.site = s;
    renderSite(s);
    $("#placeRun").disabled = !s.ok;
    $("#placeNote").textContent = s.ok ? `Corre ${PL.meta.place.n} futuros con y sin tu data center; puede tardar hasta un minuto.` : "Elige otro sitio.";
  }).catch(() => { $("#placeSite").textContent = "No se pudo consultar el sitio. ¿Está corriendo el servidor?"; });
}

function renderSite(s) {
  const el = $("#placeSite");
  if (!s.ok) { el.innerHTML = `<span class="warn">${esc(s.reason)}</span>`; return; }
  const h = s.households;
  const exp = s.node_expansions.map(([d, mw]) => `+${fmt(mw)} MW en ${ymLabel(d)}`).join(", ");
  const dcs = s.near_dc.length
    ? `${s.near_dc.length} data center${s.near_dc.length > 1 ? "s" : ""} real${s.near_dc.length > 1 ? "es" : ""} a menos de 3 km (${fmt(s.near_dc.reduce((a, d) => a + d.it_mw, 0))} MW).`
    : "Ningún data center real a menos de 3 km.";
  el.innerHTML = `<b>${esc(s.commune_name)}</b>${s.inside ? "" : `<br><span class="warn">Fuera de las zonas con hogares del modelo; se conecta como ${esc(s.commune_name)}. Si aquí vive gente de una comuna que no modelamos, no la contamos.</span>`}
    <dl class="site-dl">
      <dt>A menos de 500 m</dt><dd>${fmt(h["0.5"])} hogares</dd>
      <dt>A menos de 3 km</dt><dd>${fmt(h["3.0"])} hogares</dd>
    </dl>
    <p>Red: ${esc(s.node)}${exp ? `; ampliación prevista ${esc(exp)}` : ""}.</p>
    <p>${s.aquifer ? `Agua: ${esc(s.aquifer)}${s.prohibition ? ", en zona de prohibición" : ""}.` : "Sin acuífero sobreexplotado modelado."}</p>
    <p>${dcs}</p>`;
}

// ---------------------------------------------------------------- simular
function formSpec() {
  const f = new FormData($("#placeForm"));
  const ll = PL.marker.getLatLng();
  return { lat: ll.lat, lon: ll.lng, it_mw: Number(f.get("it_mw")), cooling: f.get("cooling"), year: Number(f.get("year")),
    rule: f.get("rule"), hv_line: f.get("hv_line") === "on", grid_priority: f.get("grid_priority") === "on" };
}

async function runPlace() {
  if (!PL.site || !PL.site.ok || PL.busy) return;
  PL.busy = true;
  const btn = $("#placeRun");
  btn.disabled = true;
  PL.marker.dragging.disable();
  const t0 = Date.now();
  const tick = () => { $("#placeNote").textContent = `Simulando ${PL.meta.place.n} futuros con y sin tu data center… ${Math.round((Date.now() - t0) / 1000)} s`; };
  tick();
  PL.timer = setInterval(tick, 1000);
  $("#placeResults").classList.add("loading");
  try {
    const r = await fetch("/api/place", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(formSpec()) });
    const res = await r.json();
    if (!r.ok) throw new Error(res.detail || "error");
    PL.res = res;
    $("#placeNote").textContent = `Listo: ${res.n} futuros, cada uno con y sin tu data center.`;
    showResults();
  } catch (err) {
    $("#placeNote").textContent = `No se pudo simular: ${err.message === "error" ? "intenta de nuevo" : err.message}`;
  } finally {
    clearInterval(PL.timer);
    PL.busy = false;
    btn.disabled = false;
    PL.marker.dragging.enable();
    $("#placeResults").classList.remove("loading");
  }
}

function clearResults() {
  stopPPlay();
  PL.res = null;
  PL.probeLayer.clearLayers();
  PL.dots = [];
  $("#placeOut").hidden = true;
  $("#placeCharts").hidden = true;
  $("#placeKey").hidden = true;
  $("#placeStory").textContent = "Elige cómo es tu data center y simula. Verás cuándo empieza a operar, si va a tribunales y cuántos de sus vecinos se movilizan en contra, comparado con no construirlo.";
  $("#placeWhen").textContent = "Simula para ver a los vecinos en el mapa";
  ["#placePlay", "#placeFrame"].forEach((s) => { $(s).disabled = true; });
  document.querySelector('[data-pview="diff"]').disabled = true;
  $("#placeFrameLabel").textContent = "—";
}

function markStale() {
  $("#placeNote").textContent = "Cambiaste el data center: simula de nuevo para actualizar los resultados.";
}

function showResults() {
  const res = PL.res;
  const P = res.probes;
  PL.probeLayer.clearLayers();
  PL.dots = P.lat.map((la, j) => L.circleMarker([la, P.lon[j]], { renderer: PL.canvas, radius: 3.4, weight: 0.8, color: "#ffffff",
    fillOpacity: 0.95, interactive: false }).addTo(PL.probeLayer));
  // escala del modo cambio: el percentil 95 de los cambios, para que un hogar extremo no apague al resto
  const diffs = [];
  res.p_mob_with.forEach((row, f) => row.forEach((v, j) => { diffs.push(Math.abs(v - res.p_mob_without[f][j]) / 100); }));
  diffs.sort((a, b) => a - b);
  PL.diffMax = Math.max(0.1, diffs[Math.floor(0.95 * (diffs.length - 1))] || 0);
  ["#placePlay", "#placeFrame"].forEach((s) => { $(s).disabled = false; });
  document.querySelector('[data-pview="diff"]').disabled = false;
  $("#placeFrame").max = res.frames.length - 1;
  $("#placeKey").hidden = false;
  $("#placeOut").hidden = false;
  $("#placeCharts").hidden = false;
  $("#placeStory").innerHTML = storyText(res);
  renderFixedBands(res);
  renderCharts();
  renderTable(res);
  $("#placeFoot").textContent = `Valor típico de ${res.n} futuros; cada futuro se corre con y sin tu data center, con los mismos números aleatorios. `
    + `Los ${fmt(res.p_mob_with[0].length)} puntos son hogares de muestra: se ubican según la densidad de población del modelo y siguen sus mismas reglas, pero no cambian los totales de la comuna. `
    + "El modelo no hace crecer ni mudarse a la población, y solo cuenta hogares de las comunas modeladas.";
  if (reduced) { PL.frame = res.frames.length - 1; updateFrame(); } else { PL.frame = 0; startPPlay(); }
  PL.map.fitBounds(PL.rings.getLayers()[1].getBounds(), { padding: [20, 20] });
}

// ---------------------------------------------------------------- texto y cifras
function storyText(res) {
  const s = res.spec; const f = res.facts; const site = res.site;
  const cool = { evaporativo: "enfriado con agua", hibrido: "híbrido", aire: "enfriado por aire" }[s.cooling];
  const route = Object.entries(f.routes).sort((a, b) => b[1] - a[1])[0][0];
  const how = { pertinencia: "por pertinencia, sin participación ciudadana", SEIA: "por el SEIA, con participación ciudadana",
    acumulativa: "en la evaluación conjunta de la zona" }[route] || "";
  let t = `<b>Tu data center de ${fmt(s.it_mw)} MW ${cool} en ${esc(site.commune_name)}</b> se anuncia en enero de ${s.year} y se tramita ${how}.`;
  if (f.p_online >= 0.5) t += ` Empieza a operar hacia ${ymLabel(f.online_p50)}${f.online_p10 !== f.online_p90 ? ` (entre ${ymLabel(f.online_p10)} y ${ymLabel(f.online_p90)})` : ""}.`;
  else if (f.p_online > 0) t += ` Llega a operar antes de 2036 solo en ${pc(f.p_online)} de los futuros.`;
  else t += " No llega a operar antes de 2036 en ningún futuro.";
  if (f.p_waiting_2035 >= 0.2) t += ` En ${pc(f.p_waiting_2035)} todavía espera conexión a la red a fines de 2035.`;
  if (f.p_sued >= 0.05) t += ` Los vecinos lo llevan a tribunales en ${pc(f.p_sued)} de los futuros${f.p_annulled >= 0.05 ? ` y el permiso se anula en ${pc(f.p_annulled)}` : ""}.`;
  else t += " Casi nunca llega a tribunales.";
  if (f.p_redesign_air >= 0.1) t += ` En ${pc(f.p_redesign_air)} termina rediseñado para enfriar por aire.`;
  if (f.p_cancel >= 0.1) t += ` La empresa desiste en ${pc(f.p_cancel)}.`;
  return t;
}

function setBand(k, val, note, delta) {
  const b = document.querySelector(`[data-pk="${k}"]`);
  b.querySelector(".val").textContent = val;
  b.querySelector("[data-pnote]").textContent = note;
  if (delta !== undefined) b.querySelector(".delta").innerHTML = delta;
}

function renderFixedBands(res) {
  const f = res.facts; const o = res.if_operating; const y = res.y2035;
  setBand("online", pc(f.p_online), f.p_online > 0
    ? `de los futuros; fecha típica ${ymLabel(f.online_p50)}${f.p_waiting_2035 >= 0.05 ? `. Sigue esperando red en ${pc(f.p_waiting_2035)}` : ""}`
    : `de los futuros${f.p_waiting_2035 > 0 ? `; espera red en ${pc(f.p_waiting_2035)}` : ""}`);
  setBand("sued", pc(f.p_sued), `de los futuros; el permiso se anula en ${pc(f.p_annulled)}`);
  if (o) {
    const dd = o.aq_drawdown_m;
    setBand("water", `${fmt(o.wls, o.wls < 10 ? 1 : 0)} L/s`, `el agua de ${fmt(o.wls * 86400 / 500)} hogares en 2035${dd > 0.005 ? `; el acuífero baja ${fmt(dd, 2)} m más` : ""}`);
    setBand("money", `US$ ${fmt(o.muni_usd_hh)}`, `por hogar de ${res.site.commune_name} al año; ${fmt(o.jobs_local)} empleos para vecinos`);
  } else {
    setBand("water", "—", "no opera en ningún futuro antes de 2036");
    setBand("money", "—", "no opera en ningún futuro antes de 2036");
  }
  const lost = Math.max(0, -y.others_mw.p50);
  const lit = y.others_lit.p50;
  setBand("others", `${fmt(lost)} MW`, `en 2035, porque tu data center ocupa red o enciende la oposición${lit >= 1 ? `; ${fmt(lit)} juicio${lit >= 2 ? "s" : ""} más contra otros` : ""}`);
}

function updateMobBand() {
  const res = PL.res; const f = PL.frame; const tot = res.households_followed || 1;
  const w = res.mob_with.p50[f] / tot; const wo = res.mob_without.p50[f] / tot;
  const d = res.mob_with.p50[f] - res.mob_without.p50[f];  // igual a la distancia entre las líneas
  const pts = (100 * d) / tot;
  const delta = Math.abs(pts) < 0.5 ? "igual que sin tu data center"
    : `<b>${pts > 0 ? "peor" : "mejor"}</b> · ${fmt(Math.abs(pts), Math.abs(pts) < 10 ? 1 : 0)} puntos ${pts > 0 ? "más" : "menos"} que sin él (${fmt(Math.abs(d))} hogares)`;
  setBand("mob", pc(w), `de ${fmt(tot)} hogares a menos de 3 km, ${ymLabel(res.frames[f])}; sin tu data center ${pc(wo)}`, delta);
}

// ---------------------------------------------------------------- mapa: cuadro a cuadro
function setPView(v) {
  PL.view = v;
  document.querySelectorAll("[data-pview]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.pview === v)));
  if (PL.res) updateFrame();
}
function startPPlay() {
  if (!PL.res) return;
  if (PL.frame >= PL.res.frames.length - 1) PL.frame = 0;
  $("#placePlay").textContent = "Pausar";
  PL.playing = setInterval(() => {
    PL.frame += 1;
    if (PL.frame >= PL.res.frames.length - 1) { PL.frame = PL.res.frames.length - 1; stopPPlay(); }
    updateFrame();
  }, 260);
  updateFrame();
}
function stopPPlay() {
  if (PL.playing) clearInterval(PL.playing);
  PL.playing = null;
  $("#placePlay").textContent = "Ver desde 2026";
}

function updateFrame() {
  const res = PL.res;
  if (!res) return;
  const f = PL.frame;
  $("#placeFrame").value = f;
  $("#placeFrameLabel").textContent = ymLabel(res.frames[f]);
  const diff = PL.view === "diff";
  const W = res.p_mob_with[f]; const WO = res.p_mob_without[f];
  const stops = METRICS.c_conflict.ramp;
  PL.dots.forEach((m, j) => {
    let fill;
    if (diff) {
      const t = (W[j] - WO[j]) / 100 / PL.diffMax;
      const a = Math.min(1, Math.abs(t)) ** 0.7;
      fill = t < 0 ? mix(MID, BETTER, a) : mix(MID, WORSE, a);
    } else {
      fill = ramp(0.06 + 0.94 * W[j] / 100, stops);
    }
    m.setStyle({ fillColor: fill });
  });
  const sp = res.status_prob[f];
  let mode = 0;
  sp.forEach((v, k) => { if (v > sp[mode]) mode = k; });
  const lab = mode === ST.NONE ? "todavía no se anuncia" : `${PL.meta.status_labels[mode]} en ${pc(sp[mode])} de los futuros`;
  $("#placeWhen").textContent = `${ymLabel(res.frames[f])} · Tu data center: ${lab}`;
  PL.marker.setTooltipContent(`<b>Tu data center</b> · ${ymLabel(res.frames[f])}<br>${PSTATUS.filter((s) => sp[s.k] >= 0.05).map((s) => `${s.label}: ${pc(sp[s.k])}`).join("<br>") || "Aún no se anuncia"}`);
  renderPKey(diff);
  updateMobBand();
  moveCursors();
}

function renderPKey(diff) {
  const el = $("#placeKey");
  if (diff) {
    const blocks = [-1, -0.66, -0.33, 0, 0.33, 0.66, 1].map((t) => `<b style="background:${t < 0 ? mix(MID, BETTER, Math.abs(t) ** 0.7) : mix(MID, WORSE, t ** 0.7)}"></b>`).join("");
    el.innerHTML = `<p class="key-title">Cambio por tu data center</p><div class="key-ramp">${blocks}</div>
      <div class="key-labels"><span>menos</span><span>igual</span><span>más</span></div>
      <p class="key-hint">Cada punto es un hogar de muestra. El color más fuerte son ${fmt(100 * PL.diffMax)} puntos más de futuros en que se moviliza.</p>`;
  } else {
    const blocks = [0, 0.17, 0.33, 0.5, 0.67, 0.83, 1].map((t) => `<b style="background:${ramp(0.06 + 0.94 * t, METRICS.c_conflict.ramp)}"></b>`).join("");
    el.innerHTML = `<p class="key-title">Hogares movilizados en contra</p><div class="key-ramp">${blocks}</div>
      <div class="key-labels"><span>0%</span><span>100% de los futuros</span></div>
      <p class="key-hint">Cada punto es un hogar de muestra. Más oscuro: se moviliza en más futuros.</p>`;
  }
}

// ---------------------------------------------------------------- gráficos (SVG)
function el(tag, attrs = {}, parent) {
  const n = document.createElementNS(SVGNS, tag);
  Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
  if (parent) parent.appendChild(n);
  return n;
}
function txt(parent, x, y, s, attrs = {}) {
  const t = el("text", { x, y, ...attrs }, parent);
  t.textContent = s;
  return t;
}

function frame2(plot, h, m) {  // svg, escala x por cuadro, ejes y tooltip
  const res = PL.res;
  const wpx = plot.clientWidth || 400;
  plot.replaceChildren();
  const svg = el("svg", { viewBox: `0 0 ${wpx} ${h}`, width: wpx, height: h, role: "img" }, plot);
  const iw = wpx - m.l - m.r; const ih = h - m.t - m.b;
  const n = res.frames.length;
  const x = (i) => m.l + (iw * (i + 0.5)) / n;
  const tip = document.createElement("div");
  tip.className = "ptip";
  tip.hidden = true;
  plot.appendChild(tip);
  // años en el eje x: enero de cada año (cada 2 si no cabe)
  const step = iw / n * 4 < 34 ? 8 : 4;
  res.frames.forEach((s, i) => {
    if (!s.endsWith("-01")) return;
    const yv = Number(s.slice(0, 4));
    if (step === 8 && yv % 2) return;
    txt(svg, x(i), h - 6, String(yv), { class: "ax", "text-anchor": "middle" });
  });
  return { svg, x, iw, ih, n, tip, wpx };
}

function hover(plot, g, m, h, onMove) {
  const hit = el("rect", { x: m.l, y: 0, width: g.iw, height: h - m.b, fill: "transparent" }, g.svg);
  const line = el("line", { y1: m.t, y2: h - m.b, class: "xhair" }, g.svg);
  line.style.display = "none";
  const pick = (ev) => {
    const r = g.svg.getBoundingClientRect();
    const px = (ev.clientX - r.left) * (g.wpx / r.width);
    return Math.max(0, Math.min(g.n - 1, Math.floor(((px - m.l) / g.iw) * g.n)));
  };
  hit.addEventListener("pointermove", (ev) => {
    const i = pick(ev);
    line.setAttribute("x1", g.x(i)); line.setAttribute("x2", g.x(i));
    line.style.display = "";
    onMove(i);
    g.tip.hidden = false;
    const left = (g.x(i) / g.wpx) * plot.clientWidth;
    g.tip.style.left = `${Math.min(plot.clientWidth - g.tip.offsetWidth - 4, Math.max(4, left + 12))}px`;
  });
  hit.addEventListener("pointerleave", () => { line.style.display = "none"; g.tip.hidden = true; });
  hit.addEventListener("click", (ev) => { stopPPlay(); PL.frame = pick(ev); updateFrame(); });
}

function tipRows(title, rows) {  // valores primero, nombres después; claves de línea
  return `<p class="ptip-t">${esc(title)}</p>${rows.map(([c, v, name]) => `<p><i style="background:${c}"></i><b>${esc(v)}</b> ${esc(name)}</p>`).join("")}`;
}

function renderCharts() {
  if (!PL.res) return;
  renderMobChart();
  renderStatusChart();
  moveCursors();
}

function renderMobChart() {
  const res = PL.res; const tot = res.households_followed || 1;
  const plot = $("#chartMob .pchart-plot");
  const h = 210; const m = { l: 40, r: 74, t: 10, b: 24 };
  const g = frame2(plot, h, m);
  const y = (v) => m.t + g.ih * (1 - v);
  [0, 0.25, 0.5, 0.75, 1].forEach((v) => {
    el("line", { x1: m.l, x2: m.l + g.iw, y1: y(v), y2: y(v), class: "grid" }, g.svg);
    txt(g.svg, m.l - 6, y(v) + 4, `${fmt(100 * v)}%`, { class: "ax", "text-anchor": "end" });
  });
  const W = res.mob_with; const WO = res.mob_without;
  const pts = (arr) => arr.map((v, i) => `${g.x(i).toFixed(1)},${y(v / tot).toFixed(1)}`).join(" ");
  const band = `${pts(W.p95)} ${W.p5.map((v, i) => [i, v]).reverse().map(([i, v]) => `${g.x(i).toFixed(1)},${y(v / tot).toFixed(1)}`).join(" ")}`;
  el("polygon", { points: band, fill: PCOL.with, "fill-opacity": 0.1 }, g.svg);
  el("polyline", { points: pts(WO.p50), class: "ln", stroke: PCOL.without }, g.svg);
  el("polyline", { points: pts(W.p50), class: "ln", stroke: PCOL.with }, g.svg);
  // etiquetas directas al final, solo si no chocan
  const last = g.n - 1;
  const ya = y(W.p50[last] / tot); const yb = y(WO.p50[last] / tot);
  if (Math.abs(ya - yb) >= 14) {
    txt(g.svg, g.x(last) + 8, ya + 4, `Con ${pc(W.p50[last] / tot)}`, { class: "lab" });
    txt(g.svg, g.x(last) + 8, yb + 4, `Sin ${pc(WO.p50[last] / tot)}`, { class: "lab" });
  }
  PL.cMob = { g, y, tot, cur: el("line", { y1: m.t, y2: h - m.b, class: "cur" }, g.svg),
    da: el("circle", { r: 4, fill: PCOL.with, class: "dot" }, g.svg), db: el("circle", { r: 4, fill: PCOL.without, class: "dot" }, g.svg) };
  hover(plot, g, m, h, (i) => {
    g.tip.innerHTML = tipRows(ymLabel(res.frames[i]), [
      [PCOL.with, pc(W.p50[i] / tot), `con tu data center (rango ${pc(W.p5[i] / tot)} a ${pc(W.p95[i] / tot)})`],
      [PCOL.without, pc(WO.p50[i] / tot), "sin él"]]);
  });
}

function renderStatusChart() {
  const res = PL.res;
  const plot = $("#chartStatus .pchart-plot");
  $("#statusKey").innerHTML = PSTATUS.map((s) => `<li><i class="sq" style="--c:${s.c}"></i>${esc(s.label)}</li>`).join("");
  const h = 180; const m = { l: 40, r: 10, t: 8, b: 24 };
  const g = frame2(plot, h, m);
  const y = (v) => m.t + g.ih * (1 - v);
  [0, 0.5, 1].forEach((v) => {
    el("line", { x1: m.l, x2: m.l + g.iw, y1: y(v), y2: y(v), class: "grid" }, g.svg);
    txt(g.svg, m.l - 6, y(v) + 4, `${fmt(100 * v)}%`, { class: "ax", "text-anchor": "end" });
  });
  const bw = Math.min(24, g.iw / g.n - 2);
  const cols = el("g", {}, g.svg);
  res.status_prob.forEach((sp, i) => {
    let acc = 0;
    PSTATUS.forEach((s) => {
      const v = sp[s.k];
      if (v <= 0.001) return;
      const top = y(acc + v); const bot = y(acc);
      const hh = Math.max(0, bot - top - (acc > 0 ? 2 : 0));  // 2px de separación entre segmentos
      if (hh > 0) el("rect", { x: g.x(i) - bw / 2, y: top, width: bw, height: hh, fill: s.c }, cols);
      acc += v;
    });
  });
  PL.cSt = { g, cur: el("line", { y1: m.t, y2: h - m.b, class: "cur" }, g.svg) };
  hover(plot, g, m, h, (i) => {
    const sp = res.status_prob[i];
    const rows = PSTATUS.slice().reverse().filter((s) => sp[s.k] >= 0.005).map((s) => [s.c, pc(sp[s.k]), s.label]);
    g.tip.innerHTML = tipRows(ymLabel(res.frames[i]), rows.length ? rows : [["transparent", "100%", "todavía no se anuncia"]]);
  });
}

function moveCursors() {
  const f = PL.frame;
  if (PL.cMob) {
    const { g, y, tot, cur, da, db } = PL.cMob;
    const x = g.x(f);
    cur.setAttribute("x1", x); cur.setAttribute("x2", x);
    da.setAttribute("cx", x); da.setAttribute("cy", y(PL.res.mob_with.p50[f] / tot));
    db.setAttribute("cx", x); db.setAttribute("cy", y(PL.res.mob_without.p50[f] / tot));
  }
  if (PL.cSt) { const x = PL.cSt.g.x(f); PL.cSt.cur.setAttribute("x1", x); PL.cSt.cur.setAttribute("x2", x); }
}

function renderTable(res) {
  const tot = res.households_followed || 1;
  const rows = res.frames.map((s, i) => [s, i]).filter(([s]) => s.endsWith("-10"));
  $("#placeTable").innerHTML = `<table class="data"><thead><tr><th>Fecha</th><th>Movilizados con tu data center</th><th>Sin él</th>${
    PSTATUS.map((s) => `<th>${esc(s.label)}</th>`).join("")}</tr></thead><tbody>${
    rows.map(([s, i]) => `<tr><td>${ymLabel(s)}</td><td>${pc(res.mob_with.p50[i] / tot)}</td><td>${pc(res.mob_without.p50[i] / tot)}</td>${
      PSTATUS.map((st) => `<td>${pc(res.status_prob[i][st.k])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}
