/* Aterriza: portada. Una sola cosa interactiva: elegir una regla y ver seis cifras de 2035. */
"use strict";
document.documentElement.classList.add("js");

const nf = (d = 0) => new Intl.NumberFormat("es-CL", { maximumFractionDigits: d, minimumFractionDigits: d });
const fmt = (x, d = 0) => nf(d).format(x);
const money = (musd) => (musd >= 1000 ? `US$ ${fmt(musd / 1000, 1)} mil millones` : `US$ ${fmt(musd)} millones`);
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

// clave -> cómo mostrarla y si "más" es mejor (null = ni mejor ni peor)
const BANDS = {
  it_chile: { show: (v) => `${fmt(v)} MW`, goodUp: null,
    note: (t) => `≈ ${fmt(100 * t.values.dc_share_national.p50, 1)}% de la electricidad de Chile` },
  water_ls_rm: { show: (v) => `${fmt(v)} L/s`, goodUp: false,
    note: (t) => `el agua de ${fmt(t.values.water_ls_rm.p50 * 86400 / 500)} hogares` },
  conflict_rm: { show: (v) => `${fmt(100 * v)}%`, goodUp: false, points: true, scale: 100 },
  litigations: { show: (v) => fmt(v), goodUp: false },
  invest_lost: { show: money, goodUp: false },
  bill_pct: { show: (v) => `+${fmt(v, 1)}%`, goodUp: false, points: true, scale: 1 },
};

let story = null;
let current = "status_quo";

fetch("/api/story")
  .then((r) => r.json())
  .then((d) => { story = d; render(false); fillFindings(); fillProof(); })
  .catch(() => {
    document.querySelectorAll(".band .val").forEach((el) => { el.textContent = "…"; });
    document.querySelector("[data-note]").textContent = "No se pudo cargar la simulación. ¿Está corriendo el servidor?";
  });

// ---------------------------------------------------------------- reglas
const tabs = [...document.querySelectorAll("#tabs [role=tab]")];
tabs.forEach((b) => {
  b.addEventListener("click", () => select(b.dataset.id));
  b.addEventListener("keydown", (e) => {
    const i = tabs.indexOf(b);
    const next = e.key === "ArrowDown" || e.key === "ArrowRight" ? i + 1 : e.key === "ArrowUp" || e.key === "ArrowLeft" ? i - 1 : null;
    if (next === null) return;
    e.preventDefault();
    const t = tabs[(next + tabs.length) % tabs.length];
    t.focus();
    select(t.dataset.id);
  });
});
document.querySelectorAll("[data-tab]").forEach((a) => a.addEventListener("click", () => select(a.dataset.tab)));

function select(id) {
  current = id;
  tabs.forEach((b) => {
    const on = b.dataset.id === id;
    b.setAttribute("aria-selected", String(on));
    b.tabIndex = on ? 0 : -1;
  });
  document.getElementById("simMap").href = `/explorar?s=${id}`;
  if (story) render(true);
}

function render(animate) {
  const tab = story.tabs.find((t) => t.id === current);
  const base = story.tabs.find((t) => t.id === "status_quo");
  let summary = tab.summary;
  if (current === "paquete") {
    const f = (story.findings || []).find((x) => x.id === "paquete");
    if (f) summary += ` <b>Mejora las seis cifras a la vez en ${f.stat} de los futuros.</b>`;
  }
  document.getElementById("ruleSummary").innerHTML = summary;
  document.querySelectorAll(".band").forEach((band) => {
    const k = band.dataset.k;
    const spec = BANDS[k];
    const v = tab.values[k].p50;
    const b = base.values[k].p50;
    const val = band.querySelector(".val");
    val.textContent = spec.show(v);
    if (animate && !reduced) { val.classList.remove("tick"); void val.offsetWidth; val.classList.add("tick"); }
    if (spec.note) band.querySelector(".note").textContent = spec.note(tab);
    band.querySelector(".delta").innerHTML = current === "status_quo"
      ? "punto de comparación para las otras reglas" : delta(spec, v, b);
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

// ---------------------------------------------------------------- hallazgos y prueba
function fillFindings() {
  const byId = Object.fromEntries((story.findings || []).map((f) => [f.id, f]));
  const set = (id, txt) => { const el = document.querySelector(`[data-f="${id}"]`); if (el && txt) el.textContent = txt; };
  if (byId.permisos) set("permisos", byId.permisos.stat.replace("+", ""));
  if (byId.cerrillos) set("cerrillos", byId.cerrillos.stat.replace(" → ", " a "));
  if (byId.boom) set("boom", byId.boom.stat.replace("×", ""));
}

function fillProof() {
  document.getElementById("passed").textContent = `${story.passed} de ${story.total}`;
  const LABEL = {
    rm_2021: [2021, "Electricidad de los data centers de Santiago", "MW"],
    google_water: [2024, "Agua usada por Google en Quilicura", "ML"],
    rm_2025: [2025, "Electricidad de los data centers de Santiago", "MW"],
    waitlist: [2026, "MW esperando conexión a la red", ""],
    litigations: [2026, "Juicios contra data centers desde 2012", ""],
    conflict_pattern: [2026, "Comunas con vecinos organizados", ""],
  };
  let lastYear = null;
  const rows = story.checks.map((c) => {
    const [year, label, unit] = LABEL[c.id];
    let real; let model;
    if (c.id === "conflict_pattern") { real = String(c.observed.length); model = `${c.sim.hits} de ${c.observed.length}`; }
    else { real = `${fmt(c.observed)}${unit ? " " + unit : ""}`; model = `${fmt(c.sim.p50)}${unit ? " " + unit : ""}`; }
    const y = year === lastYear ? "" : year;
    lastYear = year;
    return `<tr><td>${y}</td><td>${label}</td><td data-label="Real">${real}</td><td data-label="Modelo">${model}</td><td>${c.src}</td></tr>`;
  });
  document.getElementById("proofRows").innerHTML = rows.join("");
}

// ---------------------------------------------------------------- entradas al hacer scroll
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("in");
    io.unobserve(e.target);
  });
}, { threshold: 0.18 });
document.querySelectorAll("section").forEach((sec) => {
  sec.querySelectorAll("[data-rise]").forEach((el, i) => {
    el.style.transitionDelay = `${i * 80}ms`;
    io.observe(el);
  });
});
document.querySelectorAll(".chapter").forEach((c) => io.observe(c));
