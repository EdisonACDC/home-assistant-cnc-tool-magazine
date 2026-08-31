"use strict";

const state = { tools: [], inventory: [], templates: [], events: [], validation: {count:0,warnings:[],slots:[]}, visel: null, activeSlot: null, iconTarget: null };
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
const inventoryDialog = document.querySelector("#inventory-dialog");
const inventoryForm = document.querySelector("#inventory-form");
const inventoryList = document.querySelector("#inventory-list");
const materialLibraryDialog = document.querySelector("#material-library-dialog");
const templateForm = document.querySelector("#template-form");
const templateList = document.querySelector("#template-list");
const eventsDialog = document.querySelector("#events-dialog");
const eventsList = document.querySelector("#events-list");
const validationDialog = document.querySelector("#validation-dialog");
const validationList = document.querySelector("#validation-list");
const viselDialog = document.querySelector("#visel-dialog");
const viselForm = document.querySelector("#visel-form");
const searchInput = document.querySelector("#search");
const searchResults = document.querySelector("#search-results");
const clearSearchButton = document.querySelector("#clear-search");
const inventoryFields = ["description","tool_type","icon","diameter_mm","length_mm","thread_pitch_mm","flutes","notes"];
const templateFields = ["name","vc_m_min","fz_mm_tooth","ap_mm","ae_mm","coolant","notes"];
const fields = ["t_number","d_offset","h_offset","diameter_mm","length_mm","description","tool_type","icon","thread_pitch_mm","flutes","status","usage_hours","life_hours","notes"];
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
  {id:"thread_comb", label:"Pettine per filetti", asset:"tap"},
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
  return definition ? `<img class="${className}" src="static/tool-icons/${definition.asset || definition.id}.png" alt="" aria-hidden="true">` : "";
}

function iconLabel(icon) {
  return iconDefinition(icon)?.label || "Nessuna icona";
}

function setToolTypeFromIcon(form, icon) {
  const definition = iconDefinition(icon);
  if (definition) form.elements.tool_type.value = definition.label;
}

function isThreadingIcon(icon) {
  return icon === "tap" || icon === "thread_comb";
}

function updateThreadPitchVisibility(form, fieldId) {
  const active = isThreadingIcon(form.elements.icon.value);
  const field = document.querySelector(fieldId);
  field.hidden = !active;
  field.querySelector("input").required = active;
}

async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: {"Content-Type":"application/json", ...(options.headers || {})} });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Errore HTTP ${response.status}`);
  return data;
}

function isOccupied(tool) {
  return Boolean(tool.description || tool.tool_type || tool.icon || tool.diameter_mm || tool.length_mm || tool.thread_pitch_mm || tool.flutes || tool.notes || tool.cutting_parameters?.length);
}

function render() {
  const filter = document.querySelector("#filter").value;
  const visible = state.tools.filter(tool => {
    const occupied = isOccupied(tool);
    if (filter === "occupied" && !occupied) return false;
    if (filter === "free" && occupied) return false;
    return true;
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

const SEARCH_TYPE_LABELS = {active:"Montato", history:"Storico", inventory:"Officina", material:"Materiale", document:"Documento"};
let searchTimer;

function searchCuttingMarkup(items = []) {
  if (!items.length) return `<span class="search-cutting-empty">Parametri di taglio non inseriti</span>`;
  return `<span class="search-cutting">${items.map(item => `
    <span class="search-cutting-material"><b>${esc(item.material)}</b><span>
      Vc ${esc(item.vc_m_min ?? "—")} m/min · S ${esc(item.rpm ?? "—")} rpm ·
      Fz ${esc(item.fz_mm_tooth ?? "—")} mm/dente · F ${esc(item.feed_mm_min ?? "—")} mm/min ·
      ap ${esc(item.ap_mm ?? "—")} mm · ae ${esc(item.ae_mm ?? "—")} mm${item.coolant ? ` · ${esc(item.coolant)}` : ""}
    </span></span>`).join("")}</span>`;
}

function renderSearchResults(items, query) {
  searchResults.hidden = false;
  searchResults.innerHTML = items.length ? `
    <div class="search-results-head"><strong>${items.length} ${items.length === 1 ? "risultato" : "risultati"}</strong><span>per “${esc(query)}”</span></div>
    <div class="search-results-list">${items.map((item, index) => `
      <button class="search-result" type="button" data-index="${index}">
        <span class="search-result-type type-${esc(item.type)}">${esc(SEARCH_TYPE_LABELS[item.type] || item.type)}</span>
        <span class="search-result-body"><strong>${esc(item.title)}</strong><small>${esc(item.location)} · ${esc(item.detail || "")}</small>${item.type !== "material" ? searchCuttingMarkup(item.cutting_parameters) : ""}</span>
        <span class="search-result-arrow" aria-hidden="true">›</span>
      </button>`).join("")}</div>` : `<div class="search-no-results"><strong>Nessun risultato</strong><p>Prova con descrizione, numero T/D/H, materiale o nome del documento.</p></div>`;
  searchResults.querySelectorAll(".search-result").forEach(button => button.addEventListener("click", () => openSearchResult(items[Number(button.dataset.index)])));
}

function openSearchResult(item) {
  if (item.type === "active" || item.type === "history" || (item.type === "document" && item.slot)) {
    openTool(Number(item.slot), Number(item.history_id) || null);
    return;
  }
  if (item.type === "inventory" || (item.type === "document" && item.inventory_id)) {
    openInventoryDeepLink(Number(item.inventory_id));
    return;
  }
  if (item.type === "material") {
    renderTemplateList();
    materialLibraryDialog.showModal();
    const row = templateList.querySelector(`[data-id="${item.template_id}"]`);
    if (row) {
      row.classList.add("highlighted");
      setTimeout(() => row.scrollIntoView({behavior:"smooth", block:"center"}), 100);
    }
  }
}

async function runGlobalSearch() {
  const query = searchInput.value.trim();
  clearSearchButton.hidden = !query;
  if (!query) {
    searchResults.hidden = true;
    searchResults.innerHTML = "";
    return;
  }
  searchResults.hidden = false;
  searchResults.innerHTML = `<p class="search-loading">Ricerca in corso…</p>`;
  try {
    const data = await request(`api/search?q=${encodeURIComponent(query)}`);
    if (searchInput.value.trim() === query) renderSearchResults(data.results, query);
  } catch (error) { toast(error.message, true); }
}

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runGlobalSearch, 220);
});
clearSearchButton.addEventListener("click", () => {
  searchInput.value = "";
  runGlobalSearch();
  searchInput.focus();
});

function toolCard(tool) {
  const occupied = isOccupied(tool);
  const issues = state.validation.warnings.filter(item => item.slots.includes(tool.slot));
  const title = tool.description || "Posizione libera";
  const materials = tool.cutting_parameters.map(item => `<button class="chip material-chip show-material" data-id="${item.id}" type="button" aria-label="Apri parametri per ${esc(item.material)}">${esc(item.material)}</button>`).join("");
  const status = occupied ? (STATUS_LABELS[tool.status] || "In uso") : "Libero";
  const life = occupied && tool.remaining_percent !== null ? `<span class="life-meter"><i style="width:${tool.remaining_percent}%"></i></span><small>${tool.remaining_percent}% vita residua · ${formatHours(tool.usage_hours_current)}</small>` : "";
  return `<article class="tool-card ${occupied ? "" : "free"} ${issues.length ? "warning" : ""}" data-slot="${tool.slot}" role="button" tabindex="0">
    <div class="card-head"><span class="slot">${tool.slot}</span><span class="status status-${esc(tool.status)}">${esc(status)}</span></div>
    ${issues.length ? `<div class="warning-chip" title="${esc(issues.map(item => item.message).join(" · "))}">⚠ ${issues.length} ${issues.length === 1 ? "segnalazione" : "segnalazioni"}</div>` : ""}
    <div class="tool-title">${toolIcon(tool.icon, "card-tool-icon")}<h3>${esc(title)}</h3></div>
    <div class="offsets"><span>T<b>${esc(tool.t_number ?? "—")}</b></span><span>D<b>${esc(tool.d_offset ?? "—")}</b></span><span>H<b>${esc(tool.h_offset ?? "—")}</b></span></div>
    <p class="measure">Ø ${esc(tool.diameter_mm ?? "—")} mm · L ${esc(tool.length_mm ?? "—")} mm${tool.thread_pitch_mm ? ` · P${esc(tool.thread_pitch_mm)} mm` : ""}${tool.flutes ? ` · Z${esc(tool.flutes)}` : ""}</p>
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
    const [data, templateData, inventoryData, validationData] = await Promise.all([
      request("api/tools"), request("api/material-templates"), request("api/inventory"), request("api/validation")
    ]);
    state.tools = data.tools;
    state.templates = templateData.templates;
    state.inventory = inventoryData.inventory;
    state.validation = validationData;
    document.querySelector("#machine-name").textContent = data.machine.machine_name;
    renderTemplateSelect();
    document.querySelector("#inventory-count").textContent = state.inventory.length;
    document.querySelector("#validation-count").textContent = state.validation.count;
    document.querySelector("#validation-badge").textContent = state.validation.count;
    render();
    if (!state.deepLinkOpened) {
      state.deepLinkOpened = true;
      const url = new URL(window.location.href);
      const slot = Number(url.searchParams.get("slot"));
      const historyId = Number(url.searchParams.get("history")) || null;
      const inventoryId = Number(url.searchParams.get("inventory")) || null;
      if (inventoryId) openInventoryDeepLink(inventoryId);
      else if (Number.isInteger(slot) && slot >= 1 && slot <= 30) openTool(slot, historyId);
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
  updateThreadPitchVisibility(toolForm, "#thread-pitch-field");
  clearCutting();
  renderCutting(tool);
  renderHistory(tool);
  renderUsage(tool);
  renderAttachments(tool.attachments || []);
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
      <div class="history-identity">${toolIcon(item.icon, "history-tool-icon")}<div><strong>${esc(item.description || item.tool_type || "Utensile senza descrizione")}</strong><small>Archiviato ${esc(new Date(item.archived_at).toLocaleString("it-IT"))} · ${esc(STATUS_LABELS[item.status] || "In uso")}${item.thread_pitch_mm ? ` · Passo ${esc(item.thread_pitch_mm)} mm` : ""} · ${formatHours(item.usage_hours)}</small>${(item.attachments || []).map(file => `<a class="history-file" href="api/attachments/${file.id}" target="_blank" rel="noopener">📎 ${esc(file.original_name)}</a>`).join("")}</div></div>
      <div><small>T</small>${esc(item.t_number ?? "—")}</div>
      <div><small>D</small>${esc(item.d_offset ?? "—")}</div>
      <div><small>H</small>${esc(item.h_offset ?? "—")}</div>
      <div class="row-actions"><button class="mini-button history-icon" type="button">Icona</button><label class="mini-button file-button">Allega<input class="history-attachment-file" type="file" accept="application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif,text/plain" hidden></label><button class="mini-button activate" type="button">Monta</button><button class="mini-button delete-history delete" type="button">Elimina</button></div>
    </article>`).join("") : `<p class="subtitle">Nessun utensile nello storico di questa posizione.</p>`;
  historyList.querySelectorAll(".activate").forEach(button => button.addEventListener("click", () => activateHistory(Number(button.closest("article").dataset.id))));
  historyList.querySelectorAll(".history-icon").forEach(button => button.addEventListener("click", () => openIconPicker("history", Number(button.closest("article").dataset.id))));
  historyList.querySelectorAll(".delete-history").forEach(button => button.addEventListener("click", () => removeHistory(Number(button.closest("article").dataset.id))));
  historyList.querySelectorAll(".history-attachment-file").forEach(input => input.addEventListener("change", async event => {
    const historyId = Number(input.closest("article").dataset.id);
    try {
      await uploadAttachment(`api/tools/${state.activeSlot}/history/${historyId}/attachments`, event.target.files[0]);
      await loadTools();
      openRefresh();
      toast("Documento allegato allo storico");
    } catch (error) { toast(error.message, true); }
  }));
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
  document.querySelector("#material-template").value = "";
}

function renderTemplateSelect() {
  const select = document.querySelector("#material-template");
  const current = select.value;
  select.innerHTML = `<option value="">Inserimento manuale</option>${state.templates.map(item => `<option value="${item.id}">${esc(item.name)}</option>`).join("")}`;
  if ([...select.options].some(option => option.value === current)) select.value = current;
}

document.querySelector("#material-template").addEventListener("change", event => {
  const template = state.templates.find(item => item.id === Number(event.target.value));
  if (!template) return;
  const mapping = {material:"name", vc_m_min:"vc_m_min", fz_mm_tooth:"fz_mm_tooth", ap_mm:"ap_mm", ae_mm:"ae_mm", coolant:"coolant", notes:"notes"};
  Object.entries(mapping).forEach(([field, source]) => { cuttingForm.elements[field].value = template[source] ?? ""; });
  toast("Valori proposti dalla libreria: controllali prima di salvarli");
});

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
    setToolTypeFromIcon(toolForm, icon);
    updateThreadPitchVisibility(toolForm, "#thread-pitch-field");
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
  renderAttachments(tool.attachments || []);
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

function fileSize(size) {
  return size >= 1_000_000 ? `${(size / 1_000_000).toFixed(1)} MB` : `${Math.max(1, Math.round(size / 1000))} KB`;
}

function attachmentMarkup(items) {
  return items.length ? items.map(item => `
    <article class="attachment-row" data-id="${item.id}">
      <a href="api/attachments/${item.id}" target="_blank" rel="noopener"><strong>${esc(item.original_name)}</strong><small>${esc(item.mime_type)} · ${fileSize(item.size)}</small></a>
      <button class="mini-button delete delete-attachment" type="button">Elimina</button>
    </article>`).join("") : `<p class="subtitle">Nessun documento allegato.</p>`;
}

function renderAttachments(items) {
  document.querySelector("#attachment-list").innerHTML = attachmentMarkup(items);
  document.querySelector("#attachment-list").querySelectorAll(".delete-attachment").forEach(button => button.addEventListener("click", async () => {
    if (!confirm("Eliminare definitivamente questo allegato?")) return;
    try {
      await request(`api/attachments/${button.closest("article").dataset.id}`, {method:"DELETE"});
      await loadTools();
      openRefresh();
      toast("Allegato eliminato");
    } catch (error) { toast(error.message, true); }
  }));
}

async function uploadAttachment(url, file) {
  if (!file) return;
  if (file.size > 10_000_000) throw new Error("Il file supera il limite di 10 MB");
  const response = await fetch(url, {
    method:"POST",
    headers:{"X-File-Name":encodeURIComponent(file.name), "X-File-Type":file.type || "application/octet-stream"},
    body:file
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Errore HTTP ${response.status}`);
  return data;
}

document.querySelector("#attachment-file").addEventListener("change", async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    await uploadAttachment(`api/tools/${state.activeSlot}/attachments`, file);
    await loadTools();
    openRefresh();
    toast("Documento allegato");
  } catch (error) { toast(error.message, true); }
  event.target.value = "";
});

document.querySelector("#reset-tool").addEventListener("click", async () => {
  if (!confirm(`Svuotare la posizione ${state.activeSlot} e conservare l'utensile in Officina?`)) return;
  try {
    await request(`api/tools/${state.activeSlot}`, {method:"DELETE"});
    await loadTools();
    dialog.close();
    toast(`Posizione ${state.activeSlot} svuotata · utensile spostato in Officina`);
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

document.querySelector("#move-tool").addEventListener("click", async () => {
  const value = prompt(`In quale posizione libera vuoi spostare l'utensile del posto ${state.activeSlot}?`);
  if (value === null) return;
  const target = Number(value);
  if (!Number.isInteger(target) || target < 1 || target > 30 || target === state.activeSlot) {
    toast("Scegli una posizione diversa, compresa tra 1 e 30", true);
    return;
  }
  if (isOccupied(state.tools.find(tool => tool.slot === target))) {
    toast("La posizione di destinazione deve essere libera", true);
    return;
  }
  if (!confirm(`Spostare l'utensile dalla posizione ${state.activeSlot} alla ${target}?`)) return;
  try {
    await request(`api/tools/${state.activeSlot}/move`, {method:"POST", body:JSON.stringify({target_slot:target})});
    await loadTools();
    dialog.close();
    toast(`Utensile spostato nella posizione ${target}`);
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
  const pitch = Number(toolForm.elements.thread_pitch_mm.value);
  const icon = toolForm.elements.icon.value;
  let vc = Number(cuttingForm.elements.vc_m_min.value);
  let rpm = Number(cuttingForm.elements.rpm.value);
  let fz = Number(cuttingForm.elements.fz_mm_tooth.value);
  let feed = Number(cuttingForm.elements.feed_mm_min.value);
  let calculated = false;

  if (isThreadingIcon(icon) && !(pitch > 0)) {
    toast("Inserisci il passo della filettatura", true);
    return;
  }

  if (diameter > 0 && vc > 0) {
    rpm = Math.round((vc * 1000) / (Math.PI * diameter));
    cuttingForm.elements.rpm.value = rpm;
    calculated = true;
  } else if (diameter > 0 && rpm > 0 && !vc) {
    vc = (Math.PI * diameter * rpm) / 1000;
    cuttingForm.elements.vc_m_min.value = vc.toFixed(1);
    calculated = true;
  }
  if (icon === "tap" && rpm > 0 && pitch > 0) {
    feed = rpm * pitch;
    cuttingForm.elements.feed_mm_min.value = feed.toFixed(1);
    calculated = true;
  } else if (rpm > 0 && flutes > 0 && fz > 0) {
    feed = rpm * flutes * fz;
    cuttingForm.elements.feed_mm_min.value = feed.toFixed(1);
    calculated = true;
  } else if (rpm > 0 && flutes > 0 && feed > 0 && !fz) {
    fz = feed / (rpm * flutes);
    cuttingForm.elements.fz_mm_tooth.value = fz.toFixed(3);
    calculated = true;
  }
  const message = icon === "tap"
    ? `Maschio: F = S × passo${pitch > 0 ? ` (${pitch} mm)` : ""}. Controlla i valori prima di salvarli`
    : icon === "thread_comb"
      ? `Pettine: F = S × Z × Fz; passo elica ${pitch || "non inserito"} mm per giro di interpolazione`
      : "Giri e avanzamento calcolati: controlla i valori prima di salvarli";
  toast(calculated ? message : (isThreadingIcon(icon) && !pitch ? "Inserisci il passo della filettatura" : "Inserisci diametro e Vc, oppure giri, taglienti e Fz"), !calculated);
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

function toolDeepLink(slot = null, historyId = null, inventoryId = null) {
  const url = new URL(window.location.href);
  url.search = "";
  url.hash = "";
  if (slot) url.searchParams.set("slot", slot);
  if (historyId) url.searchParams.set("history", historyId);
  if (inventoryId) url.searchParams.set("inventory", inventoryId);
  return url.href;
}

function qrSource(slot = null, historyId = null, inventoryId = null) {
  return `api/qr.svg?target=${encodeURIComponent(toolDeepLink(slot, historyId, inventoryId))}`;
}

function labelEntries(includeFree = false, singleSlot = null) {
  const entries = [];
  state.tools.forEach(tool => {
    if ((!singleSlot || tool.slot === singleSlot) && (includeFree || isOccupied(tool))) entries.push({...tool, label_slot:tool.slot, label_history:null, label_inventory:null});
    if (!singleSlot) tool.history.forEach(item => entries.push({...item, label_slot:tool.slot, label_history:item.history_id, label_inventory:null}));
  });
  if (!singleSlot) state.inventory.forEach(item => entries.push({...item, label_slot:null, label_history:null, label_inventory:item.inventory_id}));
  return entries;
}

function renderLabels(tools) {
  labelSheet.innerHTML = tools.map(tool => `
    <article class="tool-label">
      <img src="${qrSource(tool.label_slot, tool.label_history, tool.label_inventory)}" alt="QR utensile ${tool.label_slot ? `posizione ${tool.label_slot}` : "Officina"}">
      <div class="label-info"><strong>${tool.label_inventory ? "OFFICINA" : `POSTO ${tool.label_slot}${tool.label_history ? " · ARCHIVIO" : ""}`}</strong><h3>${esc(tool.description || tool.tool_type || "Posizione libera")}</h3><p>T${esc(tool.t_number ?? "—")} · D${esc(tool.d_offset ?? "—")} · H${esc(tool.h_offset ?? "—")}</p><span>${esc(isOccupied({...tool, cutting_parameters:tool.cutting_parameters || []}) ? (STATUS_LABELS[tool.status] || "In uso") : "Libero")}</span></div>
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

const inventoryIconSelect = document.querySelector("#inventory-icon-select");
inventoryIconSelect.innerHTML = `<option value="">Nessuna icona</option>${TOOL_ICONS.map(item => `<option value="${item.id}">${esc(item.label)}</option>`).join("")}`;
inventoryIconSelect.addEventListener("change", () => {
  setToolTypeFromIcon(inventoryForm, inventoryIconSelect.value);
  updateThreadPitchVisibility(inventoryForm, "#inventory-thread-pitch-field");
});

async function loadInventory() {
  const data = await request("api/inventory");
  state.inventory = data.inventory;
  renderInventory();
}

function openInventoryDeepLink(id) {
  renderInventory();
  inventoryDialog.showModal();
  const card = inventoryList.querySelector(`[data-id="${id}"]`);
  if (card) {
    card.classList.add("highlighted");
    setTimeout(() => card.scrollIntoView({behavior:"smooth", block:"center"}), 100);
  }
}

function renderInventory() {
  inventoryList.innerHTML = state.inventory.length ? state.inventory.map(tool => `
    <article class="inventory-card" data-id="${tool.inventory_id}">
      <div class="inventory-head">${toolIcon(tool.icon, "history-tool-icon")}<div><strong>${esc(tool.description || tool.tool_type)}</strong><small>${esc(tool.tool_type || "Tipo non indicato")} · Ø ${esc(tool.diameter_mm ?? "—")} mm${tool.thread_pitch_mm ? ` · P${esc(tool.thread_pitch_mm)} mm` : ""} · Z${esc(tool.flutes ?? "—")}</small></div></div>
      <div class="material-chips">${(tool.cutting_parameters || []).map(item => `<span class="chip">${esc(item.material)}</span>`).join("")}</div>
      <div class="inventory-attachments">${attachmentMarkup(tool.attachments || [])}</div>
      <div class="row-actions inventory-actions"><button class="mini-button mount-inventory" type="button">Monta</button><label class="mini-button file-button">Allega<input class="inventory-file" type="file" accept="application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif,text/plain" hidden></label><button class="mini-button delete delete-inventory" type="button">Elimina</button></div>
    </article>`).join("") : `<p class="subtitle">Non ci sono utensili nel magazzino Officina.</p>`;
  inventoryList.querySelectorAll(".mount-inventory").forEach(button => button.addEventListener("click", () => mountInventory(Number(button.closest("article").dataset.id))));
  inventoryList.querySelectorAll(".delete-inventory").forEach(button => button.addEventListener("click", () => removeInventory(Number(button.closest("article").dataset.id))));
  inventoryList.querySelectorAll(".inventory-file").forEach(input => input.addEventListener("change", async event => {
    const id = Number(input.closest("article").dataset.id);
    try {
      await uploadAttachment(`api/inventory/${id}/attachments`, event.target.files[0]);
      await loadInventory();
      toast("Documento allegato");
    } catch (error) { toast(error.message, true); }
  }));
  inventoryList.querySelectorAll(".delete-attachment").forEach(button => button.addEventListener("click", async () => {
    if (!confirm("Eliminare definitivamente questo allegato?")) return;
    try {
      await request(`api/attachments/${button.closest("article").dataset.id}`, {method:"DELETE"});
      await loadInventory();
      toast("Allegato eliminato");
    } catch (error) { toast(error.message, true); }
  }));
}

async function mountInventory(id) {
  const value = prompt("In quale posizione vuoi montare l'utensile? Inserisci un numero da 1 a 30.");
  if (value === null) return;
  const target = Number(value);
  if (!Number.isInteger(target) || target < 1 || target > 30) return toast("Posizione non valida", true);
  const occupied = isOccupied(state.tools.find(tool => tool.slot === target));
  if (!confirm(occupied
    ? `La posizione ${target} è occupata. L'utensile presente verrà spostato in Officina. Continuare?`
    : `Montare l'utensile nella posizione ${target}?`)) return;
  try {
    await request(`api/inventory/${id}/mount`, {method:"POST", body:JSON.stringify({target_slot:target})});
    await Promise.all([loadTools(), loadInventory()]);
    toast(`Utensile montato nella posizione ${target}`);
  } catch (error) { toast(error.message, true); }
}

async function removeInventory(id) {
  if (!confirm("Eliminare definitivamente questo utensile dall'Officina?")) return;
  try {
    await request(`api/inventory/${id}`, {method:"DELETE"});
    await loadInventory();
    toast("Utensile rimosso");
  } catch (error) { toast(error.message, true); }
}

inventoryForm.addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await request("api/inventory", {method:"POST", body:JSON.stringify(formData(inventoryForm, inventoryFields))});
    inventoryForm.reset();
    updateThreadPitchVisibility(inventoryForm, "#inventory-thread-pitch-field");
    await loadInventory();
    toast("Utensile aggiunto in Officina");
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#inventory-button").addEventListener("click", async () => {
  try { await loadInventory(); inventoryDialog.showModal(); } catch (error) { toast(error.message, true); }
});
document.querySelector("#close-inventory-dialog").addEventListener("click", () => inventoryDialog.close());

function clearTemplateForm() {
  templateForm.reset();
  templateForm.elements.id.value = "";
}

function renderTemplateList() {
  templateList.innerHTML = state.templates.map(item => `
    <article class="template-row" data-id="${item.id}"><div><strong>${esc(item.name)}</strong><small>Vc ${esc(item.vc_m_min ?? "—")} · Fz ${esc(item.fz_mm_tooth ?? "—")} · ap ${esc(item.ap_mm ?? "—")} · ae ${esc(item.ae_mm ?? "—")}</small></div><div class="row-actions"><button class="mini-button edit-template" type="button">Modifica</button><button class="mini-button delete delete-template" type="button">Elimina</button></div></article>`).join("");
  templateList.querySelectorAll(".edit-template").forEach(button => button.addEventListener("click", () => {
    const item = state.templates.find(value => value.id === Number(button.closest("article").dataset.id));
    templateForm.elements.id.value = item.id;
    templateFields.forEach(field => { templateForm.elements[field].value = item[field] ?? ""; });
    templateForm.elements.name.focus();
  }));
  templateList.querySelectorAll(".delete-template").forEach(button => button.addEventListener("click", async () => {
    if (!confirm("Eliminare questo modello materiale?")) return;
    try {
      await request(`api/material-templates/${button.closest("article").dataset.id}`, {method:"DELETE"});
      await loadTools();
      renderTemplateList();
      toast("Modello eliminato");
    } catch (error) { toast(error.message, true); }
  }));
}

templateForm.addEventListener("submit", async event => {
  event.preventDefault();
  const id = templateForm.elements.id.value;
  try {
    await request(id ? `api/material-templates/${id}` : "api/material-templates", {method:id ? "PUT" : "POST", body:JSON.stringify(formData(templateForm, templateFields))});
    await loadTools();
    clearTemplateForm();
    renderTemplateList();
    toast("Modello materiale salvato");
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#materials-library-button").addEventListener("click", () => { renderTemplateList(); materialLibraryDialog.showModal(); });
document.querySelector("#clear-template").addEventListener("click", clearTemplateForm);
document.querySelector("#close-material-library-dialog").addEventListener("click", () => materialLibraryDialog.close());

document.querySelector("#events-button").addEventListener("click", async () => {
  try {
    const data = await request("api/events");
    state.events = data.events;
    eventsList.innerHTML = state.events.length ? state.events.map(item => `<article class="event-row"><span class="event-dot"></span><div><strong>${esc(item.description)}</strong><small>${esc(new Date(item.created_at).toLocaleString("it-IT"))}</small></div></article>`).join("") : `<p class="subtitle">Nessun movimento registrato.</p>`;
    eventsDialog.showModal();
  } catch (error) { toast(error.message, true); }
});
document.querySelector("#close-events-dialog").addEventListener("click", () => eventsDialog.close());

function renderValidation() {
  validationList.innerHTML = state.validation.warnings.length ? state.validation.warnings.map(item => `
    <button class="validation-row" type="button" data-slot="${item.slots[0]}">
      <span class="validation-icon">⚠</span><span><strong>${esc(item.message)}</strong><small>Apri la posizione ${item.slots[0]} per correggere il dato</small></span>
    </button>`).join("") : `<div class="validation-ok"><strong>✓ Nessuna segnalazione</strong><p>I numeri T, i correttori D/H e i diametri risultano coerenti.</p></div>`;
  validationList.querySelectorAll(".validation-row").forEach(button => button.addEventListener("click", () => {
    validationDialog.close();
    openTool(Number(button.dataset.slot));
  }));
}

document.querySelector("#validation-button").addEventListener("click", () => { renderValidation(); validationDialog.showModal(); });
document.querySelector("#close-validation-dialog").addEventListener("click", () => validationDialog.close());

document.querySelector("#visel-button").addEventListener("click", async () => {
  try {
    state.visel = await request("api/visel");
    ["controller_model","software_version","host","connection_type","notes"].forEach(field => { viselForm.elements[field].value = state.visel[field] ?? ""; });
    viselDialog.showModal();
  } catch (error) { toast(error.message, true); }
});
viselForm.addEventListener("submit", async event => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(viselForm).entries());
  try {
    state.visel = await request("api/visel", {method:"PUT", body:JSON.stringify(payload)});
    toast("Preparazione Visel salvata · nessun comando inviato");
  } catch (error) { toast(error.message, true); }
});
document.querySelector("#close-visel-dialog").addEventListener("click", () => viselDialog.close());

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
