/* Aterriza: la pregunta de la portada. Si se construye todo lo aprobado en Quilicura, ¿alcanza el
   agua? Los proyectos que aún no operan enfrían con aire (lo que declararon) o con agua desde 2027.
   Los dos escenarios vienen precalculados (python -m dcsim.precompute) con los mismos futuros, así
   que responden al instante y se comparan futuro a futuro. Usa $, fmt y esc de story.js. */
(() => {
  const CAL = { meta: null, base: null, water: null, cool: "aire", ci: -1, ids: [] };
  const OPER = 5;  // código de "operando" en status_prob
  const REAL = { operando: "operando", construccion: "en construcción", tramitacion: "en trámite", lista_espera: "esperando red" };
  const COOL = { evaporativo: "con agua", aire: "con aire", hibrido: "híbrido" };
  const lsTxt = (x) => (Math.abs(x) < 0.05 ? "0" : fmt(x, Math.abs(x) < 10 ? 1 : 0));
  const mwTxt = (x) => fmt(x, Math.abs(x) < 30 && Math.round(x * 10) % 10 ? 1 : 0);
  const pct = (x) => `${fmt(100 * x)}%`;
  const setText = (sel, txt) => document.querySelectorAll(sel).forEach((el) => { el.textContent = txt; });
  const get = (url, body) => fetch(url, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined).then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); });

  function initCalc(meta) {
    CAL.meta = meta;
    CAL.ci = meta.communes.findIndex((c) => c.id === meta.calc.demo_commune);
    CAL.ids = meta.calc.demo_projects;
    const all = meta.projects.filter((p) => p.commune === meta.calc.demo_commune);
    setText("[data-calc-n]", fmt(meta.calc.n));
    setText("[data-calc-k]", fmt(CAL.ids.length));
    setText("[data-calc-total]", fmt(all.length));
    renderTable(all);
    document.querySelectorAll("#calculadora [data-cool]").forEach((b) => b.addEventListener("click", () => {
      CAL.cool = b.dataset.cool;
      document.querySelectorAll("#calculadora [data-cool]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      render();
    }));
    get("/api/baseline").then((d) => { CAL.base = d; render(); })
      .catch(() => { $("#calcNote").textContent = "No se pudo cargar la simulación. Recarga la página para reintentar."; });
    const cooling = Object.fromEntries(CAL.ids.map((id) => [id, "evaporativo"]));
    get("/api/calc", { cooling }).then((d) => { CAL.water = d; render(); }).catch(() => { CAL.water = false; render(); });
  }

  // en cuántos de los mismos futuros la cifra de 2035 sube o baja con agua
  function moved(k) {
    const a = CAL.water.paired_communes[k].map((row) => row[CAL.ci][1]);
    const b = CAL.base.paired_communes[k].map((row) => row[CAL.ci][1]);
    return { up: a.filter((x, s) => x > b[s]).length, down: a.filter((x, s) => x < b[s]).length, n: a.length };
  }

  function band(k, val, note, delta) {
    const el = document.querySelector(`#calcBands [data-ck="${k}"]`);
    el.querySelector(".val").textContent = val;
    el.querySelector(".note").textContent = note;
    el.querySelector(".delta").innerHTML = delta || "";
  }

  function render() {
    const water = CAL.cool === "evaporativo";
    const res = water ? CAL.water : CAL.base;
    const note = $("#calcNote");
    if (!res) {
      note.textContent = water && CAL.water === false ? "No se pudo simular con agua. Recarga la página." : "Cargando la simulación…";
      return;
    }
    const meta = CAL.meta;
    const i = CAL.ci;
    const yi = meta.years.indexOf(2035);
    const c = meta.communes[i];
    const at = (src, k) => src.communes[k].p50[i][yi];
    const homesWater = c.households * 500 / 86400;  // L/s que usan los hogares de la comuna (500 L al día)
    const vs = water && CAL.base;
    note.textContent = water
      ? `Con agua desde 2027, comparado con lo declarado en los mismos ${fmt(res.meta.n)} futuros.`
      : "Aire es lo que declararon al SEA. Prueba con agua.";

    const w = at(res, "c_water_ls");
    const mW = vs && moved("c_water_ls");
    band("water", `${lsTxt(w)} L/s`,
      `el agua de ${fmt(w * 86400 / 500)} hogares, ${pct(w / homesWater)} de lo que usan sus ${fmt(c.households)} hogares`,
      vs ? `con aire, ${lsTxt(at(CAL.base, "c_water_ls"))} L/s · <b>más agua en ${fmt(mW.up)} de ${fmt(mW.n)} futuros</b>` : "");

    const e = at(res, "c_demand");
    const mE = vs && moved("c_demand");
    band("power", `${fmt(e)} MW`, `${pct(at(res, "c_share"))} de la electricidad que se usa en la comuna`,
      vs ? `con aire, ${fmt(at(CAL.base, "c_demand"))} MW · menos en ${fmt(mE.down)} de ${fmt(mE.n)} futuros` : "");

    const v = at(res, "c_conflict");
    const mV = vs && moved("c_conflict");
    band("conflict", pct(v), `de sus ${fmt(c.households)} hogares`,
      vs ? `con aire, ${pct(at(CAL.base, "c_conflict"))} · <b>más en ${fmt(mV.up)} de ${fmt(mV.n)} futuros</b>` : "");

    // lo que una suma no ve: cuántos de esos proyectos llegan a operar en 2035
    const op = (src) => CAL.ids.reduce((a, id) => a + src.projects.status_prob[meta.projects.findIndex((p) => p.id === id)][yi][OPER], 0) / CAL.ids.length;
    const k = fmt(CAL.ids.length);
    const oper = op(res);
    $("#calcSim").innerHTML = water
      ? `Con agua, <b>1 de cada ${fmt(Math.max(1, Math.round(1 / Math.max(1 - oper, 1e-9))))} de esos ${k} proyectos no llega a operar en 2035</b>: juicios, anulaciones y espera de red. Operan en ${pct(oper)} de los futuros${CAL.base ? `, contra ${pct(op(CAL.base))} con aire` : ""}.`
      : `Con aire, esos ${k} proyectos operan en 2035 en ${pct(oper)} de los futuros.`;
  }

  // ---------------------------------------------------------------- detalle: los proyectos y el SEA
  const statusText = (p) => (p.real_status ? REAL[p.real_status] || p.real_status : (p.pre_existing ? "operando" : "anunciado"));

  function seaCell(p) {
    const s = p.sea;
    if (!s) return `<span class="range">sin dato declarado</span>${p.src ? `<span class="range">${esc(p.src)}</span>` : ""}`;
    const parts = [];
    if (s.water_max_ls != null) parts.push(`hasta ${lsTxt(s.water_max_ls)} L/s`);
    if (s.water_avg_ls != null) parts.push(`${lsTxt(s.water_avg_ls)} L/s en promedio`);
    if (s.water_rights_ls != null) parts.push(`derechos por ${lsTxt(s.water_rights_ls)} L/s`);
    if (s.it_mw != null) parts.push(`${mwTxt(s.it_mw)} MW de servidores`);
    if (s.facility_mw != null) parts.push(`${mwTxt(s.facility_mw)} MW en total`);
    if (s.cooling) parts.push(esc(s.cooling));
    if (s.instrument) parts.push(esc(s.instrument));
    if (s.rca) parts.push(`RCA ${esc(s.rca)}`);
    else if (s.expediente) parts.push(`expediente ${esc(s.expediente)}`);
    if (typeof s.url === "string" && /^https?:\/\//.test(s.url)) parts.push(`<a href="${esc(s.url)}" target="_blank" rel="noopener">fuente</a>`);
    const extra = [s.confidence ? `confianza ${esc(s.confidence)}` : "", s.note ? esc(s.note) : ""].filter(Boolean).join(". ");
    return `${parts.join(" · ")}${extra ? `<span class="range">${extra}</span>` : ""}`;
  }

  function renderTable(all) {
    const known = all.filter((p) => !p.anonymous);
    const anon = all.filter((p) => p.anonymous);
    const rows = known.map((p) => `<tr>
      <td><b>${esc(p.name)}</b>${CAL.ids.includes(p.id) ? '<span class="range">aún no opera: cambia con el interruptor</span>' : ""}</td>
      <td data-label="Hoy">${esc(statusText(p))}</td>
      <td data-label="Servidores">${mwTxt(p.it_mw)} MW</td>
      <td data-label="Enfriamiento declarado">${esc(COOL[p.cooling_now] || p.cooling_now)}</td>
      <td data-label="Declarado al SEA">${seaCell(p)}</td></tr>`).join("");
    const mw = anon.reduce((a, p) => a + p.it_mw, 0);
    const anonRow = anon.length ? `<tr class="calc-anon"><td colspan="5">${fmt(anon.length)} ${anon.length === 1 ? "proyecto" : "proyectos"} sin nombre público (supuestos que cuadran el inventario): ${mwTxt(mw)} MW</td></tr>` : "";
    $("#calcProjects").innerHTML = `<table class="data calc-table"><thead><tr><th scope="col">Proyecto</th><th scope="col">Hoy</th><th scope="col">MW de servidores</th><th scope="col">Enfriamiento declarado</th><th scope="col">Declarado al SEA</th></tr></thead><tbody>${rows}${anonRow}</tbody></table>`;
  }

  window.initCalc = initCalc;
})();
