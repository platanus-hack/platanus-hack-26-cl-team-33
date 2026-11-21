/* Aterriza: una sola página. Elegir una regla cambia las seis cifras y el mapa. */
"use strict";
document.documentElement.classList.add("js");

const $ = (s, el = document) => el.querySelector(s);
const nf = (d = 0) => new Intl.NumberFormat("es-CL", { maximumFractionDigits: d, minimumFractionDigits: d });
const fmt = (x, d = 0) => nf(d).format(x);
const money = (musd) => (musd >= 1000 ? `US$ ${fmt(musd / 1000, 1)} mil millones` : `US$ ${fmt(musd)} millones`);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
// valor de un supuesto sin perder cifras (0,004 no es 0; 0,995 no es 0,99). Parte de los decimales
// de siempre (2 bajo 1, 1 bajo 10, 0 sobre eso) y agrega los que falten; min = 0 para texto corrido
function num(x, min) {
  const ax = Math.abs(x);
  const lo = min ?? (ax < 1 && x !== 0 ? 2 : ax < 10 ? 1 : 0);
  let d = lo;
  while (d < 6 && Math.abs(Math.round(x * 10 ** d) / 10 ** d - x) > 1e-9 * Math.max(1, ax)) d += 1;
  return new Intl.NumberFormat("es-CL", { minimumFractionDigits: lo, maximumFractionDigits: d }).format(x).replace("-", "−");
}
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const Y0 = 2012;
const yi = (y) => y - Y0;
const ST = { NONE: 0, PERMIT: 1, WAIT: 2, LITIG: 3, BUILD: 4, OPER: 5, CANCEL: 6 };
const DC_INK = "#262b33";

// cifra -> cómo mostrarla y si "más" es mejor (null = ni mejor ni peor)
const BANDS = {
  it_chile: { show: (v) => `${fmt(v)} MW`, goodUp: null,
    note: (vals) => `≈ ${fmt(100 * vals.dc_share_national, 1)}% de la electricidad de Chile` },
  water_ls_rm: { show: (v) => `${fmt(v)} L/s`, goodUp: false,
    note: (vals) => `el agua de ${fmt(vals.water_ls_rm * 86400 / 500)} hogares` },
  conflict_rm: { show: (v) => `${fmt(100 * v)}%`, goodUp: false, points: true, scale: 100 },
  litigations: { show: (v) => fmt(v), goodUp: false },
  invest_lost: { show: money, goodUp: false },
  bill_pct: { show: (v) => `+${fmt(v, 1)}%`, goodUp: false, points: true, scale: 1,
    note: (vals, r) => (r ? `respecto de 2025 · en 9 de cada 10 futuros, entre +${fmt(r[0], 1)}% y +${fmt(r[1], 1)}%` : "respecto de 2025") },
};
const KEYS = ["it_chile", "dc_share_national", "water_ls_rm", "conflict_rm", "litigations", "invest_lost", "bill_pct"];
// Cada capa tiene su propio tono (validado contra daltonismo): naranjo = conflicto, azul = agua,
// magenta = data centers. En "cambio vs como hoy": verde = mejor, naranjo rojizo = peor.
const BETTER = "#14866d";
const WORSE = "#d8461b";
const LESS_NEUTRAL = "#6b7c99";
const METRICS = {
  c_conflict: { label: "Vecinos movilizados", unit: "%", scale: 100, d: 0,
    ramp: ["#fdece3", "#fbcfb6", "#f6a984", "#ef8356", "#e0622a", "#b8481a", "#86310d"],
    hint: "Más oscuro: más hogares dispuestos a oponerse.", good: "down" },
  c_water_ls: { label: "Agua que usan los data centers", unit: "L/s", scale: 1, d: 1,
    ramp: ["#e4eefb", "#bdd6f6", "#8fb9ef", "#5c98e2", "#2a78d6", "#1d5daf", "#133f7c"],
    hint: "Más oscuro: más agua.", good: "down" },
  c_it: { label: "Data centers operando", unit: "MW", scale: 1, d: 0,
    ramp: ["#f8e6f1", "#efc3dd", "#e099c4", "#cc6aa8", "#b03c8e", "#8a2b6f", "#5f1c4c"],
    hint: "Más oscuro: más MW de data centers.", good: null },
};

// customBase: seguir como hoy en los mismos futuros que tu regla; fuera de S.ens para no mover la escala
const S = { story: null, meta: null, ens: {}, current: "status_quo", year: 2035, metric: "c_conflict",
  view: "value", playing: null, customValues: null, customText: "", editing: false, customBase: null };
const FOOT = $("#simFoot").textContent;  // nota de las reglas fijas: 200 futuros por regla
// al elegir una regla, el mapa muestra la capa donde esa regla más se nota
const RULE_METRIC = { mesa: "c_it", aire: "c_water_ls", acumulativa: "c_conflict", norte: "c_it",
  paquete: "c_conflict", custom: "c_conflict" };
const MID = "#dfe2e7";

// ---------------------------------------------------------------- arranque
Promise.all([fetch("/api/story").then((r) => r.json()), fetch("/api/meta").then((r) => r.json())])
  .then(([story, meta]) => {
    S.story = story;
    S.meta = meta;
    S.noteText = `Corre ${story.n_custom || 100} futuros; puede tardar hasta un minuto.`;
    $("#customNote").textContent = S.noteText;
    document.querySelectorAll("[data-n-custom]").forEach((el) => { el.textContent = fmt(story.n_custom || 100); });
    // cuántos supuestos se sortean en cada futuro y cuántos quedan fijos (los que prueba «Qué tan firmes»)
    const sampled = meta.params.filter((p) => p.sample).length;
    const fill = (sel, v) => document.querySelectorAll(sel).forEach((el) => { el.textContent = fmt(v); });
    fill("[data-n-params]", meta.params.length);
    fill("[data-n-sampled]", sampled);
    fill("[data-n-fixed]", meta.params.length - sampled);
    renderNumbers(false);
    fillFindings();
    fillProof();
    Object.keys(lazy).forEach((id) => loadLazy(document.getElementById(id)));  // abiertos antes de que llegaran los datos
    initMap();
    if (typeof initPlace === "function") initPlace(meta);
    loadEnsemble("status_quo").then(() => {
      updateMap();
      // el resto de las reglas en segundo plano: el mapa usa una sola escala de colores para todas
      Promise.all(story.tabs.map((t) => loadEnsemble(t.id).catch(() => null))).then(updateMap);
    });
  })
  .catch(() => { $("[data-note]").textContent = "No se pudo cargar la simulación. ¿Está corriendo el servidor?"; });

function loadEnsemble(id) {
  if (S.ens[id]) return Promise.resolve(S.ens[id]);
  return fetch(`/api/scenario/${id}`).then((r) => r.json()).then((d) => { S.ens[id] = d; return d; });
}

// tu regla corre menos futuros que las reglas fijas: se compara con seguir como hoy en esos mismos
// futuros (mismas semillas), no con los 200. Se pide una sola vez.
let customBaseReq = null;
function loadCustomBase() {
  if (!customBaseReq) {
    customBaseReq = fetch("/api/baseline")
      .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .then((d) => { S.customBase = d; return d; })
      .catch((e) => { customBaseReq = null; throw e; });
  }
  return customBaseReq;
}
// con qué se compara la regla elegida en el mapa y en el detalle de cada comuna
function baseEns() {
  if (S.current !== "custom") return S.ens.status_quo;
  const b = S.customBase;  // solo si son los mismos futuros que tu regla
  return b && S.ens.custom && b.meta.n === S.ens.custom.meta.n ? b : null;
}

// ---------------------------------------------------------------- reglas
const tabs = [...document.querySelectorAll("#tabs [role=tab]")];
tabs.forEach((b) => {
  b.addEventListener("click", () => select(b.dataset.id));
  b.addEventListener("keydown", (e) => {
    const i = tabs.indexOf(b);
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const t = tabs[(i + step + tabs.length) % tabs.length];
    t.focus();
    select(t.dataset.id);
  });
});
document.querySelectorAll("[data-tab]").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault();
  select(a.dataset.tab);
  $("#simular").scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
}));

function select(id) {
  S.current = id;
  tabs.forEach((b) => {
    const on = b.dataset.id === id;
    b.setAttribute("aria-selected", String(on));
    b.tabIndex = on ? 0 : -1;
  });
  const custom = id === "custom";
  if (id === "status_quo") setView("value", false);
  else { setView("diff", false); if (RULE_METRIC[id]) setMetric(RULE_METRIC[id], false); }
  const showForm = custom && (!S.customValues || S.editing);
  $("#custom").hidden = !showForm;
  $("#bands").hidden = showForm;
  if (!S.story) return;
  renderNumbers(true);
  if (custom && !S.ens.custom) { $("#mapWhen").textContent = "Simula tu regla para verla en el mapa"; return; }
  Promise.all([loadEnsemble(id), custom ? loadCustomBase().catch(() => null) : null]).then(updateMap).catch(() => {});
}

function rangeFor(id, k) {  // [p5, p95] de una cifra en 2035
  if (id === "custom") { const s = S.ens.custom && S.ens.custom.series[k]; return s ? [s.p5[yi(2035)], s.p95[yi(2035)]] : null; }
  const tab = S.story.tabs.find((t) => t.id === id);
  return tab && tab.values[k] ? [tab.values[k].p5, tab.values[k].p95] : null;
}

function valuesFor(id) {
  if (id === "custom") return S.customValues;
  const tab = S.story.tabs.find((t) => t.id === id);
  return Object.fromEntries(KEYS.map((k) => [k, tab.values[k].p50]));
}

function renderNumbers(animate) {
  const id = S.current;
  const mine = id === "custom" ? S.ens.custom : null;  // tu regla trae seguir como hoy en sus mismos futuros
  const base = mine ? mine.baseline.values : valuesFor("status_quo");
  let summary;
  if (id === "custom") {
    summary = S.customValues && !S.editing
      ? `<b>Tu regla:</b> ${esc(S.customText)}. <button type="button" class="inline-link" id="editRule">Cambiarla</button>`
      : "Elige cada palanca y simula. El resultado se compara con seguir como hoy en los mismos futuros.";
  } else {
    const tab = S.story.tabs.find((t) => t.id === id);
    summary = esc(tab.summary);
    if (id === "status_quo") summary += " Es el punto de comparación de las otras reglas.";
    if (id === "paquete") {
      const f = (S.story.findings || []).find((x) => x.id === "paquete");
      if (f) summary += ` <b>Mejora a la vez agua, vecinos movilizados, juicios e inversión en ${esc(f.stat)} de los futuros.</b>`;
    }
  }
  $("#ruleSummary").innerHTML = summary;
  const n = fmt(mine ? mine.baseline.n : S.story.n_custom || 100);
  $("#simFoot").textContent = id === "custom"
    ? `Cifras para 2035: valor típico de ${n} futuros simulados con tu regla, comparados con seguir como hoy en esos mismos ${n} futuros. La historia hasta noviembre de 2026 es la real.`
    : FOOT;
  const edit = $("#editRule");
  if (edit) edit.addEventListener("click", () => { S.editing = true; select("custom"); });
  const vals = valuesFor(id);
  if (!vals || (id === "custom" && S.editing)) return;
  document.querySelectorAll("#bands .band").forEach((band) => {
    const k = band.dataset.k;
    const spec = BANDS[k];
    const val = band.querySelector(".val");
    val.textContent = spec.show(vals[k]);
    if (animate && !reduced) { val.classList.remove("tick"); void val.offsetWidth; val.classList.add("tick"); }
    if (spec.note) band.querySelector(".note").textContent = spec.note(vals, rangeFor(id, k));
    band.querySelector(".delta").innerHTML = id === "status_quo" ? "" : delta(spec, vals[k], base[k], mine && mine.compare[k]);
  });
}

function delta(spec, v, b, c) {  // c: conteo futuro a futuro, solo para tu regla
  const up = v > b;
  const rel = b ? Math.abs(v - b) / Math.abs(b) : 0;
  const diff = Math.abs(v - b) * (spec.scale || 1);
  if ((spec.points && diff < 0.1) || (!spec.points && rel < 0.02)) return "igual que seguir como hoy";
  const amount = spec.points ? `${fmt(diff, diff < 10 ? 1 : 0)} puntos` : `${fmt(rel * 100)}%`;
  const verdict = spec.goodUp === null ? "" : (up === spec.goodUp ? "<b>mejor</b> · " : "<b>peor</b> · ");
  return `${verdict}${amount} ${up ? "más" : "menos"} que seguir como hoy${c ? ` · ${inFutures(c, up, spec.goodUp)}` : ""}`;
}

// en cuántos de los mismos futuros tu regla mueve la cifra hacia ese lado, y qué pasa en el resto
function inFutures(c, up, goodUp) {
  const [rise, fall] = goodUp === null ? [c.more, c.less] : goodUp ? [c.better, c.worse] : [c.worse, c.better];
  const [agree, against] = up ? [rise, fall] : [fall, rise];
  if (agree === c.n) return `en los ${fmt(c.n)} futuros`;
  const other = goodUp === null ? (up ? "menos" : "más") : (up === goodUp ? "peor" : "mejor");
  return `en ${fmt(agree)} de ${fmt(c.n)} futuros; ${against ? `${other} en ${fmt(against)}` : "igual en el resto"}`;
}

// ---------------------------------------------------------------- tu regla
$("#custom").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const pol = {
    fuel_threshold_t: Number(f.get("fuel_threshold_t")),
    permit_speed: Number(f.get("permit_speed")),
    north_incentive: Number(f.get("north_incentive")),
    community_fund_usd_mw: Number(f.get("community_fund_usd_mw")),
    demand: f.get("demand"),
    cumulative: f.get("cumulative") === "on",
    water_cap_ls: f.get("cumulative") === "on" ? 60 : null,
    air_cooling_rm: f.get("air_cooling_rm") === "on",
    transparency: f.get("transparency") === "on",
  };
  const btn = $("#runCustom");
  btn.disabled = true;
  $("#customNote").textContent = `Simulando ${S.story.n_custom || 100} futuros…`;
  loadCustomBase().catch(() => {});  // para el mapa, mientras se simula
  try {
    const r = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy: pol }) });
    if (!r.ok) throw new Error(r.statusText);
    const res = await r.json();
    S.customValues = Object.fromEntries(KEYS.map((k) => [k, res.series[k].p50[yi(2035)]]));
    S.ens.custom = res;
    S.customText = describe(pol);
    S.editing = false;
    $("#customNote").textContent = S.noteText;
    select("custom");
  } catch {
    $("#customNote").textContent = "No se pudo simular. Intenta de nuevo.";
  } finally {
    btn.disabled = false;
  }
});

function describe(p) {
  const parts = [];
  if (p.fuel_threshold_t !== 1000) parts.push(`umbral de ${fmt(p.fuel_threshold_t)} t`);
  if (p.permit_speed !== 1) parts.push(p.permit_speed < 1 ? "permisos en la mitad del tiempo" : "permisos 50% más largos");
  if (p.cumulative) parts.push("evaluación en conjunto");
  if (p.air_cooling_rm) parts.push("solo aire en Santiago");
  if (p.north_incentive) parts.push(p.north_incentive >= 1 ? "incentivo fuerte al norte" : "incentivo medio al norte");
  if (p.community_fund_usd_mw) parts.push(`fondo de US$${fmt(p.community_fund_usd_mw)} por MW`);
  if (p.transparency) parts.push("uso de agua público");
  if (p.demand !== "base") parts.push(p.demand === "alta" ? "10 proyectos al año" : "2 proyectos al año");
  return parts.length ? parts.join(", ") : "igual que hoy";
}

// ---------------------------------------------------------------- mapa
let map; let communeLayer; let dcLayer;

function initMap() {
  map = L.map("map", { scrollWheelZoom: false, zoomControl: false }).setView([-33.45, -70.73], 10);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  const key = L.control({ position: "topleft" });
  key.onAdd = () => {
    const d = L.DomUtil.create("div", "map-key");
    d.id = "mapKey";
    L.DomEvent.disableClickPropagation(d);
    return d;
  };
  key.addTo(map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 17, className: "base-tiles",
  }).addTo(map);
  communeLayer = L.layerGroup().addTo(map);
  dcLayer = L.layerGroup().addTo(map);
  const places = L.control({ position: "bottomleft" });
  places.onAdd = () => {
    const d = L.DomUtil.create("div", "places");
    d.innerHTML = [["Santiago", -33.45, -70.73, 10], ["Valparaíso", -33.08, -71.58, 11], ["Antofagasta", -23.62, -70.38, 11]]
      .map(([n, la, lo, z]) => `<button type="button" data-v="${la},${lo},${z}">${n}</button>`).join("");
    d.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const [la, lo, z] = b.dataset.v.split(",").map(Number);
      map.setView([la, lo], z);
    }));
    L.DomEvent.disableClickPropagation(d);
    return d;
  };
  places.addTo(map);
}

document.querySelectorAll(".seg [data-metric]").forEach((b) => b.addEventListener("click", () => setMetric(b.dataset.metric)));
document.querySelectorAll(".band[data-metric]").forEach((b) => {
  b.tabIndex = 0;
  b.title = "Ver esta cifra por comuna en el mapa";
  const go = () => setMetric(b.dataset.metric);
  b.addEventListener("click", go);
  b.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
});
function setMetric(m, redraw = true) {
  S.metric = m;
  document.querySelectorAll(".seg [data-metric]").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.metric === m)));
  document.querySelectorAll(".band[data-metric]").forEach((x) => x.classList.toggle("on", x.dataset.metric === m));
  document.documentElement.style.setProperty("--layer", METRICS[m].ramp[4]);
  if (redraw) updateMap();
}
function setView(v, redraw = true) {
  S.view = S.current === "status_quo" ? "value" : v;
  document.querySelectorAll(".seg [data-view]").forEach((x) => {
    x.setAttribute("aria-pressed", String(x.dataset.view === S.view));
    if (x.dataset.view === "diff") x.disabled = S.current === "status_quo";
  });
  if (redraw) updateMap();
}
document.querySelectorAll(".seg [data-view]").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
setMetric("c_conflict", false);
setView("value", false);

const yearInput = $("#year");
yearInput.addEventListener("input", () => { stopPlay(); S.year = Number(yearInput.value); updateMap(); });
$("#play").addEventListener("click", () => {
  if (S.playing) { stopPlay(); return; }
  if (S.year >= 2035) S.year = 2012;
  $("#play").textContent = "Pausar";
  S.playing = setInterval(() => {
    S.year += 1;
    if (S.year >= 2035) { S.year = 2035; stopPlay(); }
    updateMap();
  }, reduced ? 250 : 480);
  updateMap();
});
function stopPlay() {
  if (S.playing) clearInterval(S.playing);
  S.playing = null;
  $("#play").textContent = "Ver desde 2012";
}

function metricMax(m) {
  let max = 0;
  Object.values(S.ens).forEach((res) => res.communes[m].p50.forEach((row) => row.forEach((v) => { max = Math.max(max, v); })));
  return max * METRICS[m].scale || 1;
}
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
function mix(a, b, t) {
  const [x, y] = [hex(a), hex(b)];
  return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * t)).join(",")})`;
}
function ramp(t, stops = METRICS[S.metric].ramp) {  // secuencial continua: un tono, de claro a oscuro
  const n = stops.length - 1;
  const p = Math.max(0, Math.min(1, t)) * n;
  const i = Math.min(n - 1, Math.floor(p));
  return mix(stops[i], stops[i + 1], p - i);
}
function poles(m = METRICS[S.metric]) {  // [color si baja, color si sube] respecto de seguir como hoy
  if (m.good === "down") return [BETTER, WORSE];
  return [LESS_NEUTRAL, m.ramp[4]];
}
function diverge(t) {  // divergente: gris = igual que como hoy; los extremos según poles()
  const a = Math.min(1, Math.abs(t)) ** 0.7;
  const [lo, hi] = poles();
  return t < 0 ? mix(MID, lo, a) : mix(MID, hi, a);
}
function diffMax(m) {  // escala del modo cambio: el mayor cambio de la regla elegida (todas las comunas y años)
  const base = baseEns();
  const res = S.ens[S.current];
  let max = 0;
  if (!base || !res) return 1;
  res.communes[m].p50.forEach((row, i) => row.forEach((v, y) => { max = Math.max(max, Math.abs(v - base.communes[m].p50[i][y])); }));
  return max * METRICS[m].scale || 1;
}
function dcStyle(code, mw) {
  const r = 3 + 1.0 * Math.sqrt(mw);
  if (code === ST.OPER) return { radius: r, color: "#ffffff", weight: 1.5, fillColor: DC_INK, fillOpacity: 0.6 };
  if (code === ST.BUILD) return { radius: r, color: DC_INK, weight: 2.5, fillColor: DC_INK, fillOpacity: 0.15 };
  if (code === ST.PERMIT) return { radius: r, color: DC_INK, weight: 2, fillOpacity: 0 };
  if (code === ST.WAIT) return { radius: r, color: "#5d6470", weight: 2.5, dashArray: "1 5", lineCap: "round", fillOpacity: 0 };
  if (code === ST.LITIG) return { radius: r, color: "#c4152b", weight: 3, fillColor: "#ffffff", fillOpacity: 0.55 };
  return null;
}

function renderKey(m, max, diff) {
  const el = $("#mapKey");
  if (!el) return;
  const unit = (v) => `${fmt(v, m.d)} ${m.unit}`;
  if (diff) {
    const [lo, hi] = poles(m);
    const blocks = [-1, -0.66, -0.33, 0, 0.33, 0.66, 1].map((t) => `<b style="background:${t < 0 ? mix(MID, lo, Math.abs(t) ** 0.7) : mix(MID, hi, t ** 0.7)}"></b>`).join("");
    const [lw, hw] = m.good === "down" ? ["mejor", "peor"] : ["menos", "más"];
    el.innerHTML = `<p class="key-title">${esc(m.label)}: cambio vs seguir como hoy</p>
      <div class="key-ramp">${blocks}</div>
      <div class="key-labels"><span>${lw}</span><span>igual</span><span>${hw}</span></div>
      <p class="key-hint">Cada círculo es una comuna. El color más fuerte es un cambio de ${unit(max)}.</p>`;
  } else {
    const blocks = [0, 0.17, 0.33, 0.5, 0.67, 0.83, 1].map((t) => `<b style="background:${ramp(t, m.ramp)}"></b>`).join("");
    el.innerHTML = `<p class="key-title">${esc(m.label)} en ${S.year}</p>
      <div class="key-ramp">${blocks}</div>
      <div class="key-labels"><span>0</span><span>${unit(max)}</span></div>
      <p class="key-hint">Cada círculo es una comuna. ${esc(m.hint)}</p>`;
  }
}

function updateMap() {
  if (!map || !S.meta) return;
  const res = S.ens[S.current];
  const y = S.year;
  yearInput.value = y;
  $("#yearLabel").textContent = y;
  if (!res) { $("#mapWhen").textContent = S.current === "custom" ? "Simula tu regla para verla en el mapa" : "Cargando el mapa…"; return; }
  const name = S.current === "custom" ? "tu regla" : S.story.tabs.find((t) => t.id === S.current).name;
  const base = baseEns();
  const diff = S.view === "diff" && S.current !== "status_quo" && base;
  const vs = S.current === "custom" ? `Tu regla comparada con seguir como hoy en los mismos ${fmt(res.meta.n)} futuros`
    : `${name} frente a seguir como hoy`;  // "frente a": sirve para nombres femeninos y masculinos
  const when = y < 2026 ? "Historia real, igual en todas las reglas" : y === 2026 ? "2026: real hasta noviembre"
    : diff ? vs : `Futuro simulado · ${name}`;
  $("#mapWhen").textContent = diff && y <= 2026 ? `${when}: todavía no hay diferencia` : when;
  const m = METRICS[S.metric];
  const max = diff ? diffMax(S.metric) : metricMax(S.metric);
  renderKey(m, max, diff);
  communeLayer.clearLayers();
  S.meta.communes.forEach((c, i) => {
    const v = res.communes[S.metric].p50[i][yi(y)] * m.scale;
    const b = base ? base.communes[S.metric].p50[i][yi(y)] * m.scale : v;
    const d = v - b;
    const tiny = max * 0.02;
    const fill = diff ? diverge(d / max) : ramp(v / max);
    const op = diff ? (Math.abs(d) > tiny ? 0.7 : 0.15) : (v > 0 ? 0.6 : 0.12);
    const circle = L.circle([c.lat, c.lon], { radius: c.radius_km * 1000, color: "#eef0f3", weight: 1, fillColor: fill, fillOpacity: op });
    const cmp = S.current !== "status_quo" && base
      ? `<br>Como hoy: ${fmt(b, m.d)} ${m.unit} (${d >= 0 ? "+" : "−"}${fmt(Math.abs(d), m.d)})` : "";
    circle.bindTooltip(`<b>${esc(c.name)}</b><br>${m.label}: ${fmt(v, m.d)} ${m.unit}${cmp}`, { sticky: true });
    circle.on("click", () => showCommune(i));
    communeLayer.addLayer(circle);
  });
  dcLayer.clearLayers();
  const knownMW = new Array(S.meta.communes.length).fill(0);
  S.meta.projects.forEach((p, i) => {
    const pr = res.projects.status_prob[i][yi(y)];
    let code = 0;
    pr.forEach((v, k) => { if (v > pr[code]) code = k; });
    const ci = res.projects.commune_mode[i][yi(y)];
    knownMW[ci] += pr[ST.OPER] * p.it_mw;
    const style = dcStyle(code, p.it_mw);
    if (!style) return;
    const c = S.meta.communes[ci];
    const moved = c.id !== p.commune;
    const ll = moved ? [c.lat + 0.01 * Math.sin(i), c.lon - (c.radius_km / 111) * 0.9 + 0.01 * Math.cos(i)] : [p.lat, p.lon];
    const mk = L.circleMarker(ll, style);
    mk.bindTooltip(`<b>${esc(p.name)}</b> · ${fmt(p.it_mw)} MW<br>${S.meta.status_labels[code]}${moved ? `, se mudó a ${esc(c.name)}` : ""}`);
    mk.on("click", () => showProject(i));
    dcLayer.addLayer(mk);
  });
  if (y > 2026) {
    S.meta.communes.forEach((c, i) => {
      const extra = res.communes.c_it.p50[i][yi(y)] - knownMW[i];
      if (extra <= 15) return;
      const mk = L.circleMarker([c.lat - (c.radius_km / 111) * 0.5, c.lon + (c.radius_km / 111) * 0.6], {
        radius: 3 + 1.0 * Math.sqrt(extra), color: "#ffffff", weight: 1.5, fillColor: "#8a919c", fillOpacity: 0.75 });
      mk.bindTooltip(`<b>Proyectos nuevos en ${esc(c.name)}</b><br>~${fmt(extra)} MW que aún no se anuncian`);
      dcLayer.addLayer(mk);
    });
  }
  // proyectos que se mudan en al menos un cuarto de los futuros: se dibujan también en su destino
  const pm = res.projects.p_moved;
  const dm = res.projects.dest_mode;
  if (pm && dm) {
    S.meta.projects.forEach((p, i) => {
      const share = pm[i][yi(y)];
      const di = dm[i][yi(y)];
      if (share < 0.25 || di < 0) return;
      const c = S.meta.communes[di];
      const ll = [c.lat + 0.03 * Math.sin(i * 2.4), c.lon + 0.03 * Math.cos(i * 2.4)];
      const mk = L.circleMarker(ll, { radius: 3 + 1.0 * Math.sqrt(p.it_mw), color: DC_INK, weight: 2, dashArray: "7 4", fillOpacity: 0 });
      const from = S.meta.communes.find((x) => x.id === p.commune).name;
      mk.bindTooltip(`<b>${esc(p.name)}</b> · ${fmt(p.it_mw)} MW<br>Se muda de ${esc(from)} a ${esc(c.name)} en ${fmt(100 * share)}% de los futuros`);
      mk.on("click", () => showProject(i));
      dcLayer.addLayer(mk);
    });
  }
}

function infoPanel(html) {
  const el = $("#mapInfo");
  el.innerHTML = `<button type="button" class="info-close">Cerrar</button>${html}`;
  el.hidden = false;
  el.querySelector(".info-close").addEventListener("click", () => { el.hidden = true; });
}
function showCommune(i) {
  const res = S.ens[S.current];
  const c = S.meta.communes[i];
  const y = S.year;
  const base = baseEns();
  const cmp = S.current !== "status_quo" && base;
  const g = (k, sc = 1, r = res) => r.communes[k].p50[i][yi(y)] * sc;
  const row = (label, k, sc, unit, d = 0) => `<dt>${label}</dt><dd>${fmt(g(k, sc), d)} ${unit}${
    cmp ? `<small>como hoy ${fmt(g(k, sc, base), d)}</small>` : ""}</dd>`;
  const usd = (r) => (g("c_muni_usd", 1, r) + g("c_fund_usd", 1, r)) / c.households;
  infoPanel(`<h3>${esc(c.name)} · ${y}</h3>
    <p class="info-sub">${fmt(c.pop)} habitantes · ${fmt(c.households)} hogares${cmp ? " · comparado con seguir como hoy" : ""}</p>
    <dl>
      ${row("Data centers operando", "c_it", 1, "MW")}
      ${row("Esperando red", "c_waitlist", 1, "MW")}
      ${row("Electricidad de la comuna que usan", "c_share", 100, "%")}
      ${row("Agua que usan", "c_water_ls", 1, "L/s", 1)}
      ${row("Vecinos movilizados", "c_conflict", 100, "%")}
      <dt>Patentes y fondos por hogar</dt><dd>US$ ${fmt(usd(res))} al año${cmp ? `<small>como hoy US$ ${fmt(usd(base))}</small>` : ""}</dd>
    </dl>`);
}
function showProject(i) {
  const res = S.ens[S.current];
  const p = S.meta.projects[i];
  const y = S.year;
  const pr = res.projects.status_prob[i][yi(y)];
  const labels = S.meta.status_labels;
  const real = { operando: "operando", construccion: "en construcción", tramitacion: "en tramitación", lista_espera: "esperando red" }[p.real_status];
  const rows = pr.map((v, k) => ({ v, k })).filter((o) => o.v >= 0.05).sort((a, b) => b.v - a.v);
  infoPanel(`<h3>${esc(p.name)}</h3>
    <p class="info-sub">${esc(p.operator)} · ${fmt(p.it_mw, p.it_mw % 1 ? 1 : 0)} MW de servidores${p.request_mw ? ` (pide ${fmt(p.request_mw)} MW de conexión)` : ""} · enfriamiento por ${esc(p.cooling)}${p.dist_homes_m ? ` · ${fmt(p.dist_homes_m)} m de viviendas` : ""}</p>
    ${real ? `<p>Estado real en noviembre de 2026: <b>${real}</b></p>` : ""}
    <p>En ${y}, en los futuros simulados:</p>
    <dl>${rows.map((o) => `<dt>${labels[o.k]}</dt><dd>${fmt(100 * o.v)}%</dd>`).join("")}</dl>
    ${res.projects.p_moved && res.projects.p_moved[i][yi(y)] >= 0.05 && res.projects.dest_mode[i][yi(y)] >= 0
      ? `<p>Se muda a <b>${esc(S.meta.communes[res.projects.dest_mode[i][yi(y)]].name)}</b> en ${fmt(100 * res.projects.p_moved[i][yi(y)])}% de los futuros.</p>` : ""}
    ${p.hist.length ? `<ul>${p.hist.slice(0, 4).map((h) => `<li>${esc(h)}</li>`).join("")}</ul>` : ""}`);
}

function focusProject(id, year) {
  select("status_quo");
  S.year = year;
  $("#simular").scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
  loadEnsemble("status_quo").then(() => {
    updateMap();
    const i = S.meta.projects.findIndex((p) => p.id === id);
    const p = S.meta.projects[i];
    map.setView([p.lat, p.lon], 13);
    showProject(i);
  });
}
document.querySelectorAll("[data-project]").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault();
  if (S.meta) focusProject(a.dataset.project, Number(a.dataset.year));
}));

// ---------------------------------------------------------------- hallazgos, prueba y detalle
function fillFindings() {
  const byId = Object.fromEntries((S.story.findings || []).map((f) => [f.id, f]));
  const set = (id, txt) => { const el = $(`[data-f="${id}"]`); if (el && txt) el.textContent = txt; };
  if (byId.permisos) set("permisos", byId.permisos.stat.replace("+", ""));
  if (byId.cerrillos) set("cerrillos", byId.cerrillos.stat.replace(" → ", " a "));
  if (byId.boom) set("boom", byId.boom.stat.replace("×", ""));
  if (byId.boom && byId.boom.mw_pct !== undefined) set("boom-mw", `${fmt(byId.boom.mw_pct)}%`);
  const n = (S.story.findings || [])[0];
  if (n) $("#closeStats").textContent = `${fmt(n.n_sims)} simulaciones, 200 futuros por regla, ${S.story.passed} de ${S.story.total} chequeos con datos reales.`;
  // bajo cada hallazgo de la portada, si resiste mover los supuestos
  document.querySelectorAll(".chapter[data-finding]").forEach((ch) => {
    const line = firmLine((S.story.sensitivity || {})[ch.dataset.finding]);
    const p = ch.querySelector(".ch-text");
    if (line && p && !p.querySelector(".ch-firm")) p.insertAdjacentHTML("beforeend", `<span class="ch-firm">${line}</span>`);
  });
}

function fillMoreFindings() {
  const byId = Object.fromEntries((S.story.findings || []).map((f) => [f.id, f]));
  const others = ["lampa", "transparencia", "trayectoria", "paquete"].map((k) => byId[k]).filter(Boolean);
  const firm = (id) => { const line = firmLine((S.story.sensitivity || {})[id]); return line ? `<p class="finding-firm">${line}</p>` : ""; };
  $("#moreFindings").innerHTML = others.map((f) => `<div class="finding">
    <h3><span class="finding-stat">${esc(f.stat)}</span> ${esc(f.headline)}</h3>
    <p>${esc(f.body)}</p><p class="finding-cost">${esc(f.cost)}</p>${firm(f.id)}</div>`).join("");
  return Promise.resolve();
}

// ---------------------------------------------------------------- qué tan firmes son los hallazgos
// Texto a partir de cache/sensitivity.json (python -m dcsim.sensitivity): cada supuesto fijo se lleva
// a su extremo bajo y a su extremo alto, uno a la vez, y después se sortean todos juntos. Solo arman
// texto: no tocan la página.

// umbral de cada criterio (dcsim/sensitivity.py, evaluate) sobre el escalar con que se ordenan los
// extremos, y si el hallazgo pide quedar sobre él (1) o bajo él (−1). Solo sirve para avisar de los
// casos al límite: si se mantiene o no lo dice el análisis.
const FIRM_LIMIT = { paquete: [0.5, 1], permisos: [0.05, -1], boom: [1, 1], cerrillos: [0.25, 1], lampa: [0.25, 1], transparencia: [2 / 3, 1] };
const FIRM_NEAR = 0.05;  // a menos de 5% del umbral
// contexto de una variante donde el hallazgo no se mantiene. En Cerrillos, "con agua" es lo que
// pasó: la variante le da baja probabilidad al juicio real, y la regla de coherencia con la
// historia cuenta juicios, no a quién se demanda
const FIRM_CONTEXT = {
  cerrillos: (f, v) => `Con agua es lo que pasó: en esa variante, el juicio que sí hubo contra Google Cerrillos tendría ${firmPct(v[0])} de probabilidad, contra ${firmPct(f.base[0])} con los supuestos centrales. La regla de coherencia con la historia cuenta juicios, no a quién se demanda, así que no descarta esa variante.`,
};

// el escalar de "range" y "top": la cifra misma, la diferencia con agua y con aire (Cerrillos) o
// cuánto logra la transparencia del efecto del fondo
function firmScalar(f, v) {
  if (!Array.isArray(v)) return v;
  return f.id === "transparencia" ? Math.abs(v[0]) / Math.max(Math.abs(v[1]), 1e-3) : v[0] - v[1];
}
const firmSigned = (f) => /^Cambio/.test(f.metric || "");  // un cambio relativo lleva signo: +0,4%

// porcentaje que se lee bien: sin decimales, salvo bajo 10% si el decimal dice algo (+0,4%, 3,5%)
function firmPct(x, signed = false) {
  const a = Math.abs(100 * x);
  const s = fmt(a, a < 10 && Math.round(a * 10) % 10 !== 0 ? 1 : 0);
  return `${s === "0" ? "" : x < 0 ? "−" : signed ? "+" : ""}${s}%`;
}

// una cifra del hallazgo (valor central, de una variante o del sorteo conjunto)
function firmValue(f, v) {
  if (v == null) return "—";
  if (f.fmt === "ratio") return `${fmt(v, 1)} veces`;
  if (Array.isArray(v)) return f.id === "transparencia" ? `${firmPct(v[0])} vs ${firmPct(v[1])}` : `${firmPct(v[0])} → ${firmPct(v[1])}`;
  return firmPct(v, firmSigned(f));
}

// el escalar en palabras, un valor (a) o un rango (a a b)
function firmScalarText(f, a, b = null) {
  const span = (one) => (b == null ? one(a) : `${one(a)} a ${one(b)}`);
  if (f.id === "transparencia") {
    return `la transparencia logra ${b == null ? firmPct(a) : `entre ${firmPct(a)} y ${firmPct(b)}`} del efecto del fondo`;
  }
  if (f.fmt === "pair_pct") return `diferencia de ${span((x) => fmt(100 * x))} puntos`;
  if (f.fmt === "ratio") return `${span((x) => fmt(x, 1))} veces`;
  return span((x) => firmPct(x, firmSigned(f)));
}

// «Peso del agua…» → «el peso del agua…», con el artículo y el número (baja / bajan) que pide la
// primera palabra. Las siglas (PUE, WUE, NOx) no pasan a minúscula.
function firmSubject(label) {
  const w = label.split(" ")[0];
  const acro = w.length > 1 && w[1] !== w[1].toLowerCase();
  const plural = !acro && w.endsWith("s");
  const fem = w === "Prob." || /(a|as|ión|dad)$/.test(w);
  const art = plural ? (fem ? "las" : "los") : fem ? "la" : "el";
  return [`${art} ${acro ? label : label[0].toLowerCase() + label.slice(1)}`, plural];
}

// «si el peso del agua … baja de 1,2 a 0,6»; x: {label, end, value, base, unit}
function firmIf(x) {
  const [subject, plural] = firmSubject(x.label);
  const verb = (x.end === "low" ? "baja" : "sube") + (plural ? "n" : "");
  const unit = x.unit && !["—", "1/mes", "1/año"].includes(x.unit) ? ` ${x.unit}` : "";
  const from = x.base == null ? "" : `de ${num(x.base, 0)} `;
  return `si ${esc(subject)} ${verb} ${from}a ${num(x.value, 0)}${esc(unit)}`;
}

// la línea bajo cada hallazgo; s: un hallazgo de story.sensitivity (/api/story)
function firmLine(s) {
  if (!s || !s.total) return "";
  const link = '(<a href="#firmeza" data-open="firmeza">cómo se probó</a>)';
  const head = `Se mantiene en ${fmt(s.holds)} de ${fmt(s.total)} variantes`;
  if (!s.fails.length) {
    return `${head} de los supuestos${s.joint_holds === false ? ", pero no al sortearlos todos juntos" : ""} ${link}.`;
  }
  const more = s.fails.length > 2 ? ` (y en ${fmt(s.fails.length - 2)} variantes más)` : "";
  const joint = s.joint_holds === false ? " ni al sortear todos los supuestos juntos" : "";
  return `${head}. No se mantiene ${s.fails.slice(0, 2).map(firmIf).join(" ni ")}${more}${joint} ${link}.`;
}

// el detalle técnico: un párrafo, una fila por hallazgo y, debajo, dónde no se mantiene.
// kicker(f): el título del hallazgo en la portada; nSampled: supuestos que se sortean en cada futuro
function firmHtml(sens, kicker = (f) => f.kicker, nSampled = null) {
  if (!sens || !sens.findings || !sens.findings.length) return "<p>Todavía no está el análisis de sensibilidad (cache/sensitivity.json).</p>";
  const F = sens.findings;
  const nF = sens.factors.length;
  const total = F[0].total;
  const factor = Object.fromEntries(sens.factors.map((p) => [p.key, p]));
  const at = (r, e) => ({ ...factor[r.key], end: e, value: factor[r.key][e] });  // para firmIf
  const intro = `<p>En cada futuro, ${fmt(nF)} supuestos quedan fijos en su valor central${nSampled == null ? "" : ` (los otros ${fmt(nSampled)} se sortean)`}. Para ver si los hallazgos dependen de ellos, llevamos cada uno a su extremo bajo y a su extremo alto, de a uno: ${fmt(total)} variantes de ${fmt(sens.n_oat)} futuros cada una, con los mismos números aleatorios que la corrida normal, así la diferencia es efecto del supuesto. Después los sorteamos todos juntos en ${fmt(sens.n_joint)} futuros. Son ${fmt(sens.n_sims)} simulaciones. La columna de los supuestos centrales usa esos mismos ${fmt(sens.n_oat)} futuros, por eso puede diferir un poco de la cifra de la portada, calculada con más futuros.</p>`;
  const rows = F.map((f) => `<tr><td>${esc(kicker(f))}<br><span class="range">${esc(f.metric)}</span></td>
    <td data-label="Con los supuestos centrales">${firmValue(f, f.base)}</td>
    <td data-label="Al mover cada supuesto">${firmScalarText(f, f.range[0], f.range[1])}</td>
    <td data-label="Se mantiene">${fmt(f.holds)} de ${fmt(f.total)}</td>
    <td data-label="Todos juntos">${firmValue(f, f.joint.value)}${f.joint.value != null && !f.joint.holds ? " · no se mantiene" : ""}</td>
    <td data-label="Lo que más lo mueve">${f.top && f.top[0] ? esc(f.top[0].label) : "—"}</td></tr>`).join("");
  const table = `<table class="data firm-table"><thead><tr><th>Hallazgo</th><th>Con los supuestos centrales</th><th>Al mover cada supuesto</th><th>Se mantiene</th><th>Todos sorteados juntos (${fmt(sens.n_joint)} futuros)</th><th>El supuesto que más lo mueve</th></tr></thead><tbody>${rows}</tbody></table>`;
  // totales, dónde no se mantiene y dónde se mantiene por poco
  const held = F.reduce((a, f) => a + f.holds, 0);
  const tests = F.reduce((a, f) => a + f.total, 0);
  const jointOk = F.filter((f) => f.joint.value != null && f.joint.holds).length;
  const jointRun = F.filter((f) => f.joint.value != null).length;
  let sum = `Se mantienen ${fmt(held)} de las ${fmt(tests)} pruebas (${fmt(F.length)} hallazgos × ${fmt(total)} variantes).`;
  if (jointRun) sum += ` Con todos los supuestos sorteados juntos se mantienen ${jointOk === jointRun ? `los ${fmt(jointOk)}` : `${fmt(jointOk)} de ${fmt(jointRun)}`}.`;
  const ends = (f, keep) => f.oat.flatMap((r) => ["low", "high"].filter((e) => keep(r, e)).map((e) => [r, e]));
  const explain = (f, r, e) => {
    const s = firmScalar(f, r[e]);
    return `${firmIf(at(r, e))}: queda en ${firmValue(f, r[e])}${Array.isArray(r[e]) ? ` (${firmScalarText(f, s)})` : ""}`;
  };
  const context = (f, x) => (FIRM_CONTEXT[f.id] ? x.map(([r, e]) => ` ${FIRM_CONTEXT[f.id](f, r[e])}`).join("") : "");
  const fails = F.map((f) => [f, ends(f, (r, e) => !r[`holds_${e}`])]).filter(([, x]) => x.length)
    .map(([f, x]) => `«${esc(kicker(f))}» no se mantiene ${x.map(([r, e]) => explain(f, r, e)).join("; ni ")}. ${esc(f.criterion)}${context(f, x)}`);
  const near = F.filter((f) => FIRM_LIMIT[f.id]).map((f) => {
    const [lim, dir] = FIRM_LIMIT[f.id];
    return [f, ends(f, (r, e) => r[`holds_${e}`] && dir * (firmScalar(f, r[e]) - lim) / Math.abs(lim) < FIRM_NEAR)];
  }).filter(([, x]) => x.length)
    .map(([f, x]) => `«${esc(kicker(f))}» se mantiene por poco ${x.map(([r, e]) => explain(f, r, e)).join("; y ")}. ${esc(f.criterion)}`);
  const cons = F[0].total_consistent;
  const history = `${cons === total ? `Las ${fmt(total)} variantes` : `${fmt(cons)} de las ${fmt(total)} variantes`} siguen siendo coherentes con la historia. ${esc(sens.hindcast_rule)}`;
  const limits = `Límites: con ${fmt(sens.n_oat)} futuros por variante, cada porcentaje tiene un error de azar de hasta ${fmt(100 * Math.sqrt(0.25 / sens.n_oat))} puntos; las combinaciones de supuestos solo se prueban en el sorteo conjunto; y quedan números fijos en el código que este análisis no mueve: los pesos con que un proyecto elige comuna, cuánto molesta cada fuente y a qué distancia, quién cuenta como vecino, la desconfianza que deja cada juicio o anulación, las decisiones de la evaluación conjunta y la sensibilidad y el umbral de cada hogar.`;
  return `${intro}${table}<p>${sum}</p>${fails.map((t) => `<p>${t}</p>`).join("")}${near.map((t) => `<p>${t}</p>`).join("")}<p class="where">${history}</p><p class="where">${limits}</p>`;
}

function fillProof() {
  $("#passed").textContent = `${S.story.passed} de ${S.story.total}`;
  if (S.story.n_validation !== undefined) $("#passedKinds").textContent = `(${S.story.n_validation} de validación y ${S.story.n_calibration} de calibración)`;
  const LABEL = {
    rm_2021: [2021, "Electricidad de los data centers de Santiago", "MW"],
    google_water: [2024, "Agua usada por Google en Quilicura", "ML"],
    rm_2025: [2025, "Electricidad de los data centers de Santiago", "MW"],
    waitlist: [2026, "MW esperando conexión a la red", ""],
    litigations: [2026, "Juicios contra data centers desde 2012", ""],
    conflict_pattern: [2026, "Comunas con vecinos organizados", ""],
  };
  let lastYear = null;
  $("#proofRows").innerHTML = S.story.checks.map((c) => {
    const [year, label, unit] = LABEL[c.id];
    const u = unit ? ` ${unit}` : "";
    const real = c.id === "conflict_pattern" ? String(c.observed.length) : `${fmt(c.observed)}${u}`;
    const model = c.id === "conflict_pattern" ? `${c.sim.hits} de ${c.observed.length}` : `${fmt(c.sim.p50)}${u}`;
    const yr = year === lastYear ? "" : year;
    lastYear = year;
    return `<tr><td>${yr}</td><td>${label}</td><td data-label="Real">${real}</td><td data-label="Modelo">${model}</td><td>${esc(c.src)}</td></tr>`;
  }).join("");
}

// enlaces que abren una parte del detalle técnico, también los que se agregan después («cómo se probó»)
document.addEventListener("click", (e) => {
  const a = e.target.closest && e.target.closest("[data-open]");
  const d = a && document.getElementById(a.dataset.open);
  if (!d) return;
  e.preventDefault();
  d.open = true;
  d.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
});

const lazy = {
  "mas-hallazgos": () => fillMoreFindings(),
  firmeza: () => fetch("/api/sensitivity").then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); }).then((sens) => {
    const byId = Object.fromEntries((S.story.findings || []).map((f) => [f.id, f]));
    $("#firmezaBody").innerHTML = firmHtml(sens, (f) => (byId[f.id] || f).kicker, S.meta.params.filter((p) => p.sample).length);
  }),
  matematica: () => { $("#mathBody").replaceChildren($("#mathTpl").content.cloneNode(true)); return Promise.resolve(); },
  chequeos: () => fetch("/api/validation").then((r) => r.json()).then((v) => {
    const n = (x) => fmt(x, Math.abs(x) < 10 && x % 1 ? 1 : 0);
    const show = (x) => {
      if (x == null) return "";
      if (Array.isArray(x)) return esc(x.join(", "));
      if (typeof x === "number") return n(x);
      if (x.p50 !== undefined) return `${n(x.p50)} <span class="range">(${n(x.p5)} a ${n(x.p95)})</span>`;
      if (x.low !== undefined) return `${n(x.low)} a ${n(x.high)}`;
      if (x.top4) return esc(x.top4.join(", "));
      if (x.accuracy !== undefined) return `${n(x.accuracy)}% de acierto${x.naive !== undefined ? ` (regla trivial: ${n(x.naive)}%)` : ""}`;
      return "";
    };
    $("#checksBody").innerHTML = `<p>${v.passed} de ${v.total} coinciden. <b>Validación</b>: el modelo nunca se ajustó a ese dato. <b>Calibración</b>: un parámetro se ajustó usando ese dato.</p>
      <table class="data"><thead><tr><th>Pregunta</th><th>Real</th><th>Modelo (rango del 90%)</th><th>Tipo</th><th>Resultado</th></tr></thead><tbody>${
      v.checks.map((c) => `<tr><td>${esc(c.question)}</td><td>${show(c.observed)} ${c.id === "status" ? "proyectos" : esc(c.unit)}</td><td>${show(c.sim)}</td><td>${esc(c.kind)}</td><td>${c.pass ? "coincide" : "no coincide"}</td></tr>`).join("")
      }</tbody></table>`;
  }),
  supuestos: () => {
    const ps = S.meta.params;
    const sampled = ps.filter((p) => p.sample).length;
    $("#paramsBody").innerHTML = `<p>${fmt(ps.length)} supuestos: ${fmt(sampled)} se sortean en cada futuro y los otros ${fmt(ps.length - sampled)} quedan en su valor central. Esos ${fmt(ps.length - sampled)} se llevan a sus extremos en <a href="#firmeza" data-open="firmeza">Qué tan firmes son los hallazgos</a>.</p>
      <table class="data"><thead><tr><th>Supuesto</th><th>Valor</th><th>Rango</th><th>¿Se sortea?</th><th>Tipo</th><th>Fuente</th></tr></thead><tbody>${
      ps.map((p) => `<tr><td>${esc(p.label)}</td><td>${num(p.base)} ${p.unit === "—" ? "" : esc(p.unit)}</td><td>${num(p.low)} a ${num(p.high)}</td><td>${p.sample ? "sí" : "no"}</td><td>${esc(p.kind)}</td><td>${esc(p.src)}</td></tr>`).join("")
      }</tbody></table>`;
    return Promise.resolve();
  },
  inventario: () => {
    const real = { operando: "operando", construccion: "en construcción", tramitacion: "en tramitación", lista_espera: "esperando red" };
    const cname = Object.fromEntries(S.meta.communes.map((c) => [c.id, c.name]));
    $("#projectsBody").innerHTML = `<table class="data"><thead><tr><th>Proyecto</th><th>Comuna</th><th>MW</th><th>Enfriamiento</th><th>Estado nov-2026</th><th>Fuente o supuesto</th></tr></thead><tbody>${
      S.meta.projects.map((p) => `<tr><td>${esc(p.name)}</td><td>${esc(cname[p.commune])}</td><td>${fmt(p.it_mw, p.it_mw % 1 ? 1 : 0)}</td><td>${esc(p.cooling)}</td><td>${p.real_status ? real[p.real_status] : ""}</td><td>${esc(p.src)}</td></tr>`).join("")
      }</tbody></table>`;
    return Promise.resolve();
  },
};
// cada parte se llena al abrirla; si se abrió antes de que llegaran los datos, al llegar (arranque)
function loadLazy(d) {
  if (!d || !d.open || d.dataset.loaded || !S.meta || !S.story) return;
  d.dataset.loaded = "1";
  lazy[d.id]().catch(() => { d.dataset.loaded = ""; });
}
Object.keys(lazy).forEach((id) => {
  const d = document.getElementById(id);
  d.addEventListener("toggle", () => loadLazy(d));
});
// un enlace directo a una parte (/#firmeza) la abre
const linked = location.hash.length > 1 && document.getElementById(location.hash.slice(1));
if (linked && linked.tagName === "DETAILS") linked.open = true;

// ---------------------------------------------------------------- entradas al hacer scroll
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("in");
    io.unobserve(e.target);
    if (e.target.classList.contains("map-card") && map) setTimeout(() => map.invalidateSize(), 50);
  });
}, { threshold: 0.12 });
document.querySelectorAll("section").forEach((sec) => {
  sec.querySelectorAll("[data-rise]").forEach((el, i) => {
    el.style.transitionDelay = `${i * 80}ms`;
    io.observe(el);
  });
});
document.querySelectorAll(".chapter").forEach((c) => io.observe(c));
