/* Aterriza: una sola página. Elegir una regla cambia las seis cifras y el mapa. */
"use strict";
document.documentElement.classList.add("js");

const $ = (s, el = document) => el.querySelector(s);
const nf = (d = 0) => new Intl.NumberFormat("es-CL", { maximumFractionDigits: d, minimumFractionDigits: d });
const fmt = (x, d = 0) => nf(d).format(x);
const money = (musd) => (musd >= 1000 ? `US$ ${fmt(musd / 1000, 1)} mil millones` : `US$ ${fmt(musd)} millones`);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const Y0 = 2012;
const yi = (y) => y - Y0;
const ST = { NONE: 0, PERMIT: 1, WAIT: 2, LITIG: 3, BUILD: 4, OPER: 5, CANCEL: 6 };
const INK = "#0b0c0e";
const COBALT_RAMP = ["#dde1fa", "#b9c1f7", "#8e99f2", "#6372ee", "#3d4cea", "#1f2de6", "#1520a8"];

// cifra -> cómo mostrarla y si "más" es mejor (null = ni mejor ni peor)
const BANDS = {
  it_chile: { show: (v) => `${fmt(v)} MW`, goodUp: null,
    note: (vals) => `≈ ${fmt(100 * vals.dc_share_national, 1)}% de la electricidad de Chile` },
  water_ls_rm: { show: (v) => `${fmt(v)} L/s`, goodUp: false,
    note: (vals) => `el agua de ${fmt(vals.water_ls_rm * 86400 / 500)} hogares` },
  conflict_rm: { show: (v) => `${fmt(100 * v)}%`, goodUp: false, points: true, scale: 100 },
  litigations: { show: (v) => fmt(v), goodUp: false },
  invest_lost: { show: money, goodUp: false },
  bill_pct: { show: (v) => `+${fmt(v, 1)}%`, goodUp: false, points: true, scale: 1 },
};
const KEYS = ["it_chile", "dc_share_national", "water_ls_rm", "conflict_rm", "litigations", "invest_lost", "bill_pct"];
const METRICS = {
  c_conflict: { label: "Vecinos movilizados", unit: "%", scale: 100, d: 0 },
  c_water_ls: { label: "Agua de data centers", unit: "L/s", scale: 1, d: 1 },
  c_it: { label: "Data centers operando", unit: "MW", scale: 1, d: 0 },
};

const S = { story: null, meta: null, ens: {}, current: "status_quo", year: 2035, metric: "c_conflict",
  view: "value", playing: null, customValues: null, customText: "", editing: false };
// al elegir una regla, el mapa muestra la capa donde esa regla más se nota
const RULE_METRIC = { mesa: "c_it", aire: "c_water_ls", acumulativa: "c_conflict", norte: "c_it",
  paquete: "c_conflict", custom: "c_conflict" };
const WARM = "#d8461b";
const MID = "#d9dce2";

// ---------------------------------------------------------------- arranque
Promise.all([fetch("/api/story").then((r) => r.json()), fetch("/api/meta").then((r) => r.json())])
  .then(([story, meta]) => {
    S.story = story;
    S.meta = meta;
    renderNumbers(false);
    fillFindings();
    fillProof();
    initMap();
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
  loadEnsemble(id).then(updateMap).catch(() => {});
}

function valuesFor(id) {
  if (id === "custom") return S.customValues;
  const tab = S.story.tabs.find((t) => t.id === id);
  return Object.fromEntries(KEYS.map((k) => [k, tab.values[k].p50]));
}

function renderNumbers(animate) {
  const id = S.current;
  const base = valuesFor("status_quo");
  let summary;
  if (id === "custom") {
    summary = S.customValues && !S.editing
      ? `<b>Tu regla:</b> ${esc(S.customText)}. <button type="button" class="inline-link" id="editRule">Cambiarla</button>`
      : "Elige cada palanca y simula. El resultado se compara con seguir como hoy.";
  } else {
    const tab = S.story.tabs.find((t) => t.id === id);
    summary = esc(tab.summary);
    if (id === "status_quo") summary += " Es el punto de comparación de las otras reglas.";
    if (id === "paquete") {
      const f = (S.story.findings || []).find((x) => x.id === "paquete");
      if (f) summary += ` <b>Mejora las seis cifras a la vez en ${esc(f.stat)} de los futuros.</b>`;
    }
  }
  $("#ruleSummary").innerHTML = summary;
  const edit = $("#editRule");
  if (edit) edit.addEventListener("click", () => { S.editing = true; select("custom"); });
  const vals = valuesFor(id);
  if (!vals || (id === "custom" && S.editing)) return;
  document.querySelectorAll(".band").forEach((band) => {
    const k = band.dataset.k;
    const spec = BANDS[k];
    const val = band.querySelector(".val");
    val.textContent = spec.show(vals[k]);
    if (animate && !reduced) { val.classList.remove("tick"); void val.offsetWidth; val.classList.add("tick"); }
    if (spec.note) band.querySelector(".note").textContent = spec.note(vals);
    band.querySelector(".delta").innerHTML = id === "status_quo" ? "" : delta(spec, vals[k], base[k]);
  });
}

function delta(spec, v, b) {
  const up = v > b;
  const rel = b ? Math.abs(v - b) / Math.abs(b) : 0;
  const diff = Math.abs(v - b) * (spec.scale || 1);
  if ((spec.points && diff < 0.1) || (!spec.points && rel < 0.02)) return "igual que seguir como hoy";
  const amount = spec.points ? `${fmt(diff, diff < 10 ? 1 : 0)} puntos` : `${fmt(rel * 100)}%`;
  const verdict = spec.goodUp === null ? "" : (up === spec.goodUp ? "<b>mejor</b> · " : "<b>peor</b> · ");
  return `${verdict}${amount} ${up ? "más" : "menos"} que seguir como hoy`;
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
  $("#customNote").textContent = "Simulando 100 futuros…";
  try {
    const res = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy: pol }) }).then((r) => r.json());
    S.ens.custom = res;
    S.customValues = Object.fromEntries(KEYS.map((k) => [k, res.series[k].p50[yi(2035)]]));
    S.customText = describe(pol);
    S.editing = false;
    $("#customNote").textContent = "Corre 100 futuros, unos 5 segundos.";
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
  map = L.map("map", { scrollWheelZoom: false, zoomControl: true }).setView([-33.45, -70.73], 10);
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
function ramp(t) {  // secuencial continua: un solo tono, de claro a oscuro
  const n = COBALT_RAMP.length - 1;
  const p = Math.max(0, Math.min(1, t)) * n;
  const i = Math.min(n - 1, Math.floor(p));
  return mix(COBALT_RAMP[i], COBALT_RAMP[i + 1], p - i);
}
function diverge(t) {  // divergente: cobalto = menos que como hoy, gris = igual, naranjo = más
  const a = Math.min(1, Math.abs(t)) ** 0.7;
  return t < 0 ? mix(MID, COBALT_RAMP[5], a) : mix(MID, WARM, a);
}
function diffMax(m) {
  const base = S.ens.status_quo;
  let max = 0;
  if (!base) return 1;
  Object.entries(S.ens).forEach(([id, res]) => {
    if (id === "status_quo") return;
    res.communes[m].p50.forEach((row, i) => row.forEach((v, y) => { max = Math.max(max, Math.abs(v - base.communes[m].p50[i][y])); }));
  });
  return max * METRICS[m].scale || 1;
}
function dcStyle(code, mw) {
  const r = 3 + 1.4 * Math.sqrt(mw);
  if (code === ST.OPER) return { radius: r, color: "#ffffff", weight: 1.5, fillColor: INK, fillOpacity: 0.9 };
  if (code === ST.BUILD) return { radius: r, color: INK, weight: 3, fillColor: INK, fillOpacity: 0.35 };
  if (code === ST.PERMIT) return { radius: r, color: INK, weight: 2, fillOpacity: 0 };
  if (code === ST.WAIT) return { radius: r, color: "#5d6470", weight: 2, dashArray: "3 4", fillOpacity: 0 };
  if (code === ST.LITIG) return { radius: r, color: "#d03b3b", weight: 3, fillColor: "#d03b3b", fillOpacity: 0.12 };
  return null;
}

function updateMap() {
  if (!map || !S.meta) return;
  const res = S.ens[S.current];
  const y = S.year;
  yearInput.value = y;
  $("#yearLabel").textContent = y;
  if (!res) { $("#mapWhen").textContent = S.current === "custom" ? "Simula tu regla para verla en el mapa" : "Cargando el mapa…"; return; }
  const name = S.current === "custom" ? "tu regla" : S.story.tabs.find((t) => t.id === S.current).name;
  const base = S.ens.status_quo;
  const diff = S.view === "diff" && S.current !== "status_quo" && base;
  const when = y < 2026 ? "Historia real, igual en todas las reglas" : y === 2026 ? "2026: real hasta noviembre"
    : diff ? `${name} comparado con seguir como hoy` : `Futuro simulado · ${name}`;
  $("#mapWhen").textContent = diff && y <= 2026 ? `${when}: todavía no hay diferencia` : when;
  const m = METRICS[S.metric];
  const max = diff ? diffMax(S.metric) : metricMax(S.metric);
  const rampEl = $("#ramp");
  if (diff) {
    $("#rampLow").textContent = `−${fmt(max, m.d)} ${m.unit}`;
    $("#rampHigh").textContent = `+${fmt(max, m.d)} ${m.unit}`;
    rampEl.style.background = `linear-gradient(90deg, ${COBALT_RAMP[5]}, ${MID}, ${WARM})`;
    rampEl.title = "Menos que como hoy, igual, más que como hoy";
  } else {
    $("#rampLow").textContent = "0";
    $("#rampHigh").textContent = `${fmt(max, m.d)} ${m.unit}`;
    rampEl.style.background = `linear-gradient(90deg, ${COBALT_RAMP.join(", ")})`;
    rampEl.title = m.label;
  }
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
        radius: 3 + 1.4 * Math.sqrt(extra), color: "#ffffff", weight: 1.5, fillColor: "#8a919c", fillOpacity: 0.9 });
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
      const mk = L.circleMarker(ll, { radius: 3 + 1.4 * Math.sqrt(p.it_mw), color: COBALT_RAMP[5], weight: 2, dashArray: "4 4", fillOpacity: 0 });
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
  const base = S.ens.status_quo;
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
    <p class="info-sub">${esc(p.operator)} · ${fmt(p.it_mw, p.it_mw % 1 ? 1 : 0)} MW · enfriamiento por ${esc(p.cooling)}${p.dist_homes_m ? ` · ${fmt(p.dist_homes_m)} m de viviendas` : ""}</p>
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
}

function fillMoreFindings() {
  const byId = Object.fromEntries((S.story.findings || []).map((f) => [f.id, f]));
  const others = ["lampa", "transparencia", "trayectoria", "paquete"].map((k) => byId[k]).filter(Boolean);
  $("#moreFindings").innerHTML = others.map((f) => `<div class="finding">
    <h3><span class="finding-stat">${esc(f.stat)}</span> ${esc(f.headline)}</h3>
    <p>${esc(f.body)}</p><p class="finding-cost">${esc(f.cost)}</p></div>`).join("");
  return Promise.resolve();
}

function fillProof() {
  $("#passed").textContent = `${S.story.passed} de ${S.story.total}`;
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

document.querySelectorAll("[data-open]").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault();
  const d = document.getElementById(a.dataset.open);
  d.open = true;
  d.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
}));

const lazy = {
  "mas-hallazgos": () => fillMoreFindings(),
  chequeos: () => fetch("/api/validation").then((r) => r.json()).then((v) => {
    const n = (x) => fmt(x, Math.abs(x) < 10 && x % 1 ? 1 : 0);
    const show = (x) => {
      if (x == null) return "";
      if (Array.isArray(x)) return esc(x.join(", "));
      if (typeof x === "number") return n(x);
      if (x.p50 !== undefined) return `${n(x.p50)} <span class="range">(${n(x.p5)} a ${n(x.p95)})</span>`;
      if (x.low !== undefined) return `${n(x.low)} a ${n(x.high)}`;
      if (x.top4) return esc(x.top4.join(", "));
      if (x.accuracy !== undefined) return `${n(x.accuracy)}% de acierto`;
      return "";
    };
    $("#checksBody").innerHTML = `<p>${v.passed} de ${v.total} coinciden. <b>Validación</b>: el modelo nunca se ajustó a ese dato. <b>Calibración</b>: un parámetro se ajustó usando ese dato.</p>
      <table class="data"><thead><tr><th>Pregunta</th><th>Real</th><th>Modelo (rango del 90%)</th><th>Tipo</th><th>Resultado</th></tr></thead><tbody>${
      v.checks.map((c) => `<tr><td>${esc(c.question)}</td><td>${show(c.observed)} ${c.id === "status" ? "proyectos" : esc(c.unit)}</td><td>${show(c.sim)}</td><td>${esc(c.kind)}</td><td>${c.pass ? "coincide" : "no coincide"}</td></tr>`).join("")
      }</tbody></table>`;
  }),
  supuestos: () => {
    const nd = (x) => (Math.abs(x) < 1 && x !== 0 ? 2 : Math.abs(x) < 10 ? 1 : 0);
    $("#paramsBody").innerHTML = `<table class="data"><thead><tr><th>Supuesto</th><th>Valor</th><th>Rango</th><th>Tipo</th><th>Fuente</th></tr></thead><tbody>${
      S.meta.params.map((p) => `<tr><td>${esc(p.label)}</td><td>${fmt(p.base, nd(p.base))} ${p.unit === "—" ? "" : esc(p.unit)}</td><td>${fmt(p.low, nd(p.low))} a ${fmt(p.high, nd(p.high))}</td><td>${esc(p.kind)}</td><td>${esc(p.src)}</td></tr>`).join("")
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
Object.keys(lazy).forEach((id) => {
  const d = document.getElementById(id);
  d.addEventListener("toggle", () => {
    if (!d.open || d.dataset.loaded || !S.meta || !S.story) return;
    d.dataset.loaded = "1";
    lazy[id]().catch(() => { d.dataset.loaded = ""; });
  });
});

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
