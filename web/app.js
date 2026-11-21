/* Data centers y comunidades — interfaz */
"use strict";

const S = {
  meta: null, results: {}, selected: "status_quo", year: 2035, mapYear: 2026,
  mapMetric: "c_conflict", validation: null, insights: null, playing: null,
  customName: "Mi regla",
};
const ST = { NONE: 0, PERMIT: 1, WAIT: 2, LITIG: 3, BUILD: 4, OPER: 5, CANCEL: 6 };
const charts = {};

// ------------------------------------------------------------ utilidades
const $ = (sel, el = document) => el.querySelector(sel);
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const isDark = () => document.documentElement.dataset.theme === "dark" ||
  (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
const nf = (d = 0) => new Intl.NumberFormat("es-CL", { maximumFractionDigits: d, minimumFractionDigits: d });
const fmt = (x, d = 0) => (x === null || x === undefined || Number.isNaN(x)) ? "—" : nf(d).format(x);
const fmtAuto = (x) => Math.abs(x) >= 100 ? fmt(x) : Math.abs(x) >= 10 ? fmt(x, 0) : fmt(x, 1);
const yi = (y) => y - 2012;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function money(musd) {
  if (Math.abs(musd) >= 1000) return `US$ ${fmt(musd / 1000, 1)} mil millones`;
  return `US$ ${fmt(musd)} millones`;
}
async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}
const scenName = (id) => id === "custom" ? S.customName : (S.meta.scenarios.find((s) => s.id === id) || {}).name || id;

// ------------------------------------------------------------ arranque
init();
async function init() {
  setupTheme();
  S.meta = await api("/api/meta");
  renderScenarioCards();
  renderLevers();
  renderParams();
  renderProjects();
  setupYearSeg();
  initMap();
  api("/api/validation").then((v) => { S.validation = v; renderValidation(); }).catch(showErr("#validation"));
  await selectScenario("status_quo", false);
  api("/api/insights").then((v) => { S.insights = v; renderHypotheses(); }).catch(showErr("#hyps"));
}
function showErr(sel) {
  return (e) => { $(sel).innerHTML = `<p class="sub">No se pudo cargar (${esc(e.message)}). ¿Está corriendo el servidor?</p>`; };
}

function setupTheme() {
  const saved = (() => { try { return localStorage.getItem("theme"); } catch { return null; } })();
  if (saved) document.documentElement.dataset.theme = saved;
  $("#themeBtn").addEventListener("click", () => {
    const next = isDark() ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch { /* sin almacenamiento */ }
    refreshTheme();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", refreshTheme);
}
function refreshTheme() {
  setBaseLayer();
  if (S.validation) renderValidation();
  if (S.results[S.selected]) renderResults();
}

// ------------------------------------------------------------ 1. validación
function renderValidation() {
  const v = S.validation;
  const el = $("#validation");
  const checks = v.checks;
  const nVal = checks.filter((c) => c.kind === "validación").length;
  const cards = checks.filter((c) => c.id !== "status").map(checkCard).join("");
  const status = checks.find((c) => c.id === "status");
  el.innerHTML = `
    <div class="verdict-row">
      <div class="card score">
        <div class="big">${v.passed}<small> de ${v.total}</small></div>
        <p><b>chequeos coinciden con la realidad.</b></p>
        <p class="sub" style="margin:0">${nVal} son validaciones puras: el modelo nunca se ajustó a esos datos.
        El resto son calibraciones, marcadas como tales.</p>
        <p style="margin-top:8px"><span class="pill good">✓ Acierta el estado de ${fmt(status.sim.accuracy)}% de los proyectos</span></p>
      </div>
      <div class="card">
        <h3>Electricidad de los data centers de la RM: modelo vs dato oficial</h3>
        <div class="legend">
          <span><i style="background:${css("--s1")}"></i>Modelo (valor típico)</span>
          <span><i class="band" style="background:${css("--s1-wash")}"></i>90% de las simulaciones</span>
          <span><i class="dot"></i>Dato real (Min. de Energía / CEN)</span>
        </div>
        <div class="chart-box"><canvas id="valChart" aria-label="Gráfico de validación"></canvas></div>
      </div>
    </div>
    <div class="checks">${cards}</div>
    <details class="more">
      <summary>Ver proyecto por proyecto: estado real vs estado simulado (nov-2026)</summary>
      <div class="card table-wrap" style="margin-top:12px">${statusTable(status)}</div>
    </details>`;
  const s = v.series.demand_rm_dec;
  const years = S.meta.years.filter((y) => y <= 2026);
  lineChart("valChart", {
    years, unit: "MW", yTitle: "MW",
    series: [{ label: "Modelo", color: css("--s1"), wash: css("--s1-wash"), data: s, cut: years.length }],
    points: [{ x: 2021, y: 90, label: "Dato real 2021" }, { x: 2025, y: 260, label: "Dato real fin 2025" }],
    history: false,
  });
}
function simText(c) {
  const s = c.sim;
  if (s && s.p50 !== undefined) return `${fmtAuto(s.p50)}`;
  if (s && s.top4) return s.top4.join(", ");
  return "";
}
function obsText(c) {
  const o = c.observed;
  if (Array.isArray(o)) return o.join(", ");
  if (o && o.low !== undefined) return `${fmt(o.low)}–${fmt(o.high)}`;
  return fmtAuto(o);
}
function checkCard(c) {
  const kindTip = c.kind === "validación"
    ? "Validación: el modelo no fue ajustado para reproducir este dato."
    : "Calibración: un parámetro del modelo se ajustó usando este dato.";
  const isList = Array.isArray(c.observed);
  const range = c.sim && c.sim.p5 !== undefined ? `<div class="src">Rango simulado (90%): ${fmtAuto(c.sim.p5)}–${fmtAuto(c.sim.p95)} ${esc(c.unit)}</div>` : "";
  return `<div class="card check">
    <div class="check-top">
      <span class="pill ${c.pass ? "good" : "bad"}">${c.pass ? "✓ Coincide" : "✗ No coincide"}</span>
      <span class="kind" title="${kindTip}">${c.kind}</span>
    </div>
    <div class="q">${esc(c.question)}</div>
    ${isList ? `<div class="nums" style="flex-direction:column;gap:4px">
        <span>Real: <b style="display:inline;font-size:15px">${esc(obsText(c))}</b></span>
        <span>Modelo: <b style="display:inline;font-size:15px">${esc(simText(c))}</b></span></div>`
      : `<div class="nums"><span>Real<b>${esc(obsText(c))}</b></span><span>Modelo<b>${esc(simText(c))}</b></span>
        <span style="align-self:flex-end">${esc(c.unit)}</span></div>`}
    ${range}
    ${c.note ? `<div class="note">${esc(c.note)}</div>` : ""}
    <div class="src">Fuente: ${esc(c.src)}</div>
  </div>`;
}
function statusTable(c) {
  const labels = S.meta.status_labels;
  const realLabel = { operando: "operando", construccion: "en construcción", tramitacion: "en tramitación", lista_espera: "esperando red" };
  const rows = c.sim.rows.map((r) => `<tr>
    <td>${esc(r.name)}${r.anonymous ? ' <span class="sub">(sin nombre público)</span>' : ""}</td>
    <td>${realLabel[r.real]}</td><td>${labels[r.model]}</td>
    <td>${fmt(100 * r.p_real)}%</td>
    <td>${r.hit ? '<span class="pill good">✓</span>' : '<span class="pill bad">✗</span>'}</td></tr>`).join("");
  return `<table class="data"><thead><tr><th>Proyecto</th><th>Real (nov-2026)</th><th>Modelo (lo más probable)</th>
    <th title="En qué fracción de las simulaciones el proyecto estaba en su estado real">Prob. del estado real</th><th>¿Acierta?</th></tr></thead><tbody>${rows}</tbody></table>`;
}

// ------------------------------------------------------------ 2. escenarios
function renderScenarioCards() {
  const el = $("#scenarios");
  el.innerHTML = S.meta.scenarios.map((s) => `
    <button class="scen ${s.id === "status_quo" ? "base" : ""}" data-id="${s.id}" aria-pressed="${s.id === S.selected}">
      <span class="check-mark" aria-hidden="true">✓</span>
      <span class="tag">${s.id === "status_quo" ? "PUNTO DE COMPARACIÓN" : esc(s.name.toUpperCase())}</span>
      <span class="q">${esc(s.question)}</span>
      <span class="s">${esc(s.summary)}</span>
    </button>`).join("");
  el.querySelectorAll(".scen").forEach((b) => b.addEventListener("click", () => {
    selectScenario(b.dataset.id, true);
  }));
}
function markSelected() {
  document.querySelectorAll(".scen").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === S.selected)));
}
async function loadScenario(id) {
  if (!S.results[id]) S.results[id] = await api(`/api/scenario/${id}`);
  return S.results[id];
}
async function selectScenario(id, scroll) {
  S.selected = id;
  markSelected();
  if (scroll) $("#gente").scrollIntoView({ behavior: "smooth" });
  if (!S.results[id] || !S.results.status_quo) {
    $("#tiles").innerHTML = `<div class="loading"><div class="spinner"></div>Simulando 200 futuros con la regla "${esc(scenName(id))}"…</div>`;
  }
  try {
    await Promise.all([loadScenario("status_quo"), id === "custom" ? null : loadScenario(id)]);
  } catch (e) {
    $("#tiles").innerHTML = `<p class="sub">Error: ${esc(e.message)}</p>`;
    return;
  }
  if (S.mapYear <= 2026 && id !== "status_quo") S.mapYear = 2035;
  renderResults();
}

const LEVERS = [
  { key: "fuel_threshold_t", type: "select", label: "Umbral de diésel para entrar al SEIA",
    help: "Sobre este umbral, el proyecto pasa por evaluación con participación ciudadana.",
    options: [[80, "80 t (antes del DS 17)"], [500, "500 t"], [1000, "1.000 t (hoy)"], [3000, "3.000 t"]] },
  { key: "cumulative", type: "bool", label: "Evaluar en conjunto por zona",
    help: "El Estado revisa una vez al año cuánta red y agua quedan en cada zona, con participación." },
  { key: "water_cap_ls", type: "range", label: "Tope de agua por acuífero (solo evaluación conjunta)", min: 10, max: 200, step: 10, unit: "L/s", nullable: true },
  { key: "air_cooling_rm", type: "bool", label: "Prohibir enfriar con agua en la RM", help: "Los nuevos DC usan aire: casi no gastan agua, pero más electricidad." },
  { key: "permit_speed", type: "range", label: "Duración de los permisos", min: 0.5, max: 1.5, step: 0.1, unit: "×", help: "0,5× = el doble de rápido." },
  { key: "north_incentive", type: "range", label: "Incentivo para instalarse en Antofagasta", min: 0, max: 1, step: 0.1, unit: "" },
  { key: "community_fund_usd_mw", type: "range", label: "Fondo comunitario", min: 0, max: 50000, step: 5000, unit: "US$/MW/año" },
  { key: "transparency", type: "bool", label: "Publicar el consumo real de agua y energía", help: "Los vecinos ven el uso real, no el derecho de agua completo." },
  { key: "demand", type: "select", label: "Contexto: proyectos nuevos desde 2027", options: [["baja", "Pocos (2 al año)"], ["base", "Base (5 al año)"], ["alta", "Boom de IA (10 al año)"]] },
  { key: "climate", type: "select", label: "Contexto: recarga del acuífero a 2035", options: [["moderado", "−10%"], ["base", "−20%"], ["severo", "−40%"]] },
];
const customPolicy = { fuel_threshold_t: 1000, cumulative: false, water_cap_ls: 60, air_cooling_rm: false, permit_speed: 1,
  north_incentive: 0, community_fund_usd_mw: 0, transparency: false, demand: "base", climate: "base" };
function renderLevers() {
  const el = $("#levers");
  el.innerHTML = LEVERS.map((l) => {
    const v = customPolicy[l.key];
    if (l.type === "bool") {
      return `<div class="lever"><label class="switch"><input type="checkbox" data-k="${l.key}" ${v ? "checked" : ""}>
        <span>${esc(l.label)}<small>${esc(l.help || "")}</small></span></label></div>`;
    }
    if (l.type === "select") {
      return `<div class="lever"><label for="lv-${l.key}">${esc(l.label)}</label>
        <select id="lv-${l.key}" data-k="${l.key}">${l.options.map(([ov, ol]) => `<option value="${ov}" ${String(ov) === String(v) ? "selected" : ""}>${esc(ol)}</option>`).join("")}</select>
        ${l.help ? `<small>${esc(l.help)}</small>` : ""}</div>`;
    }
    return `<div class="lever"><label for="lv-${l.key}">${esc(l.label)} <output id="out-${l.key}">${fmt(v, l.step < 1 ? 1 : 0)} ${l.unit}</output></label>
      <input type="range" id="lv-${l.key}" data-k="${l.key}" min="${l.min}" max="${l.max}" step="${l.step}" value="${v}">
      ${l.help ? `<small>${esc(l.help)}</small>` : ""}</div>`;
  }).join("");
  el.querySelectorAll("[data-k]").forEach((inp) => inp.addEventListener("input", () => {
    const l = LEVERS.find((x) => x.key === inp.dataset.k);
    let val = inp.type === "checkbox" ? inp.checked : inp.value;
    if (l.type === "range") val = Number(val);
    if (l.type === "select" && l.key === "fuel_threshold_t") val = Number(val);
    customPolicy[l.key] = val;
    const out = $(`#out-${l.key}`);
    if (out) out.textContent = `${fmt(val, l.step < 1 ? 1 : 0)} ${l.unit}`;
  }));
  $("#runCustom").addEventListener("click", runCustom);
}
async function runCustom() {
  const btn = $("#runCustom");
  btn.disabled = true;
  $("#customMsg").textContent = "Simulando 100 futuros…";
  try {
    const pol = { ...customPolicy };
    if (!pol.cumulative) pol.water_cap_ls = null;
    S.results.custom = await api("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ policy: pol }) });
    $("#customMsg").textContent = "Listo. Resultados abajo.";
    await selectScenario("custom", true);
  } catch (e) {
    $("#customMsg").textContent = `Error: ${e.message}`;
  } finally {
    btn.disabled = false;
  }
}

// ------------------------------------------------------------ 3. resultados
function setupYearSeg() {
  document.querySelectorAll(".seg button").forEach((b) => b.addEventListener("click", () => {
    S.year = Number(b.dataset.year);
    document.querySelectorAll(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderTiles();
    renderCommuneTable();
  }));
}
function renderResults() {
  const base = S.selected === "status_quo";
  $("#who").innerHTML = base
    ? `<span><i style="background:${css("--s1")}"></i><b>Como hoy</b></span><span class="sub" style="margin:0">Elige otra regla arriba para comparar.</span>`
    : `<span><i style="background:${css("--s2")}"></i><b>${esc(scenName(S.selected))}</b></span><span>vs</span>
       <span><i style="background:${css("--s1")}"></i>Como hoy</span>`;
  $("#resultsLead").textContent = base
    ? "Qué pasa si seguimos aprobando data centers uno por uno. Valores típicos (mediana de 200 futuros simulados)."
    : `Qué cambia con "${scenName(S.selected)}" respecto de seguir como hoy. Valores típicos (mediana de los futuros simulados).`;
  renderTiles();
  renderCharts();
  updateMap();
  renderCommuneTable();
}

const TILES = [
  { key: "it_chile", label: "Data centers operando en Chile", unit: "MW", good: null,
    eq: (r, y) => `≈ ${fmt(100 * r.series.dc_share_national.p50[yi(y)], 1)}% de la electricidad del país` },
  { key: "water_ls_rm", label: "Agua que usan en la RM", unit: "L/s", good: false,
    eq: (r, y) => `= agua de ${fmt(r.series.water_ls_rm.p50[yi(y)] * 86400 / 500)} hogares (promedio anual)` },
  { key: "households_500m", label: "Hogares a menos de 500 m de un DC grande", unit: "", good: false,
    eq: (r, y) => `≈ ${fmt(r.series.households_500m.p50[yi(y)] * 3)} personas · estimación aproximada` },
  { key: "conflict_rm", label: "Hogares movilizados en contra", unit: "%", scale: 100, good: false,
    eq: () => "de los hogares de la RM con algún DC cerca o en su comuna" },
  { key: "litigations", label: "Juicios contra proyectos", unit: "", good: false,
    eq: () => "acumulados desde 2012" },
  { key: "bill_pct", label: "Alza de la cuenta de la luz", unit: "%", good: false, hyp: true, d: 1,
    eq: () => "respecto de 2025, por la demanda de los DC" },
  { key: "waitlist_mw", label: "Proyectos esperando conexión", unit: "MW", good: false,
    eq: (r, y) => `${fmt(r.series.waitlist_n.p50[yi(y)])} proyectos sin espacio en la red` },
  { key: "invest_realized", label: "Inversión materializada", unit: "money", good: true,
    eq: (r, y) => `perdida (se fue de Chile): ${money(r.series.invest_lost.p50[yi(y)])}` },
  { key: "jobs_oper", label: "Empleos de operación", unit: "", good: true,
    eq: (r, y) => `+ ${fmt(r.series.jobs_build.p50[yi(y)])} empleos de construcción ese año` },
];
function renderTiles() {
  const r = S.results[S.selected];
  const b = S.results.status_quo;
  if (!r || !b) return;
  const y = S.year;
  $("#tiles").innerHTML = TILES.map((t) => {
    const sc = t.scale || 1;
    const s = r.series[t.key];
    const v = s.p50[yi(y)] * sc;
    const lo = s.p5[yi(y)] * sc;
    const hi = s.p95[yi(y)] * sc;
    const d = t.d || 0;
    const valTxt = t.unit === "money" ? money(v) : `${fmt(v, d)}<small>${t.unit}</small>`;
    let delta = "";
    if (S.selected !== "status_quo") {
      const bv = b.series[t.key].p50[yi(y)] * sc;
      const dv = v - bv;
      const rel = bv ? dv / Math.abs(bv) : 0;
      const tiny = Math.abs(rel) < 0.02 && Math.abs(dv) < (t.unit === "%" ? 0.5 : 1);
      if (tiny) delta = `<span class="delta flat">= igual que como hoy</span>`;
      else {
        const up = dv > 0;
        const cls = t.good === null ? "flat" : (up === t.good ? "good" : "bad");
        const amount = t.unit === "money" ? money(Math.abs(dv))
          : t.unit === "%" ? `${fmt(Math.abs(dv), d || (Math.abs(dv) < 1 ? 1 : 0))} puntos`
          : `${fmt(Math.abs(dv), d)} ${t.unit}`;
        const relTxt = `${up ? "+" : "−"}${fmt(Math.abs(rel) * 100, Math.abs(rel) < 0.1 ? 1 : 0)}%`;
        delta = `<span class="delta ${cls}">${up ? "▲" : "▼"} ${up ? "más" : "menos"}: ${amount}${Math.abs(rel) < 10 ? ` (${relTxt})` : ""} vs como hoy</span>`;
      }
    }
    const rangeTxt = t.unit === "money" ? `${money(lo)} – ${money(hi)}` : `${fmt(lo, d)}–${fmt(hi, d)} ${t.unit}`;
    return `<div class="card tile">
      <div class="lab"><span>${esc(t.label)} · ${y}</span>${t.hyp ? '<span class="hyp-badge" title="No hay estudio chileno del efecto en la tarifa: es una hipótesis con rango amplio.">hipótesis</span>' : ""}</div>
      <div class="val">${valTxt}</div>
      ${delta}
      <div class="eq">${t.eq(r, y)}</div>
      <div class="range" title="El 90% de los futuros simulados cae en este rango">Rango probable: ${rangeTxt}</div>
    </div>`;
  }).join("");
}

const CHARTS = [
  { key: "demand_chile_dec", title: "Electricidad que consumen los data centers en Chile", unit: "MW",
    sub: "Potencia media de diciembre. Los puntos marcan el dato 2025 y la proyección oficial del CEN para 2030.",
    points: [{ x: 2025, y: 325, label: "CEN 2025" }, { x: 2030, y: 1207, label: "Proyección CEN 2030" }] },
  { key: "waitlist_mw", title: "Proyectos esperando conexión a la red", unit: "MW",
    sub: "MW de data centers que pidieron conexión y no tienen espacio. Dato real 2026: 1.420 MW.",
    points: [{ x: 2026, y: 1420, label: "CEN 2026" }] },
  { key: "water_ls_rm", title: "Agua que usan los data centers en la RM", unit: "L/s",
    sub: "Litros por segundo, promedio del año. 1 L/s ≈ agua de 170 hogares." },
  { key: "conflict_rm", title: "Hogares de la RM movilizados contra data centers", unit: "%", scale: 100,
    sub: "Porcentaje de hogares de comunas con data centers dispuestos a oponerse activamente." },
  { key: "litigations", title: "Juicios contra proyectos (acumulado)", unit: "casos",
    sub: "Reclamaciones y recursos ante tribunales desde 2012. Dato real: 2 a 2026." , points: [{ x: 2026, y: 2, label: "Real 2026" }] },
  { key: "invest_realized", title: "Inversión materializada (acumulada)", unit: "MUS$",
    sub: "Millones de dólares de proyectos que llegaron a construirse." },
];
function renderCharts() {
  const r = S.results[S.selected];
  const b = S.results.status_quo;
  const el = $("#charts");
  const base = S.selected === "status_quo";
  el.innerHTML = CHARTS.map((c, i) => `<div class="card">
      <h3>${esc(c.title)}</h3><p class="sub">${esc(c.sub)}</p>
      <div class="legend">
        <span><i style="background:${css("--s1")}"></i>Como hoy</span>
        ${base ? "" : `<span><i style="background:${css("--s2")}"></i>${esc(scenName(S.selected))}</span>`}
        <span><i class="band" style="background:${css("--s1-wash")}"></i>90% de los futuros</span>
        ${c.points ? '<span><i class="dot"></i>Dato o proyección oficial</span>' : ""}
      </div>
      <div class="chart-box"><canvas id="ch${i}"></canvas></div></div>`).join("");
  CHARTS.forEach((c, i) => {
    const sc = c.scale || 1;
    const scale = (q) => ({ p5: q.p5.map((x) => x * sc), p50: q.p50.map((x) => x * sc), p95: q.p95.map((x) => x * sc) });
    const series = [{ label: "Como hoy", color: css("--s1"), wash: css("--s1-wash"), data: scale(b.series[c.key]) }];
    if (!base) series.push({ label: scenName(S.selected), color: css("--s2"), wash: css("--s2-wash"), data: scale(r.series[c.key]) });
    lineChart(`ch${i}`, { years: S.meta.years, unit: c.unit, series, points: c.points, history: true });
  });
}

// ------------------------------------------------------------ gráficos de línea con franja
const historyPlugin = {
  id: "history",
  beforeDraw(chart, _args, opts) {
    if (!opts || !opts.on) return;
    const { ctx, chartArea: a, scales: { x } } = chart;
    const xNow = x.getPixelForValue(2026.85);
    ctx.save();
    ctx.fillStyle = css("--neutral-bg");
    ctx.fillRect(a.left, a.top, Math.max(0, xNow - a.left), a.bottom - a.top);
    ctx.strokeStyle = css("--axis");
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(xNow, a.top); ctx.lineTo(xNow, a.bottom); ctx.stroke();
    ctx.fillStyle = css("--muted");
    ctx.font = "12px system-ui, sans-serif";
    ctx.textAlign = "right"; ctx.fillText("historia", xNow - 6, a.top + 14);
    ctx.textAlign = "left"; ctx.fillText("futuro simulado", xNow + 6, a.top + 14);
    ctx.restore();
  },
};
function lineChart(id, { years, unit, series, points, history }) {
  if (charts[id]) charts[id].destroy();
  const ink2 = css("--ink-2"); const muted = css("--muted"); const grid = css("--grid");
  const datasets = [];
  series.forEach((s) => {
    const n = s.cut || years.length;
    const pts = (arr) => years.slice(0, n).map((y, i) => ({ x: y, y: arr[i] }));
    datasets.push({ label: `${s.label}__p5`, data: pts(s.data.p5), borderWidth: 0, pointRadius: 0, fill: false, _band: true });
    datasets.push({ label: `${s.label}__p95`, data: pts(s.data.p95), borderWidth: 0, pointRadius: 0, backgroundColor: s.wash, fill: "-1", _band: true });
    datasets.push({ label: s.label, data: pts(s.data.p50), borderColor: s.color, backgroundColor: s.color, borderWidth: 2,
      pointRadius: 0, pointHoverRadius: 5, pointHitRadius: 10, tension: 0.25, fill: false, _p5: s.data.p5, _p95: s.data.p95 });
  });
  if (points) {
    datasets.push({ type: "scatter", label: "Dato real", data: points.map((p) => ({ x: p.x, y: p.y, _label: p.label })),
      backgroundColor: css("--ink"), borderColor: css("--surface"), borderWidth: 2, pointRadius: 5, pointHoverRadius: 7 });
  }
  charts[id] = new Chart(document.getElementById(id), {
    type: "line",
    data: { datasets },
    plugins: [historyPlugin],
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "x", intersect: false },
      plugins: {
        history: { on: history },
        legend: { display: false },
        tooltip: {
          backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: ink2, borderColor: css("--axis"), borderWidth: 1,
          padding: 10, displayColors: true, boxWidth: 8, boxHeight: 8, usePointStyle: true,
          filter: (it) => !it.dataset._band,
          callbacks: {
            title: (items) => items.length ? String(Math.round(items[0].parsed.x)) : "",
            label: (it) => {
              const ds = it.dataset;
              if (ds.type === "scatter") return ` ${it.raw._label}: ${fmtAuto(it.parsed.y)} ${unit}`;
              const i = it.dataIndex;
              return ` ${ds.label}: ${fmtAuto(it.parsed.y)} ${unit}  (90%: ${fmtAuto(ds._p5[i])}–${fmtAuto(ds._p95[i])})`;
            },
          },
        },
      },
      scales: {
        x: { type: "linear", min: years[0], max: years[years.length - 1], grid: { display: false },
          border: { color: css("--axis") },
          ticks: { color: muted, stepSize: years.length > 16 ? 4 : 2, callback: (v) => String(v) } },
        y: { beginAtZero: true, grid: { color: grid }, border: { display: false },
          ticks: { color: muted, maxTicksLimit: 5, callback: (v) => fmt(v) },
          title: { display: true, text: unit, color: muted, font: { size: 12 } } },
      },
    },
  });
}

// ------------------------------------------------------------ mapa
let map, baseLayer, communeLayer, dcLayer;
const RAMP_LIGHT = ["#fde9df", "#f9c9b0", "#f4a27e", "#ee7d50", "#d95f2b", "#b0461a", "#83310f"];
const RAMP_DARK = ["#3a2218", "#5a2f1c", "#80401f", "#a85024", "#d0622d", "#ee8150", "#f6ab85"];
const METRIC_INFO = {
  c_conflict: { label: "Hogares movilizados", unit: "%", scale: 100, d: 0 },
  c_share: { label: "Electricidad comunal de DC", unit: "%", scale: 100, d: 0 },
  c_water_ls: { label: "Agua de DC", unit: "L/s", scale: 1, d: 1 },
  c_h500: { label: "Hogares a < 500 m", unit: "hogares", scale: 1, d: 0 },
  c_it: { label: "DC operando", unit: "MW", scale: 1, d: 0 },
};
function initMap() {
  map = L.map("map", { zoomControl: true, scrollWheelZoom: false, attributionControl: true }).setView([-33.45, -70.74], 10);
  setBaseLayer();
  communeLayer = L.layerGroup().addTo(map);
  dcLayer = L.layerGroup().addTo(map);
  const slider = $("#yearSlider");
  slider.addEventListener("input", () => { S.mapYear = Number(slider.value); stopPlay(); updateMap(); });
  $("#metricSel").addEventListener("change", (e) => { S.mapMetric = e.target.value; updateMap(); });
  $("#playBtn").addEventListener("click", togglePlay);
  const regions = L.control({ position: "bottomleft" });
  regions.onAdd = () => {
    const d = L.DomUtil.create("div", "leaflet-bar");
    d.style.cssText = `background:${css("--surface")};padding:4px;display:flex;gap:4px`;
    d.innerHTML = [["RM", -33.45, -70.74, 10], ["Valparaíso", -33.08, -71.58, 11], ["Antofagasta", -23.62, -70.38, 11], ["Chile", -30, -71, 5]]
      .map(([n, la, lo, z]) => `<a href="#" data-v="${la},${lo},${z}" style="width:auto;padding:0 8px;line-height:26px;height:26px;font-size:12px;color:${css("--ink")};background:${css("--surface")}">${n}</a>`).join("");
    d.querySelectorAll("a").forEach((a) => a.addEventListener("click", (e) => {
      e.preventDefault(); const [la, lo, z] = a.dataset.v.split(",").map(Number); map.setView([la, lo], z);
    }));
    L.DomEvent.disableClickPropagation(d);
    return d;
  };
  regions.addTo(map);
}
function setBaseLayer() {
  if (!map) return;
  if (baseLayer) map.removeLayer(baseLayer);
  baseLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 18,
    className: "base-tiles",
  }).addTo(map);
}
function togglePlay() {
  if (S.playing) { stopPlay(); return; }
  if (S.mapYear >= 2035) S.mapYear = 2012;
  $("#playBtn").textContent = "❚❚";
  S.playing = setInterval(() => {
    S.mapYear += 1;
    if (S.mapYear >= 2035) { S.mapYear = 2035; stopPlay(); }
    updateMap();
  }, 550);
}
function stopPlay() {
  if (S.playing) clearInterval(S.playing);
  S.playing = null;
  $("#playBtn").textContent = "▶";
}
function rampColor(t) {
  const r = isDark() ? RAMP_DARK : RAMP_LIGHT;
  const i = Math.max(0, Math.min(r.length - 1, Math.floor(t * (r.length - 1) + 0.5)));
  return r[i];
}
function dcStyle(code, mw) {
  const s1 = css("--s1");
  const r = 3 + 1.5 * Math.sqrt(mw);
  const base = { radius: r, weight: 2, color: s1, fillColor: s1, fillOpacity: 0 };
  if (code === ST.OPER) return { ...base, fillOpacity: 0.85, color: css("--surface") };
  if (code === ST.BUILD) return { ...base, fillOpacity: 0.45, weight: 3 };
  if (code === ST.PERMIT) return { ...base, fillOpacity: 0, weight: 2 };
  if (code === ST.LITIG) return { ...base, color: "#d03b3b", fillColor: "#d03b3b", fillOpacity: 0.1, weight: 2.5 };
  if (code === ST.WAIT) return { ...base, color: css("--muted"), fillOpacity: 0, dashArray: "3 4", weight: 2 };
  return null;
}
function updateMap() {
  const r = S.results[S.selected];
  if (!r || !map) return;
  const y = S.mapYear;
  $("#yearSlider").value = y;
  $("#yearLabel").textContent = y;
  $("#whenLabel").innerHTML = y < 2026
    ? "Historia real (igual en todas las reglas)."
    : y === 2026 ? "Fin de 2026: historia real hasta noviembre; diciembre ya es simulado."
    : `Futuro simulado con <b>${esc(scenName(S.selected))}</b>.`;
  const m = METRIC_INFO[S.mapMetric];
  const cm = r.communes[S.mapMetric].p50;
  let max = 0;
  cm.forEach((row) => row.forEach((v) => { max = Math.max(max, v); }));
  max = max * m.scale || 1;
  communeLayer.clearLayers();
  S.meta.communes.forEach((c, i) => {
    const v = cm[i][yi(y)] * m.scale;
    const circ = L.circle([c.lat, c.lon], {
      radius: c.radius_km * 1000, color: css("--surface"), weight: 1,
      fillColor: rampColor(v / max), fillOpacity: v > 0 ? 0.6 : 0.15,
    });
    circ.bindTooltip(`<b>${esc(c.name)}</b><br>${m.label}: ${fmt(v, m.d)} ${m.unit}`, { sticky: true });
    circ.on("click", () => showCommune(i));
    communeLayer.addLayer(circ);
  });
  // proyectos conocidos
  dcLayer.clearLayers();
  const probs = r.projects.status_prob;
  const comMode = r.projects.commune_mode;
  const knownMW = new Array(S.meta.communes.length).fill(0);
  S.meta.projects.forEach((p, i) => {
    const pr = probs[i][yi(y)];
    let code = 0; let best = -1;
    pr.forEach((v, k) => { if (v > best) { best = v; code = k; } });
    const ci = comMode[i][yi(y)];
    knownMW[ci] += pr[ST.OPER] * p.it_mw;
    const style = dcStyle(code, p.it_mw);
    if (!style) return;
    const c = S.meta.communes[ci];
    const moved = c.id !== p.commune;
    const ll = moved ? [c.lat + 0.01 * Math.sin(i), c.lon - c.radius_km / 111 * 0.9 + 0.01 * Math.cos(i)] : [p.lat, p.lon];
    const mk = L.circleMarker(ll, style);
    mk.bindTooltip(`<b>${esc(p.name)}</b> · ${fmt(p.it_mw)} MW<br>${S.meta.status_labels[code]}${moved ? ` (se mudó a ${esc(c.name)})` : ""}`);
    mk.on("click", () => showProject(i, y));
    dcLayer.addLayer(mk);
  });
  // proyectos nuevos simulados (sin nombre): diferencia entre el total comunal y los conocidos
  const cit = r.communes.c_it.p50;
  S.meta.communes.forEach((c, i) => {
    const extra = cit[i][yi(y)] - knownMW[i];
    if (y > 2026 && extra > 15) {
      const ll = [c.lat - c.radius_km / 111 * 0.5, c.lon + c.radius_km / 111 * 0.6];
      const mk = L.circleMarker(ll, { radius: 3 + 1.5 * Math.sqrt(extra), color: css("--surface"), weight: 2,
        fillColor: css("--s3"), fillOpacity: 0.85 });
      mk.bindTooltip(`<b>Nuevos proyectos simulados en ${esc(c.name)}</b><br>~${fmt(extra)} MW operando que aún no se anuncian`);
      dcLayer.addLayer(mk);
    }
  });
  renderMapLegend(max, m);
}
function renderMapLegend(max, m) {
  const ramp = (isDark() ? RAMP_DARK : RAMP_LIGHT).join(",");
  const s1 = css("--s1");
  $("#mapLegend").innerHTML = `
    <div><b>Comunas</b> · ${esc(m.label)}
      <div class="ramp" style="background:linear-gradient(90deg,${ramp})"></div>
      <div class="ramp-labels"><span>0</span><span>${fmt(max, m.d)} ${m.unit}</span></div></div>
    <div><b>Data centers</b> (tamaño = MW)</div>
    <div class="row"><span class="mk" style="background:${s1}"></span>Operando</div>
    <div class="row"><span class="mk" style="background:color-mix(in srgb, ${s1} 45%, transparent);border:3px solid ${s1}"></span>En construcción</div>
    <div class="row"><span class="mk" style="border:2px solid ${s1}"></span>En trámite</div>
    <div class="row"><span class="mk" style="border:2px dashed ${css("--muted")}"></span>Esperando conexión a la red</div>
    <div class="row"><span class="mk" style="border:2.5px solid #d03b3b"></span>En tribunales</div>
    <div class="row"><span class="mk" style="background:${css("--s3")}"></span>Proyectos futuros simulados (sin nombre)</div>`;
}
function showCommune(i) {
  const r = S.results[S.selected];
  const c = S.meta.communes[i];
  const y = S.mapYear;
  const g = (k, sc = 1) => r.communes[k].p50[i][yi(y)] * sc;
  const hh = c.households;
  $("#infoBox").innerHTML = `<h4>${esc(c.name)} · ${y}</h4>
    <div class="sub" style="margin:0 0 6px">${fmt(c.pop)} habitantes (Censo 2017) · ${fmt(hh)} hogares</div>
    <dl>
      <dt>Data centers operando</dt><dd>${fmt(g("c_it"))} MW</dd>
      <dt>Esperando red</dt><dd>${fmt(g("c_waitlist"))} MW</dd>
      <dt>Electricidad comunal que usan</dt><dd>${fmt(g("c_share", 100))}%</dd>
      <dt>Agua que usan</dt><dd>${fmt(g("c_water_ls"), 1)} L/s</dd>
      <dt>Equivale al agua de</dt><dd>${fmt(g("c_water_ls") * 86400 / 500)} hogares</dd>
      <dt>Hogares a &lt; 500 m</dt><dd>${fmt(g("c_h500"))}</dd>
      <dt>Empleos locales</dt><dd>${fmt(g("c_jobs_local"))}</dd>
      <dt>Patentes y fondos por hogar</dt><dd>US$ ${fmt((g("c_muni_usd") + g("c_fund_usd")) / hh)} /año</dd>
      <dt>NOx de diésel</dt><dd>${fmt(g("c_nox"), 1)} t/año</dd>
      <dt>Hogares movilizados</dt><dd>${fmt(g("c_conflict", 100))}%</dd>
    </dl>`;
}
function showProject(i, y) {
  const r = S.results[S.selected];
  const p = S.meta.projects[i];
  const pr = r.projects.status_prob[i][yi(y)];
  const labels = S.meta.status_labels;
  const colors = [css("--grid"), css("--s1-wash"), css("--muted"), "#d03b3b", css("--s3"), css("--s1"), css("--axis")];
  const real = { operando: "operando", construccion: "en construcción", tramitacion: "en tramitación", lista_espera: "esperando red" }[p.real_status];
  const rows = pr.map((v, k) => ({ v, k })).filter((o) => o.v >= 0.02).sort((a, b) => b.v - a.v);
  $("#infoBox").innerHTML = `<div class="pop"><h4>${esc(p.name)}</h4>
    <div class="op">${esc(p.operator)} · ${fmt(p.it_mw, p.it_mw % 1 ? 1 : 0)} MW · enfriamiento por ${esc(p.cooling)}${p.fuel_t ? ` · ${fmt(p.fuel_t)} t de diésel` : ""}${p.dist_homes_m ? ` · ${fmt(p.dist_homes_m)} m de viviendas` : ""}</div>
    ${real ? `<div>Estado real a nov-2026: <b>${real}</b></div>` : ""}
    <div style="margin-top:6px">En ${y}, en los futuros simulados:</div>
    <div class="bar">${rows.map((o) => `<span style="width:${100 * o.v}%;background:${colors[o.k]}" title="${labels[o.k]}"></span>`).join("")}</div>
    <dl>${rows.map((o) => `<dt>${labels[o.k]}</dt><dd>${fmt(100 * o.v)}%</dd>`).join("")}</dl>
    ${p.hist.length ? `<ul>${p.hist.map((h) => `<li>${esc(h)}</li>`).join("")}</ul>` : ""}
    <div class="sub" style="margin:8px 0 0">${esc(p.src)}</div></div>`;
}

// ------------------------------------------------------------ tabla por comuna
let sortKey = "it_mw";
function communeRows(res, y) {
  const cm = res.communes;
  return S.meta.communes.map((c, i) => {
    const g = (k) => cm[k].p50[i][yi(y)];
    const hh = c.households;
    return { i, id: c.id, name: c.name, it_mw: g("c_it"), wait: g("c_waitlist"), share: 100 * g("c_share"),
      water: g("c_water_ls"), h500: g("c_h500"), jobs: g("c_jobs_local"),
      usd: (g("c_muni_usd") + g("c_fund_usd")) / hh, conflict: 100 * g("c_conflict") };
  });
}
function balance(r) {
  if (r.it_mw < 1 && r.wait < 1) return '<span class="pill neutral">Sin DC</span>';
  if (r.conflict >= 15 && r.usd < 30) return '<span class="pill bad" title="Muchos hogares movilizados y pocos beneficios por hogar">▼ Más cargas</span>';
  if (r.usd >= 30 && r.conflict < 10) return '<span class="pill good" title="Beneficios por hogar relevantes y poco conflicto">▲ Más beneficios</span>';
  return '<span class="pill warn" title="Cargas y beneficios en tensión">◆ Mixto</span>';
}
function renderCommuneTable() {
  const r = S.results[S.selected];
  const b = S.results.status_quo;
  if (!r || !b) return;
  const y = S.year;
  const rows = communeRows(r, y).filter((x) => x.it_mw >= 1 || x.wait >= 1);
  const baseRows = communeRows(b, y);
  rows.sort((a, c) => (c[sortKey] ?? 0) - (a[sortKey] ?? 0));
  const maxMW = Math.max(...rows.map((x) => x.it_mw), 1);
  const cmp = S.selected !== "status_quo";
  $("#tableSub").textContent = `Año ${y}, regla "${scenName(S.selected)}". Toca un encabezado para ordenar.` +
    (cmp ? " Las flechas comparan con seguir como hoy." : "");
  const dlt = (v, bv, goodUp, d = 0) => {
    if (!cmp) return "";
    const dv = v - bv;
    if (Math.abs(dv) < (d ? 0.5 : 1)) return "";
    const good = goodUp === null ? null : (dv > 0) === goodUp;
    return ` <span class="delta ${good === null ? "flat" : good ? "good" : "bad"}" style="font-size:12px">${dv > 0 ? "▲" : "▼"}${fmt(Math.abs(dv), d)}</span>`;
  };
  const cols = [
    ["name", "Comuna"], ["it_mw", "DC operando (MW)"], ["wait", "Esperando red (MW)"], ["share", "Electricidad de la comuna que usan"],
    ["water", "Agua (L/s)"], ["h500", "Hogares a menos de 500 m"], ["jobs", "Empleos locales"], ["usd", "US$ por hogar al año (patentes y fondos)"],
    ["conflict", "Hogares movilizados"], ["bal", "Balance"],
  ];
  $("#communeTable").innerHTML = `<thead><tr>${cols.map(([k, l]) => `<th data-k="${k}" ${k === sortKey ? 'aria-sort="descending"' : ""}>${l}${k === sortKey ? " ↓" : ""}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((x) => {
      const bx = baseRows[x.i];
      return `<tr>
      <td><b>${esc(x.name)}</b></td>
      <td><span class="cell-bar">${fmt(x.it_mw)}${dlt(x.it_mw, bx.it_mw, null)}<i style="width:${Math.max(2, 60 * x.it_mw / maxMW)}px"></i></span></td>
      <td>${fmt(x.wait)}</td>
      <td>${fmt(x.share)}%</td>
      <td>${fmt(x.water, 1)}${dlt(x.water, bx.water, false, 1)}</td>
      <td>${fmt(x.h500)}</td>
      <td>${fmt(x.jobs)}</td>
      <td>${fmt(x.usd)}</td>
      <td>${fmt(x.conflict)}%${dlt(x.conflict, bx.conflict, false)}</td>
      <td>${balance(x)}</td></tr>`;
    }).join("")}</tbody>`;
  $("#communeTable").querySelectorAll("th").forEach((th) => th.addEventListener("click", () => {
    if (th.dataset.k === "name" || th.dataset.k === "bal") return;
    sortKey = th.dataset.k; renderCommuneTable();
  }));
}

// ------------------------------------------------------------ 4. hipótesis
function renderHypotheses() {
  const vClass = { "Se confirma": "good", "Parcialmente": "warn", "No se confirma": "neutral" };
  const vIcon = { "Se confirma": "✓", "Parcialmente": "◐", "No se confirma": "✗" };
  $("#hyps").innerHTML = S.insights.hypotheses.map((h) => `<div class="card hyp">
    <div><span class="pill ${vClass[h.verdict]}">${vIcon[h.verdict]} ${esc(h.verdict)}</span></div>
    <div class="claim">“${esc(h.claim)}”</div>
    <div class="ev">${esc(h.evidence)}</div>
    <div class="take">${esc(h.takeaway)}</div>
    <div class="src">${esc(h.source)}</div>
    <button class="linkish" data-s="${h.scenario}">Ver “${esc(scenName(h.scenario))}” en el mapa →</button>
  </div>`).join("");
  $("#hyps").querySelectorAll("[data-s]").forEach((b) => b.addEventListener("click", () => selectScenario(b.dataset.s, true)));
}

// ------------------------------------------------------------ supuestos
function renderParams() {
  const kindPill = { dato: "good", calibrado: "warn", supuesto: "neutral" };
  const groups = {};
  S.meta.params.forEach((p) => { (groups[p.group] = groups[p.group] || []).push(p); });
  const nd = (x) => (Math.abs(x) < 1 && x !== 0 ? 2 : Math.abs(x) < 10 ? 1 : 0);
  $("#paramsTable").innerHTML = `<thead><tr><th>Grupo</th><th>Parámetro</th><th>Valor</th><th>Rango</th><th>Tipo</th><th>Fuente</th></tr></thead><tbody>${
    Object.entries(groups).map(([g, ps]) => ps.map((p) => `<tr><td>${esc(g)}</td><td>${esc(p.label)}</td>
      <td>${fmt(p.base, nd(p.base))} ${esc(p.unit === "—" ? "" : p.unit)}</td><td>${fmt(p.low, nd(p.low))}–${fmt(p.high, nd(p.high))}${p.sample ? ' <span class="sub" title="Se sortea en cada simulación">· incierto</span>' : ""}</td>
      <td><span class="pill ${kindPill[p.kind]}">${esc(p.kind)}</span></td><td>${esc(p.src)}</td></tr>`).join("")).join("")}</tbody>`;
}
function renderProjects() {
  const real = { operando: "operando", construccion: "en construcción", tramitacion: "en tramitación", lista_espera: "esperando red" };
  const cname = Object.fromEntries(S.meta.communes.map((c) => [c.id, c.name]));
  $("#projectsTable").innerHTML = `<thead><tr><th>Proyecto</th><th>Operador</th><th>Comuna</th><th>MW TI</th><th>Enfriamiento</th><th>Estado nov-2026</th><th>Fuente / supuesto</th></tr></thead><tbody>${
    S.meta.projects.map((p) => `<tr><td>${esc(p.name)}</td><td style="text-align:left">${esc(p.operator)}</td><td style="text-align:left">${esc(cname[p.commune])}</td>
      <td>${fmt(p.it_mw, p.it_mw % 1 ? 1 : 0)}</td><td style="text-align:left">${esc(p.cooling)}</td>
      <td style="text-align:left">${p.real_status ? real[p.real_status] : "—"}</td><td>${esc(p.src)}</td></tr>`).join("")}</tbody>`;
}
