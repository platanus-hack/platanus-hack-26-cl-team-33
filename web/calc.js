/* Aterriza: calculadora de evaluación conjunta. Suma todos los data centers de una comuna y deja
   cambiar desde 2027 el enfriamiento de los que aún no operan. Usa $, fmt y esc de story.js, que
   llama a initCalc(meta) al llegar /api/meta. */
"use strict";

(() => {
  const CAL = { meta: null, ci: -1, year: 2035, cool: {}, base: null, res: null, shown: "{}", busy: false,
    cache: new Map(), switchable: new Set() };
  const REAL = { operando: "operando", construccion: "en construcción", tramitacion: "en trámite", lista_espera: "esperando red" };
  const COOL = { evaporativo: "con agua", aire: "con aire", hibrido: "híbrido" };
  const OPER = 5;  // código de "operando" en status_prob
  const CACHE_MAX = 6;  // resultados con cambios guardados en el navegador

  // cifras: MW con un decimal solo si es chico y lo tiene; L/s con un decimal bajo 10
  const mwTxt = (x) => fmt(x, Math.abs(x) < 30 && Math.round(x * 10) % 10 ? 1 : 0);
  const lsTxt = (x) => (Math.abs(x) < 0.05 ? "0" : fmt(x, Math.abs(x) < 10 ? 1 : 0));
  const pct = (x) => { const a = 100 * x; return `${fmt(a, Math.abs(a) < 10 && Math.round(a * 10) % 10 ? 1 : 0)}%`; };
  const sign = (x, txt) => `${x > 0 ? "+" : "−"}${txt(Math.abs(x))}`;
  const val = (v, f) => (typeof v === "number" && Number.isFinite(v) ? f(v) : esc(v));
  const plural = (n, one, many) => `${fmt(n)} ${n === 1 ? one : many}`;
  const keyOf = (changes) => JSON.stringify(Object.keys(changes).sort().reduce((o, k) => ({ ...o, [k]: changes[k] }), {}));

  // ---------------------------------------------------------------- arranque (lo llama story.js)
  function initCalc(meta) {
    CAL.meta = meta;
    CAL.switchable = new Set(meta.calc.projects);
    document.querySelectorAll("[data-calc-n]").forEach((el) => { el.textContent = fmt(meta.calc.n); });
    // solo comunas con al menos un proyecto con nombre público; los anónimos igual suman
    const count = {};
    meta.projects.forEach((p) => {
      count[p.commune] = count[p.commune] || { known: 0, all: 0 };
      count[p.commune].all += 1;
      if (!p.anonymous) count[p.commune].known += 1;
    });
    const opts = meta.communes.map((c, i) => ({ c, i })).filter(({ c }) => count[c.id] && count[c.id].known)
      .sort((a, b) => a.c.name.localeCompare(b.c.name, "es"));
    const sel = $("#calcCommune");
    sel.innerHTML = opts.map(({ c, i }) => `<option value="${i}">${esc(c.name)} · ${plural(count[c.id].all, "proyecto", "proyectos")}</option>`).join("");
    const start = opts.find(({ c }) => c.id === "quilicura") || opts[0];
    sel.value = String(start.i);
    sel.disabled = false;
    sel.addEventListener("change", () => setCommune(Number(sel.value)));
    $("#calcProjects").addEventListener("click", (e) => {
      const b = e.target.closest("[data-cool]");
      if (b && !CAL.busy) setCooling(b.dataset.pid, b.dataset.cool);
    });
    $("#calcForm").addEventListener("submit", (e) => { e.preventDefault(); run(); });
    document.querySelectorAll("[data-cyear]").forEach((b) => b.addEventListener("click", () => {
      CAL.year = Number(b.dataset.cyear);
      document.querySelectorAll("[data-cyear]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      renderResults();
    }));
    setCommune(start.i);
    loadBase();
  }

  // lo declarado (seguir como hoy en los mismos futuros que corre un cambio): llega al instante
  function loadBase() {
    post({}).then((res) => {
      CAL.base = res;
      if (CAL.shown === "{}") CAL.res = res;
      $("#calcRun").disabled = false;
      renderResults();
      updateNote();
    }).catch(() => {
      $("#calcSummary").textContent = "No se pudo cargar la calculadora. Recarga la página para reintentar.";
    });
  }

  async function post(cooling) {
    const r = await fetch("/api/calc", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cooling }) });
    const res = await r.json().catch(() => ({}));
    if (!r.ok) {
      const d = res.detail;
      throw new Error(typeof d === "string" ? d : "intenta de nuevo");
    }
    return res;
  }

  // ---------------------------------------------------------------- comuna y proyectos
  const projectsOf = (ci) => CAL.meta.projects.map((p, i) => ({ p, i })).filter(({ p }) => p.commune === CAL.meta.communes[ci].id);
  const canSwitch = (p) => CAL.switchable.has(p.id) && !p.anonymous;
  const current = (p) => CAL.cool[p.id] || p.cooling_now;

  // cambios respecto de lo declarado: solo agua o aire, solo en los que aún no operan
  function changes() {
    const out = {};
    CAL.meta.projects.forEach((p) => {
      const c = CAL.cool[p.id];
      if (c && c !== p.cooling_now && canSwitch(p)) out[p.id] = c;
    });
    return out;
  }

  function setCommune(ci) {
    CAL.ci = ci;
    CAL.cool = {};  // una comuna a la vez: al cambiarla se vuelve a lo declarado
    CAL.shown = "{}";
    CAL.res = CAL.base;
    renderTable();
    renderResults();
    updateNote();
  }

  function setCooling(pid, cool) {
    const p = CAL.meta.projects.find((x) => x.id === pid);
    if (!p || !canSwitch(p)) return;
    CAL.cool[pid] = cool;
    document.querySelectorAll(`[data-pid="${pid}"]`).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cool === cool)));
    const was = document.querySelector(`[data-was="${pid}"]`);
    if (was) was.textContent = cool !== p.cooling_now ? `declarado ${COOL[p.cooling_now]}; cambia desde 2027` : wasText(p);
    updateNote();
  }

  const wasText = (p) => (p.cooling !== p.cooling_now ? `antes ${COOL[p.cooling] || p.cooling}` : "");

  function statusText(p) {
    if (p.real_status) return REAL[p.real_status] || p.real_status;
    return p.pre_existing ? "operando" : "anunciado";
  }

  // el trade-off a operación plena, con los valores centrales del modelo (params.py): cuánta agua
  // usa enfriando con agua y cuánta electricidad más pide enfriando con aire. Es solo ingeniería;
  // los resultados de la derecha además incluyen permisos, la fila de la red y tribunales.
  function tradeOff(p) {
    const v = Object.fromEntries(CAL.meta.params.map((x) => [x.key, x.base]));
    const mw = p.it_mw * v.lf_max;  // MW de servidores con la carga típica
    const water = mw * v.pue_evap * 1000 * v.wue_evap / 3600;
    const extra = mw * (v.pue_air - v.pue_evap);
    const peak = mw * (v.pue_air * v.peak_pue_ratio - v.pue_evap * (1 + 0.6 * (v.peak_pue_ratio - 1)));
    const homes = water * 86400 / 500;
    return `A plena carga: con agua usa ~${lsTxt(water)} L/s (el agua de ${fmt(homes)} hogares); con aire, ~${mwTxt(extra)} MW más de electricidad (~${mwTxt(peak)} MW en verano).`;
  }

  function coolCell(p) {
    if (!canSwitch(p)) return esc(COOL[p.cooling_now] || p.cooling_now);
    const c = current(p);
    const btn = (k, label) => `<button type="button" data-pid="${esc(p.id)}" data-cool="${k}" aria-pressed="${c === k}">${label}</button>`;
    const note = c !== p.cooling_now ? `declarado ${COOL[p.cooling_now]}; cambia desde 2027` : wasText(p);
    return `<div class="seg" role="group" aria-label="Enfriamiento de ${esc(p.name)} desde 2027">${btn("evaporativo", "Agua")}${btn("aire", "Aire")}</div>`
      + `<span class="range" data-was="${esc(p.id)}">${esc(note)}</span>`
      + `<span class="range calc-trade">${esc(tradeOff(p))}</span>`;
  }

  // lo declarado al SEA, si existe; si no, de dónde sale lo que usamos
  function seaCell(p) {
    const s = p.sea;
    if (!s) return `<span class="range">sin dato declarado</span>${p.src ? `<span class="range">${esc(p.src)}</span>` : ""}`;
    const parts = [];
    if (s.water_max_ls != null) parts.push(`hasta ${val(s.water_max_ls, lsTxt)} L/s`);
    if (s.water_avg_ls != null) parts.push(`${val(s.water_avg_ls, lsTxt)} L/s en promedio`);
    if (s.water_rights_ls != null) parts.push(`derechos por ${val(s.water_rights_ls, lsTxt)} L/s`);
    if (s.it_mw != null) parts.push(`${val(s.it_mw, mwTxt)} MW de servidores`);
    if (s.facility_mw != null) parts.push(`${val(s.facility_mw, mwTxt)} MW en total`);
    if (s.cooling) parts.push(esc(COOL[s.cooling] || s.cooling));
    if (s.instrument) parts.push(esc(s.instrument));
    if (s.rca) parts.push(`RCA ${esc(s.rca)}`);
    else if (s.expediente) parts.push(`expediente ${esc(s.expediente)}`);
    if (typeof s.url === "string" && /^https?:\/\//.test(s.url)) parts.push(`<a href="${esc(s.url)}" target="_blank" rel="noopener">fuente</a>`);
    const extra = [s.confidence ? `confianza ${esc(s.confidence)}` : "", s.note ? esc(s.note) : ""].filter(Boolean).join(". ");
    return `${parts.join(" · ") || "declarado al SEA"}${extra ? `<span class="range">${extra}</span>` : ""}`;
  }

  function renderTable() {
    const all = projectsOf(CAL.ci).map(({ p }) => p);
    const known = all.filter((p) => !p.anonymous);
    const anon = all.filter((p) => p.anonymous);
    const rows = known.map((p) => `<tr>
      <td><b>${esc(p.name)}</b>${p.operator && !p.operator.startsWith("(") && !p.name.includes(p.operator) ? `<span class="range">${esc(p.operator)}</span>` : ""}</td>
      <td data-label="Hoy">${esc(statusText(p))}</td>
      <td data-label="Servidores">${mwTxt(p.it_mw)} MW${p.request_mw ? `<span class="range">pidió ${fmt(p.request_mw)} MW al CEN</span>` : ""}</td>
      <td data-label="Enfriamiento">${coolCell(p)}</td>
      <td data-label="Declarado al SEA">${seaCell(p)}</td></tr>`).join("");
    const mw = anon.reduce((a, p) => a + p.it_mw, 0);
    const anonRow = anon.length ? `<tr class="calc-anon"><td colspan="5">${anon.length === 1
      ? "1 proyecto sin nombre público (un supuesto que cuadra el inventario)"
      : `${fmt(anon.length)} proyectos sin nombre público (supuestos que cuadran el inventario)`}: ${mwTxt(mw)} MW</td></tr>` : "";
    $("#calcProjects").innerHTML = `<table class="data calc-table"><thead><tr><th scope="col">Proyecto</th><th scope="col">Hoy</th><th scope="col">MW de servidores</th><th scope="col">Enfriamiento</th><th scope="col">Declarado al SEA</th></tr></thead><tbody>${rows}${anonRow}</tbody></table>`;
  }

  // ---------------------------------------------------------------- calcular
  function updateNote() {
    if (CAL.busy) return;
    const ch = changes();
    const key = keyOf(ch);
    const stale = Boolean(CAL.res) && key !== CAL.shown;
    $("#calcResults").classList.toggle("stale", stale);
    const n = fmt(CAL.meta.calc.n);
    let t;
    if (!CAL.base) t = "Cargando lo declarado…";
    else if (stale && Object.keys(ch).length) t = `Cambiaste el enfriamiento. Presiona Calcular: se simulan ${n} futuros y puede tardar hasta un minuto.`;
    else if (stale) t = "Volviste a lo declarado. Presiona Calcular para verlo.";
    else if (key !== "{}") t = `Listo: con tus cambios, comparado con lo declarado en los mismos ${n} futuros.`;
    else t = "Elige agua o aire para los que aún no operan y presiona Calcular.";
    $("#calcNote").textContent = t;
  }

  async function run() {
    if (CAL.busy || !CAL.base) return;
    const ch = changes();
    const key = keyOf(ch);
    const max = CAL.meta.calc.max_changes;
    if (Object.keys(ch).length > max) { $("#calcNote").textContent = `Como máximo ${fmt(max)} cambios a la vez.`; return; }
    if (key === "{}") { show(CAL.base, key); return; }
    if (CAL.cache.has(key)) { show(CAL.cache.get(key), key); return; }
    CAL.busy = true;
    const ctrls = [$("#calcRun"), $("#calcCommune"), ...document.querySelectorAll("#calcProjects [data-cool]")];
    ctrls.forEach((el) => { el.disabled = true; });
    const n = fmt(CAL.meta.calc.n);
    const t0 = Date.now();
    const tick = () => {
      const sec = Math.round((Date.now() - t0) / 1000);
      $("#calcNote").textContent = `Simulando ${n} futuros… ${sec} s${sec >= 45 ? " (si otra persona está simulando, se espera su turno)" : ""}`;
    };
    tick();
    const timer = setInterval(tick, 1000);
    try {
      const res = await post(ch);
      CAL.cache.set(key, res);
      while (CAL.cache.size > CACHE_MAX) CAL.cache.delete(CAL.cache.keys().next().value);
      CAL.busy = false;
      show(res, key);
    } catch (err) {
      CAL.busy = false;
      $("#calcNote").textContent = `No se pudo calcular: ${err.message}.`;
    } finally {
      clearInterval(timer);
      CAL.busy = false;
      ctrls.forEach((el) => { el.disabled = false; });
    }
  }

  function show(res, key) {
    CAL.res = res;
    CAL.shown = key;
    renderResults();
    updateNote();
  }

  // ---------------------------------------------------------------- resultados
  // en cuántos de los mismos futuros sube o baja una cifra de la comuna (2030 o 2035), futuro a futuro
  function counts(k) {
    const r = CAL.res;
    const b = CAL.base;
    const col = CAL.year === 2030 ? 0 : CAL.year === 2035 ? 1 : -1;
    if (r.paired_communes && b.paired_communes && col >= 0 && r.paired_communes[k] && b.paired_communes[k]) {
      const a = r.paired_communes[k];
      const z = b.paired_communes[k];
      if (a.length === z.length) {
        let more = 0;
        let less = 0;
        a.forEach((row, s) => {
          const x = row[CAL.ci][col];
          const y = z[s][CAL.ci][col];
          if (x > y) more += 1; else if (x < y) less += 1;
        });
        return { more, less, n: a.length };
      }
    }
    const c = CAL.year === 2035 && r.compare && r.compare[k] && r.compare[k][CAL.ci];  // lo que calcula el servidor
    if (!c) return null;
    const goodUp = k === "c_demand" ? null : false;
    const [more, less] = goodUp === null ? [c.more, c.less] : [c.worse, c.better];
    return { more, less, n: r.meta.n };
  }

  // en cuántos futuros la cifra se mueve hacia ese lado, y qué pasa en el resto
  function inFutures(c, up, goodUp) {
    const [agree, against] = up ? [c.more, c.less] : [c.less, c.more];
    if (agree === c.n) return `en los ${fmt(c.n)} futuros`;
    const other = goodUp === null ? (up ? "menos" : "más") : (up === goodUp ? "peor" : "mejor");
    return `en ${fmt(agree)} de ${fmt(c.n)} futuros; ${against ? `${other} en ${fmt(against)}` : "igual en el resto"}`;
  }

  // comparación con lo declarado: valor típico y, si hay pares, en cuántos futuros
  function versus(spec, v, b, c) {
    const d = v - b;
    const diff = Math.abs(d) * spec.scale;
    if (diff < spec.eps) {
      if (!c || c.more + c.less === 0) return `igual que como lo declararon${c ? ` en los ${fmt(c.n)} futuros` : ""} (${spec.show(b)})`;
      const [up, down] = spec.goodUp === null ? ["más", "menos"] : spec.goodUp ? ["mejor", "peor"] : ["peor", "mejor"];
      return `casi igual que como lo declararon (${spec.show(b)}) · ${up} en ${fmt(c.more)} de ${fmt(c.n)} futuros, ${down} en ${fmt(c.less)}`;
    }
    const up = d > 0;
    const verdict = spec.goodUp === null ? "" : `<b>${up === spec.goodUp ? "mejor" : "peor"}</b> · `;
    return `${verdict}${spec.amount(diff)} ${up ? "más" : "menos"} que como lo declararon (${spec.show(b)})${c ? ` · ${inFutures(c, up, spec.goodUp)}` : " · valor típico"}`;
  }

  function setBand(k, value, note, delta) {
    const band = document.querySelector(`#calcBands [data-ck="${k}"]`);
    band.querySelector(".val").textContent = value;
    band.querySelector(".note").textContent = note;
    band.querySelector(".delta").innerHTML = delta || "";
  }

  function renderResults() {
    const meta = CAL.meta;
    const r = CAL.res;
    if (!meta || CAL.ci < 0) return;
    const c = meta.communes[CAL.ci];
    const all = projectsOf(CAL.ci).map(({ p }) => p);
    const known = all.filter((p) => !p.anonymous);
    const mwAll = all.reduce((a, p) => a + p.it_mw, 0);
    const ch = r ? r.changes || {} : {};
    const changed = Boolean(r) && r !== CAL.base && Object.keys(ch).length > 0;
    const nAnon = all.length - known.length;
    const sum = `${all.length === 1 ? "Suma su único proyecto" : `Suma sus ${fmt(all.length)} proyectos`}${nAnon ? ` (${fmt(nAnon)} sin nombre público)` : ""}, ${mwTxt(mwAll)} MW de servidores, y los nuevos que llegan en cada futuro.`;
    if (!r) { $("#calcSummary").innerHTML = `<b>${esc(c.name)}</b>. ${sum} Cargando las cifras…`; return; }
    const how = changed
      ? `con ${Object.keys(ch).length === 1 ? "un cambio" : `${fmt(Object.keys(ch).length)} cambios`} desde 2027: ${Object.entries(ch).map(([pid, cool]) => `${esc(meta.projects.find((p) => p.id === pid).name)} ${COOL[cool]}`).join(", ")}`
      : "con el enfriamiento que declaró cada proyecto";
    $("#calcSummary").innerHTML = `<b>${esc(c.name)}</b>, ${how}. ${sum}`;

    const yi = meta.years.indexOf(CAL.year);
    const i = CAL.ci;
    const q = (src, k, idx = i) => ({ p5: src[k].p5[idx][yi], p50: src[k].p50[idx][yi], p95: src[k].p95[idx][yi] });
    const b = CAL.base;
    const range = (v, f, unit) => `en 9 de cada 10 futuros, entre ${f(v.p5)} y ${f(v.p95)}${unit}`;
    const cmp = (spec, v, k, src = "communes", idx = i) => (changed
      ? versus(spec, v.p50, q(b[src], k, idx).p50, k && src === "communes" ? counts(k) : null) : "");

    // agua: L/s del promedio del año; 500 L por hogar al día
    const w = q(r.communes, "c_water_ls");
    const homes = w.p50 * 86400 / 500;
    const homesWater = c.households * 500 / 86400;
    const wSpec = { show: (x) => `${lsTxt(x)} L/s`, amount: (x) => `${lsTxt(x)} L/s`, scale: 1, eps: 0.05, goodUp: false };
    setBand("water", `${lsTxt(w.p50)} L/s`,
      `promedio del año${w.p50 >= 0.05 ? `; el agua de ${fmt(homes)} hogares, ${pct(w.p50 / homesWater)} de lo que usan los ${fmt(c.households)} hogares de la comuna` : ""} · ${range(w, lsTxt, " L/s")}`,
      cmp(wSpec, w, "c_water_ls"));

    // electricidad: MW promedio del año y parte de la electricidad de la comuna
    const e = q(r.communes, "c_demand");
    const sh = q(r.communes, "c_share");
    const eSpec = { show: (x) => `${fmt(x)} MW`, amount: (x) => `${fmt(x)} MW`, scale: 1, eps: 0.5, goodUp: null };
    setBand("power", `${fmt(e.p50)} MW`,
      `promedio del año: ${pct(sh.p50)} de la electricidad que se usa en la comuna · ${range(e, fmt, " MW")}`,
      cmp(eSpec, e, "c_demand"));

    // red: MW sin reservar en el nodo de la comuna, que comparten varias comunas
    const ni = meta.nodes.findIndex((n) => n.id === c.node);
    const node = meta.nodes[ni];
    const f0 = (x) => fmt(Math.max(0, x));
    if (ni >= 0 && r.nodes && r.nodes.n_free) {
      const g = q(r.nodes, "n_free", ni);
      const full = g.p50 <= 0;
      const gSpec = { show: (x) => `${f0(x)} MW`, amount: (x) => `${fmt(x)} MW`, scale: 1, eps: 0.5, goodUp: true };
      setBand("grid", `${f0(g.p50)} MW`,
        `${full ? "la red del nodo está llena · " : ""}sin reservar a fin de ${CAL.year} en el nodo ${node.name}; un proyecto que pide más espera en la fila · ${range(g, f0, " MW")}`,
        changed ? versus(gSpec, g.p50, q(b.nodes, "n_free", ni).p50, null) : "");
    } else {
      setBand("grid", "—", "sin dato de la red para esta comuna", "");
    }

    // fila del CEN: MW pedidos por proyectos de la comuna que esperan conexión
    const wl = q(r.communes, "c_waitlist");
    const wlSpec = { show: (x) => `${fmt(x)} MW`, amount: (x) => `${fmt(x)} MW`, scale: 1, eps: 0.5, goodUp: false };
    setBand("wait", `${fmt(wl.p50)} MW`,
      `pedidos de conexión de proyectos de la comuna que esperan en la fila del CEN · ${range(wl, fmt, " MW")}`,
      cmp(wlSpec, wl, "c_waitlist"));

    // vecinos: parte de los hogares de la comuna dispuestos a oponerse
    const m = q(r.communes, "c_conflict");
    const p100 = (x) => fmt(100 * x);
    const mSpec = { show: (x) => `${p100(x)}%`, amount: (x) => `${fmt(x, x < 10 ? 1 : 0)} puntos`, scale: 100, eps: 0.1, goodUp: false };
    setBand("conflict", `${p100(m.p50)}%`,
      `de los ${fmt(c.households)} hogares de la comuna · ${range(m, p100, "%")}`,
      cmp(mSpec, m, "c_conflict"));

    renderChanges(changed ? ch : null);
  }

  // lo que cambia cada proyecto: su propia agua y electricidad (valor típico) y si llega a operar
  function renderChanges(ch) {
    const el = $("#calcChanges");
    if (!ch) { el.hidden = true; el.innerHTML = ""; return; }
    const meta = CAL.meta;
    const r = CAL.res;
    const b = CAL.base;
    const yi = meta.years.indexOf(CAL.year);
    const q = (src, k, pi) => ({ p5: src.projects[k].p5[pi][yi], p50: src.projects[k].p50[pi][yi], p95: src.projects[k].p95[pi][yi], mean: src.projects[k].mean[pi][yi] });
    const dWater = (d) => (Math.abs(d) < 0.05 ? "casi la misma agua" : `${sign(d, lsTxt)} L/s de agua`);
    const dPower = (d) => (Math.abs(d) < 0.5 ? "casi la misma electricidad" : `${sign(d, fmt)} MW de electricidad`);
    const items = Object.entries(ch).map(([pid, cool]) => {
      const pi = meta.projects.findIndex((p) => p.id === pid);
      const p = meta.projects[pi];
      const w = q(r, "water_ls", pi);
      const w0 = q(b, "water_ls", pi);
      const e = q(r, "mw", pi);
      const e0 = q(b, "mw", pi);
      // valor típico y promedio: si un proyecto termina con agua en unos futuros y con aire en otros,
      // la mediana cae en uno de los dos y el promedio muestra el cambio que la mediana esconde
      const typical = `${dWater(w.p50 - w0.p50)} y ${dPower(e.p50 - e0.p50)}`;
      const short = (d, f, unit) => `${sign(d, f)} ${unit}`;
      const average = `${short(w.mean - w0.mean, lsTxt, "L/s")} y ${short(e.mean - e0.mean, fmt, "MW")}`;
      const op = r.projects.status_prob[pi][yi][OPER];
      const op0 = b.projects.status_prob[pi][yi][OPER];
      const spread = cool === "evaporativo"
        ? ` Con agua usa entre ${lsTxt(w.p5)} y ${lsTxt(w.p95)} L/s en 9 de cada 10 futuros.`
        : ` Con aire usa entre ${fmt(e.p5)} y ${fmt(e.p95)} MW en 9 de cada 10 futuros.`;
      return `<li><b>${esc(p.name)} ${COOL[cool]}</b>: ${typical} en ${CAL.year} (valor típico; en promedio, ${average}).${spread} Opera en ${pct(op)} de los futuros, ${Math.abs(op - op0) < 0.005 ? "igual que" : `contra ${pct(op0)}`} ${COOL[p.cooling_now]}.</li>`;
    });
    el.innerHTML = `<p>Cada cambio, comparado con lo declarado</p><ul>${items.join("")}</ul>`;
    el.hidden = false;
  }

  window.initCalc = initCalc;
})();
