"use strict";

const state = { tools: [], activeSlot: null, iconTarget: null };
const grid = document.querySelector("#tool-grid");
const dialog = document.querySelector("#tool-dialog");
const toolForm = document.querySelector("#tool-form");
const cuttingForm = document.querySelector("#cutting-form");
const cuttingList = document.querySelector("#cutting-list");
const historyList = document.querySelector("#history-list");
const materialsDialog = document.querySelector("#materials-dialog");
const materialsDialogList = document.querySelector("#materials-dialog-list");
const iconDialog = document.querySelector("#icon-dialog");
const iconGrid = document.querySelector("#icon-grid");
const labelsDialog = document.querySelector("#labels-dialog");
const labelSheet = document.querySelector("#label-sheet");
const fields = ["t_number","d_offset","h_offset","diameter_mm","length_mm","description","tool_type","icon","flutes","status","usage_hours","life_hours","notes"];
const cuttingFields = ["id","material","coolant","vc_m_min","rpm","fz_mm_tooth","feed_mm_min","ap_mm","ae_mm","notes"];
const TOOL_ICONS = [
  {id:"end_mill", label:"Fresa cilindrica"},
  {id:"roughing_mill", label:"Fresa a sgrossare"},
  {id:"ball_nose", label:"Fresa sferica"},
  {id:"face_mill", label:"Fresa a spianare"},
  {id:"slitting_saw", label:"Fresa a disco"},
  {id:"t_slot", label:"Fresa a T"},
  {id:"dovetail", label:"Fresa a coda di rondine"},
  {id:"chamfer", label:"Fresa per smussi"},
  {id:"drill", label:"Punta da trapano"},
  {id:"center_drill", label:"Punta a centrare"},
  {id:"tap", label:"Maschio"},
  {id:"reamer", label:"Alesatore"},
  {id:"boring_bar", label:"Bareno"},
  {id:"engraving", label:"Utensile da incisione"},
  {id:"probe", label:"Tastatore"},
  {id:"custom", label:"Utensile personalizzato"}
];
const STATUS_LABELS = {new:"Nuovo", in_use:"In uso", to_sharpen:"Da affilare", maintenance:"In manutenzione", worn:"Fuori servizio"};

function esc(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);
}

function iconDefinition(icon) {
  return TOOL_ICONS.find(item => item.id === icon);
}

function toolIcon(icon, className = "tool-icon") {
  const definition = iconDefinition(icon);
  return definition ? `<img class="${className}" src="static/tool-icons/${definition.id}.png" alt="" aria-hidden="true">` : "";
}

function iconLabel(icon) {
  return iconDefinition(icon)?.label || "Nessuna icona";
}

async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: {"Content-Type":"application/json", ...(options.headers || {})} });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Errore HTTP ${response.status}`);
  return data;
}

function isOccupied(tool) {
  return Boolean(tool.description || tool.tool_type || tool.icon || tool.diameter_mm || tool.length_mm || tool.flutes || tool.notes || tool.cutting_parameters?.length);
}

function render() {
  const query = document.querySelector("#search").value.trim().toLowerCase();
  const filter = document.querySelector("#filter").value;
  const visible = state.tools.filter(tool => {
    const occupied = isOccupied(tool);
    if (filter === "occupied" && !occupied) return false;
    if (filter === "free" && occupied) return false;
    const haystack = [tool.slot, tool.t_number, tool.description, tool.tool_type, tool.notes, ...tool.cutting_parameters.map(x => x.material)].join(" ").toLowerCase();
    return !query || haystack.includes(query);
  });
  grid.innerHTML = visible.map(toolCard).join("");
  document.querySelector("#empty-state").hidden = visible.length > 0;
  grid.querySelectorAll(".tool-card").forEach(card => {
    card.addEventListener("click", () => openTool(Number(card.dataset.slot)));
    card.addEventListener("keydown", event => {
      if ((event.key === "Enter" || event.key === " ") && event.target === card) {
        event.preventDefault();
        openTool(Number(card.dataset.slot));
      }
    });
  });
  grid.querySelectorAll(".show-material").forEach(button => button.addEventListener("click", event => {
    event.stopPropagation();
    openMaterial(Number(button.closest(".tool-card").dataset.slot), Number(button.dataset.id));
  }));

  const occupied = state.tools.filter(isOccupied).length;
  document.querySelector("#occupied-count").textContent = occupied;
  document.querySelector("#free-count").textContent = 30 - occupied;
  document.querySelector("#material-count").textContent = state.tools.reduce((sum, tool) => sum + tool.cutting_parameters.length, 0);
}

function toolCard(tool) {
  const occupied = isOccupied(tool);
  const title = tool.description || "Posizione libera";
  const materials = tool.cutting_parameters.map(item => `<button class="chip material-chip show-material" data-id="${item.id}" type="button" aria-label="Apri parametri per ${esc(item.material)}">${esc(item.material)}</button>`).join("");
  const status = occupied ? (STATUS_LABELS[tool.status] || "In uso") : "Libero";
  const life = occupied && tool.remaining_percent !== null ? `<span class="life-meter"><i style="width:${tool.remaining_percent}%"></i></span><small>${tool.remaining_percent}% vita residua · ${formatHours(tool.usage_hours_current)}</small>` : "";
  return `<article class="tool-card ${occupied ? "" : "free"}" data-slot="${tool.slot}" role="button" tabindex="0">
    <div class="card-head"><span class="slot">${tool.slot}</span><span class="status status-${esc(tool.status)}">${esc(status)}</span></div>
    <div class="tool-title">${toolIcon(tool.icon, "card-tool-icon")}<h3>${esc(title)}</h3></div>
    <div class="offsets"><span>T<b>${esc(tool.t_number ?? "—")}</b></span><span>D<b>${esc(tool.d_offset ?? "—")}</b></span><span>H<b>${esc(tool.h_offset ?? "—")}</b></span></div>
    <p class="measure">Ø ${esc(tool.diameter_mm ?? "—")} mm · L ${esc(tool.length_mm ?? "—")} mm${tool.flutes ? ` · Z${esc(tool.flutes)}` : ""}</p>
    <div class="card-life">${life}</div>
    <div class="material-chips">${materials}${tool.history.length ? `<span class="chip">${tool.history.length} storico</span>` : ""}</div>
  </article>`;
}

function formatHours(value) {
  const hours = Number(value || 0);
  return `${hours.toLocaleString("it-IT", {minimumFractionDigits:1, maximumFractionDigits:2})} ore`;
}

function parameterValue(value, unit = "") {
  return value === null || value === undefined || value === "" ? "—" : `${esc(value)}${unit}`;
}

function openMaterial(slot, materialId) {
  const tool = state.tools.find(item => item.slot === slot);
  const item = tool?.cutting_parameters.find(value => value.id === materialId);
  if (!tool || !item) return;
  document.querySelector("#materials-dialog-title").textContent = item.material;
  document.querySelector("#materials-dialog-tool").textContent = `Posto ${slot} · ${tool.description || tool.tool_type || "Utensile montato"}`;
  document.querySelector("#materials-dialog-icon").innerHTML = toolIcon(tool.icon, "popup-tool-icon");
  materialsDialogList.innerHTML = `
    <article class="material-detail">
      <div class="material-detail-head">
        <h3>Parametri di taglio</h3>
        <span class="chip">${esc(item.coolant || "Refrigerazione non indicata")}</span>
      </div>
      <div class="parameter-grid">
        <div><small>Velocità Vc</small><strong>${parameterValue(item.vc_m_min, " m/min")}</strong></div>
        <div><small>Giri S</small><strong>${parameterValue(item.rpm, " rpm")}</strong></div>
        <div><small>Avanzamento Fz</small><strong>${parameterValue(item.fz_mm_tooth, " mm/dente")}</strong></div>
        <div><small>Avanzamento F</small><strong>${parameterValue(item.feed_mm_min, " mm/min")}</strong></div>
        <div><small>Profondità ap</small><strong>${parameterValue(item.ap_mm, " mm")}</strong></div>
        <div><small>Larghezza ae</small><strong>${parameterValue(item.ae_mm, " mm")}</strong></div>
      </div>
      ${item.notes ? `<p class="material-notes"><strong>Note:</strong> ${esc(item.notes)}</p>` : ""}
    </article>`;
  materialsDialog.showModal();
}

async function loadTools(showMessage = false) {
  try {
    const data = await request("api/tools");
    state.tools = data.tools;
    document.querySelector("#machine-name").textContent = data.machine.machine_name;
    render();
    if (!state.deepLinkOpened) {
      state.deepLinkOpened = true;
      const url = new URL(window.location.href);
      const slot = Number(url.searchParams.get("slot"));
      const historyId = Number(url.searchParams.get("history")) || null;
      if (Number.isInteger(slot) && slot >= 1 && slot <= 30) openTool(slot, historyId);
    }
    if (showMessage) toast("Dati aggiornati");
  } catch (error) { toast(error.message, true); }
}

function openTool(slot, historyId = null) {
  state.activeSlot = slot;
  const tool = state.tools.find(item => item.slot === slot);
  document.querySelector("#slot").value = slot;
  document.querySelector("#dialog-title").textContent = `Posto ${slot}`;
  fields.forEach(field => { toolForm.elements[field].value = tool[field] ?? ""; });
  renderSelectedIcon(tool.icon);
  clearCutting();
  renderCutting(tool);
  renderHistory(tool);
  renderUsage(tool);
  dialog.showModal();
  if (historyId) {
    const archived = historyList.querySelector(`[data-id="${historyId}"]`);
    if (archived) {
      archived.classList.add("highlighted");
      setTimeout(() => archived.scrollIntoView({behavior:"smooth", block:"center"}), 100);
    }
  }
}

function currentUsage(tool) {
  let usage = Number(tool.usage_hours || 0);
  if (tool.timer_started_at) {
    usage += Math.max(0, (Date.now() - new Date(tool.timer_started_at).getTime()) / 3600000);
  }
  return usage;
}

function renderUsage(tool) {
  const usage = currentUsage(tool);
  const life = Number(tool.life_hours || 0);
  document.querySelector("#usage-summary").textContent = `${formatHours(usage)}${tool.timer_started_at ? " · conteggio attivo" : ""}`;
  document.querySelector("#life-summary").textContent = life > 0
    ? `${Math.max(0, Math.round((1 - usage / life) * 100))}% di vita residua su ${formatHours(life)}`
    : "Vita prevista non impostata";
  document.querySelector("#start-usage").disabled = Boolean(tool.timer_started_at);
  document.querySelector("#stop-usage").disabled = !tool.timer_started_at;
}

function renderHistory(tool) {
  historyList.innerHTML = tool.history.length ? tool.history.map(item => `
    <article class="history-row" data-id="${item.history_id}">
      <div class="history-identity">${toolIcon(item.icon, "history-tool-icon")}<div><strong>${esc(item.description || item.tool_type || "Utensile senza descrizione")}</strong><small>Archiviato ${esc(new Date(item.archived_at).toLocaleString("it-IT"))} · ${esc(STATUS_LABELS[item.status] || "In uso")} · ${formatHours(item.usage_hours)}</small></div></div>
      <div><small>T</small>${esc(item.t_number ?? "—")}</div>
      <div><small>D</small>${esc(item.d_offset ?? "—")}</div>
      <div><small>H</small>${esc(item.h_offset ?? "—")}</div>
      <div class="row-actions"><button class="mini-button history-icon" type="button">Icona</button><button class="mini-button activate" type="button">Monta</button><button class="mini-button delete-history delete" type="button">Elimina</button></div>
    </article>`).join("") : `<p class="subtitle">Nessun utensile nello storico di questa posizione.</p>`;
  historyList.querySelectorAll(".activate").forEach(button => button.addEventListener("click", () => activateHistory(Number(button.closest("article").dataset.id))));
  historyList.querySelectorAll(".history-icon").forEach(button => button.addEventListener("click", () => openIconPicker("history", Number(button.closest("article").dataset.id))));
  historyList.querySelectorAll(".delete-history").forEach(button => button.addEventListener("click", () => removeHistory(Number(button.closest("article").dataset.id))));
}

function renderCutting(tool) {
  cuttingList.innerHTML = tool.cutting_parameters.length ? tool.cutting_parameters.map(item => `
    <article class="cutting-row" data-id="${item.id}">
      <div><strong>${esc(item.material)}</strong><small>${esc(item.coolant || "Senza refrigerazione indicata")}</small></div>
      <div><small>Vc</small>${esc(item.vc_m_min ?? "—")} m/min</div>
      <div><small>S</small>${esc(item.rpm ?? "—")} rpm</div>
      <div><small>Fz</small>${esc(item.fz_mm_tooth ?? "—")}</div>
      <div><small>F</small>${esc(item.feed_mm_min ?? "—")} mm/min</div>
      <div class="row-actions"><button class="mini-button edit" type="button">Modifica</button><button class="mini-button delete" type="button">Elimina</button></div>
    </article>`).join("") : `<p class="subtitle">Nessun parametro inserito per questo utensile.</p>`;
  cuttingList.querySelectorAll(".edit").forEach(button => button.addEventListener("click", () => editCutting(Number(button.closest("article").dataset.id))));
  cuttingList.querySelectorAll(".delete").forEach(button => button.addEventListener("click", () => removeCutting(Number(button.closest("article").dataset.id))));
}

function editCutting(id) {
  const item = state.tools.find(tool => tool.slot === state.activeSlot).cutting_parameters.find(value => value.id === id);
  cuttingFields.forEach(field => { cuttingForm.elements[field].value = item[field] ?? ""; });
  cuttingForm.elements.material.focus();
}

function clearCutting() {
  cuttingForm.reset();
  cuttingForm.elements.id.value = "";
}

function formData(form, names) {
  return Object.fromEntries(names.filter(name => name !== "id").map(name => [name, form.elements[name].value]));
}

function renderSelectedIcon(icon) {
  document.querySelector("#selected-tool-icon").innerHTML = toolIcon(icon, "selected-tool-icon") || '<span class="empty-tool-icon">＋</span>';
  document.querySelector("#selected-tool-icon-label").textContent = iconLabel(icon);
}

function openIconPicker(type, historyId = null) {
  state.iconTarget = {type, historyId};
  const currentIcon = type === "active"
    ? toolForm.elements.icon.value
    : state.tools.find(tool => tool.slot === state.activeSlot).history.find(item => item.history_id === historyId)?.icon || "";
  iconGrid.innerHTML = [
    `<button type="button" class="icon-choice ${currentIcon ? "" : "selected"}" data-icon=""><span class="empty-tool-icon">×</span><span>Nessuna</span></button>`,
    ...TOOL_ICONS.map(item => `<button type="button" class="icon-choice ${currentIcon === item.id ? "selected" : ""}" data-icon="${item.id}">${toolIcon(item.id, "picker-tool-icon")}<span>${esc(item.label)}</span></button>`)
  ].join("");
  iconGrid.querySelectorAll(".icon-choice").forEach(button => button.addEventListener("click", () => selectIcon(button.dataset.icon)));
  document.querySelector("#icon-dialog-title").textContent = type === "history" ? "Icona utensile archiviato" : "Scegli icona utensile";
  iconDialog.showModal();
}

async function selectIcon(icon) {
  if (state.iconTarget?.type === "active") {
    toolForm.elements.icon.value = icon;
    renderSelectedIcon(icon);
    iconDialog.close();
    return;
  }
  if (state.iconTarget?.type === "history") {
    try {
      await request(`api/tools/${state.activeSlot}/history/${state.iconTarget.historyId}/icon`, {method:"PUT", body:JSON.stringify({icon})});
      await loadTools();
      openRefresh();
      iconDialog.close();
      toast("Icona dello storico aggiornata");
    } catch (error) { toast(error.message, true); }
  }
}

toolForm.addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await request(`api/tools/${state.activeSlot}`, {method:"PUT", body:JSON.stringify(formData(toolForm, fields))});
    await loadTools();
    openRefresh();
    toast(`Utensile del posto ${state.activeSlot} salvato`);
  } catch (error) { toast(error.message, true); }
});

cuttingForm.addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await request(`api/tools/${state.activeSlot}/cutting`, {method:"PUT", body:JSON.stringify(formData(cuttingForm, cuttingFields))});
    await loadTools();
    clearCutting();
    openRefresh();
    toast("Parametri di taglio salvati");
  } catch (error) { toast(error.message, true); }
});

async function removeCutting(id) {
  if (!confirm("Eliminare questi parametri di taglio?")) return;
  try {
    await request(`api/tools/${state.activeSlot}/cutting/${id}`, {method:"DELETE"});
    await loadTools();
    openRefresh();
    toast("Parametri eliminati");
  } catch (error) { toast(error.message, true); }
}

function openRefresh() {
  const tool = state.tools.find(item => item.slot === state.activeSlot);
  fields.forEach(field => { toolForm.elements[field].value = tool[field] ?? ""; });
  renderSelectedIcon(tool.icon);
  renderCutting(tool);
  renderHistory(tool);
  renderUsage(tool);
}

document.querySelector("#start-usage").addEventListener("click", async () => {
  try {
    await request(`api/tools/${state.activeSlot}/usage/start`, {method:"POST"});
    await loadTools();
    openRefresh();
    toast("Conteggio utilizzo avviato");
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#stop-usage").addEventListener("click", async () => {
  try {
    await request(`api/tools/${state.activeSlot}/usage/stop`, {method:"POST"});
    await loadTools();
    openRefresh();
    toast("Conteggio fermato e ore salvate");
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#archive-tool").addEventListener("click", async () => {
  if (!confirm(`Archiviare l'utensile attivo del posto ${state.activeSlot} e liberare la posizione per uno nuovo?`)) return;
  try {
    await request(`api/tools/${state.activeSlot}/archive`, {method:"POST"});
    await loadTools();
    openRefresh();
    toast("Utensile archiviato: ora puoi inserire quello nuovo");
  } catch (error) { toast(error.message, true); }
});

async function activateHistory(id) {
  if (!confirm("Montare questo utensile? Quello attualmente attivo verrà spostato nello storico.")) return;
  try {
    await request(`api/tools/${state.activeSlot}/history/${id}/activate`, {method:"POST"});
    await loadTools();
    openRefresh();
    toast("Utensile storico montato");
  } catch (error) { toast(error.message, true); }
}

async function removeHistory(id) {
  if (!confirm("Eliminare definitivamente questo utensile dallo storico?")) return;
  try {
    await request(`api/tools/${state.activeSlot}/history/${id}`, {method:"DELETE"});
    await loadTools();
    openRefresh();
    toast("Utensile eliminato dallo storico");
  } catch (error) { toast(error.message, true); }
}

document.querySelector("#reset-tool").addEventListener("click", async () => {
  if (!confirm(`Svuotare completamente la posizione ${state.activeSlot}?`)) return;
  try {
    await request(`api/tools/${state.activeSlot}`, {method:"DELETE"});
    await loadTools();
    dialog.close();
    toast(`Posizione ${state.activeSlot} svuotata`);
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#duplicate-tool").addEventListener("click", async () => {
  const value = prompt(`In quale posizione vuoi duplicare l'utensile del posto ${state.activeSlot}? Inserisci un numero da 1 a 30.`);
  if (value === null) return;
  const target = Number(value);
  if (!Number.isInteger(target) || target < 1 || target > 30 || target === state.activeSlot) {
    toast("Scegli una posizione diversa, compresa tra 1 e 30", true);
    return;
  }
  const destination = state.tools.find(tool => tool.slot === target);
  const warning = isOccupied(destination)
    ? `La posizione ${target} è occupata: l'utensile attivo verrà conservato nel suo storico. Continuare?`
    : `Duplicare l'utensile nella posizione libera ${target}?`;
  if (!confirm(warning)) return;
  try {
    await request(`api/tools/${state.activeSlot}/duplicate`, {method:"POST", body:JSON.stringify({target_slot:target})});
    await loadTools();
    toast(`Utensile duplicato nella posizione ${target}`);
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#copy-cutting").addEventListener("click", async () => {
  const value = prompt(`Da quale posizione vuoi copiare i materiali nel posto ${state.activeSlot}? Inserisci un numero da 1 a 30.`);
  if (value === null) return;
  const source = Number(value);
  if (!Number.isInteger(source) || source < 1 || source > 30 || source === state.activeSlot) {
    toast("Scegli una posizione di origine diversa, compresa tra 1 e 30", true);
    return;
  }
  if (!confirm("I materiali con lo stesso nome verranno aggiornati; gli altri resteranno invariati. Continuare?")) return;
  try {
    const result = await request(`api/tools/${state.activeSlot}/cutting/copy`, {method:"POST", body:JSON.stringify({source_slot:source})});
    await loadTools();
    openRefresh();
    toast(`${result.copied} materiali copiati dalla posizione ${source}`);
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#calculate-cutting").addEventListener("click", () => {
  const diameter = Number(toolForm.elements.diameter_mm.value);
  const flutes = Number(toolForm.elements.flutes.value);
  let vc = Number(cuttingForm.elements.vc_m_min.value);
  let rpm = Number(cuttingForm.elements.rpm.value);
  let fz = Number(cuttingForm.elements.fz_mm_tooth.value);
  let feed = Number(cuttingForm.elements.feed_mm_min.value);
  let calculated = false;

  if (diameter > 0 && vc > 0) {
    rpm = Math.round((vc * 1000) / (Math.PI * diameter));
    cuttingForm.elements.rpm.value = rpm;
    calculated = true;
  } else if (diameter > 0 && rpm > 0 && !vc) {
    vc = (Math.PI * diameter * rpm) / 1000;
    cuttingForm.elements.vc_m_min.value = vc.toFixed(1);
    calculated = true;
  }
  if (rpm > 0 && flutes > 0 && fz > 0) {
    feed = rpm * flutes * fz;
    cuttingForm.elements.feed_mm_min.value = feed.toFixed(1);
    calculated = true;
  } else if (rpm > 0 && flutes > 0 && feed > 0 && !fz) {
    fz = feed / (rpm * flutes);
    cuttingForm.elements.fz_mm_tooth.value = fz.toFixed(3);
    calculated = true;
  }
  toast(calculated ? "Giri e avanzamento calcolati: controlla i valori prima di salvarli" : "Inserisci diametro e Vc, oppure giri, taglienti e Fz", !calculated);
});

const importFile = document.querySelector("#import-file");
document.querySelector("#import-button").addEventListener("click", () => {
  importFile.value = "";
  importFile.click();
});
importFile.addEventListener("change", async () => {
  const file = importFile.files[0];
  if (!file) return;
  try {
    if (file.size > 5_000_000) throw new Error("Il file supera il limite di 5 MB");
    const data = JSON.parse(await file.text());
    if (data.schema_version !== 1 || !Array.isArray(data.tools) || data.tools.length !== 30) {
      throw new Error("Questo non è un backup valido di CNC Tool Magazine");
    }
    const occupied = data.tools.filter(tool => isOccupied({...tool, cutting_parameters:tool.cutting_parameters || []})).length;
    const materials = data.tools.reduce((sum, tool) => sum + (tool.cutting_parameters?.length || 0), 0);
    const history = data.tools.reduce((sum, tool) => sum + (tool.history?.length || 0), 0);
    if (!confirm(`Ripristinare questo backup?\n\n${occupied} utensili montati\n${history} utensili nello storico\n${materials} materiali\n\nLo stato attuale verrà salvato automaticamente.`)) return;
    const result = await request("api/import", {method:"POST", body:JSON.stringify(data)});
    await loadTools();
    toast(`Ripristino completato. Backup precedente: ${result.backup}`);
  } catch (error) { toast(`Importazione non riuscita: ${error.message}`, true); }
});

function toolDeepLink(slot, historyId = null) {
  const url = new URL(window.location.href);
  url.search = "";
  url.hash = "";
  url.searchParams.set("slot", slot);
  if (historyId) url.searchParams.set("history", historyId);
  return url.href;
}

function qrSource(slot, historyId = null) {
  return `api/tools/${slot}/qr.svg?target=${encodeURIComponent(toolDeepLink(slot, historyId))}`;
}

function labelEntries(includeFree = false, singleSlot = null) {
  const entries = [];
  state.tools.forEach(tool => {
    if ((!singleSlot || tool.slot === singleSlot) && (includeFree || isOccupied(tool))) entries.push({...tool, label_slot:tool.slot, label_history:null});
    if (!singleSlot) tool.history.forEach(item => entries.push({...item, label_slot:tool.slot, label_history:item.history_id}));
  });
  return entries;
}

function renderLabels(tools) {
  labelSheet.innerHTML = tools.map(tool => `
    <article class="tool-label">
      <img src="${qrSource(tool.label_slot, tool.label_history)}" alt="QR utensile posizione ${tool.label_slot}">
      <div class="label-info"><strong>POSTO ${tool.label_slot}${tool.label_history ? " · ARCHIVIO" : ""}</strong><h3>${esc(tool.description || tool.tool_type || "Posizione libera")}</h3><p>T${esc(tool.t_number ?? "—")} · D${esc(tool.d_offset ?? "—")} · H${esc(tool.h_offset ?? "—")}</p><span>${esc(isOccupied({...tool, cutting_parameters:tool.cutting_parameters || []}) ? (STATUS_LABELS[tool.status] || "In uso") : "Libero")}</span></div>
    </article>`).join("");
}

function openLabels(singleSlot = null) {
  const tools = labelEntries(false, singleSlot);
  renderLabels(tools.length ? tools : labelEntries(true, singleSlot));
  document.querySelector("#show-all-labels").hidden = Boolean(singleSlot);
  labelsDialog.showModal();
}

document.querySelector("#labels-button").addEventListener("click", () => openLabels());
document.querySelector("#tool-qr").addEventListener("click", () => openLabels(state.activeSlot));
document.querySelector("#show-all-labels").addEventListener("click", () => {
  renderLabels(labelEntries(true));
  document.querySelector("#show-all-labels").hidden = true;
});
document.querySelector("#print-labels").addEventListener("click", () => window.print());
document.querySelector("#close-labels-dialog").addEventListener("click", () => labelsDialog.close());
labelsDialog.addEventListener("click", event => { if (event.target === labelsDialog) labelsDialog.close(); });

document.querySelector("#export-button").addEventListener("click", async () => {
  try {
    const data = await request("api/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], {type:"application/json"});
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `cnc-tool-magazine-${new Date().toISOString().slice(0,10)}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#export-pdf-button").addEventListener("click", async () => {
  try {
    const response = await fetch("api/export/pdf");
    if (!response.ok) throw new Error(`Errore HTTP ${response.status}`);
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `cnc-tool-magazine-${new Date().toISOString().slice(0,10)}.pdf`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  } catch (error) { toast(error.message, true); }
});

let toastTimer;
function toast(message, error = false) {
  const element = document.querySelector("#toast");
  element.textContent = message;
  element.className = `toast show${error ? " error" : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.className = "toast", 2800);
}

document.querySelector("#search").addEventListener("input", render);
document.querySelector("#filter").addEventListener("change", render);
document.querySelector("#refresh-button").addEventListener("click", () => loadTools(true));
document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
document.querySelector("#clear-cutting").addEventListener("click", clearCutting);
document.querySelector("#choose-tool-icon").addEventListener("click", () => openIconPicker("active"));
dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
document.querySelector("#close-materials-dialog").addEventListener("click", () => materialsDialog.close());
materialsDialog.addEventListener("click", event => { if (event.target === materialsDialog) materialsDialog.close(); });
document.querySelector("#close-icon-dialog").addEventListener("click", () => iconDialog.close());
iconDialog.addEventListener("click", event => { if (event.target === iconDialog) iconDialog.close(); });

setInterval(() => {
  if (dialog.open && state.activeSlot) {
    const tool = state.tools.find(item => item.slot === state.activeSlot);
    if (tool?.timer_started_at) renderUsage(tool);
  }
}, 1000);

loadTools();
