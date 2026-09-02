"use strict";

const MAGAZINE_GROUP_SIZE = 30;
const state = { tools: [], inventory: [], templates: [], events: [], validation: {count:0,warnings:[],slots:[]}, machine: {machine_name:"PentaMac / Visel", magazine_slots:30}, visel: null, activeSlot: null, activeInventoryId: null, dashboardSlot: 1, magazineGroup: 0, iconTarget: null, mountTargetSlot: null };
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
const inventoryToolDialog = document.querySelector("#inventory-tool-dialog");
const inventoryToolForm = document.querySelector("#inventory-tool-form");
const inventoryCuttingForm = document.querySelector("#inventory-cutting-form");
const inventoryCuttingList = document.querySelector("#inventory-cutting-list");
const mountFromWorkshopDialog = document.querySelector("#mount-from-workshop-dialog");
const mountFromWorkshopList = document.querySelector("#mount-from-workshop-list");
const magazineCarousel = document.querySelector("#magazine-carousel");
const machineSettingsDialog = document.querySelector("#machine-settings-dialog");
const machineSettingsForm = document.querySelector("#machine-settings-form");
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
const inventoryFields = ["description","tool_type","icon","d_offset","h_offset","diameter_mm","length_mm","thread_pitch_mm","flutes","notes"];
const templateFields = ["name","tool_icon","vc_m_min","fz_mm_tooth","ap_mm","ae_mm","coolant","notes"];
const fields = ["t_number","d_offset","h_offset","diameter_mm","length_mm","description","tool_type","icon","thread_pitch_mm","flutes","status","usage_hours","life_hours","notes"];
const inventoryDetailFields = ["description","tool_type","icon","thread_pitch_mm","d_offset","h_offset","diameter_mm","length_mm","flutes","status","usage_hours","life_hours","notes"];
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
  {id:"roll_tap", label:"Maschio a rullare"},
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
  return icon === "tap" || icon === "roll_tap" || icon === "thread_comb";
}

function templatesForIcon(icon) {
  const generic = state.templates.filter(item => !item.tool_icon);
  const specific = state.templates.filter(item => item.tool_icon === icon);
  const byName = new Map(generic.map(item => [item.name.toLocaleLowerCase("it"), item]));
  specific.forEach(item => byName.set(item.name.toLocaleLowerCase("it"), item));
  return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name, "it"));
}

function renderPresetPicker(containerId, icon) {
  const container = document.querySelector(containerId);
  const templates = templatesForIcon(icon);
  if (!icon) {
    container.innerHTML = `<p class="subtitle">Scegli prima l’icona del tipo utensile.</p>`;
    return;
  }
  container.innerHTML = templates.map(item => `
    <article class="preset-material" data-template-id="${item.id}">
      <label class="preset-check"><input type="checkbox"><strong>${esc(item.name)}</strong></label>
      <div class="preset-values">
        <label><span>Vc</span><input class="preset-vc" type="number" min="0" step="0.1" value="${esc(item.vc_m_min ?? "")}"></label>
        <label><span>Fz</span><input class="preset-fz" type="number" min="0" step="0.001" value="${esc(item.fz_mm_tooth ?? "")}"></label>
        <label><span>ap</span><input class="preset-ap" type="number" min="0" step="0.01" value="${esc(item.ap_mm ?? "")}"></label>
        <label><span>ae</span><input class="preset-ae" type="number" min="0" step="0.01" value="${esc(item.ae_mm ?? "")}"></label>
      </div>
    </article>`).join("") || `<p class="subtitle">Nessun modello disponibile per questo tipo utensile.</p>`;
}

function selectedPresetCuts(containerId, dimensionsForm) {
  const icon = dimensionsForm.elements.icon.value;
  const diameter = Number(dimensionsForm.elements.diameter_mm.value);
  const flutes = Number(dimensionsForm.elements.flutes.value);
  const pitch = Number(dimensionsForm.elements.thread_pitch_mm.value);
  return [...document.querySelector(containerId).querySelectorAll(".preset-material")]
    .filter(row => row.querySelector("input[type='checkbox']").checked)
    .map(row => {
      const template = state.templates.find(item => item.id === Number(row.dataset.templateId));
      const vc = Number(row.querySelector(".preset-vc").value) || null;
      const fz = Number(row.querySelector(".preset-fz").value) || null;
      const rpm = diameter > 0 && vc > 0 ? Math.round((vc * 1000) / (Math.PI * diameter)) : null;
      const feed = rpm && isThreadingIcon(icon) && pitch > 0
        ? Math.round(rpm * pitch)
        : rpm && flutes > 0 && fz > 0 ? Math.round(rpm * flutes * fz) : null;
      return {
        material:template.name, coolant:template.coolant || "", vc_m_min:vc, rpm,
        fz_mm_tooth:fz, feed_mm_min:feed,
        ap_mm:Number(row.querySelector(".preset-ap").value) || null,
        ae_mm:Number(row.querySelector(".preset-ae").value) || null,
        notes:template.notes || "",
      };
    });
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
  grid.querySelectorAll(".mount-tool-card").forEach(button => button.addEventListener("click", event => {
    event.stopPropagation();
    openMountFromWorkshop(Number(button.closest(".tool-card").dataset.slot));
  }));

  const occupied = state.tools.filter(isOccupied).length;
  document.querySelector("#occupied-count").textContent = occupied;
  document.querySelector("#free-count").textContent = state.tools.length - occupied;
  document.querySelector("#material-count").textContent = state.tools.reduce((sum, tool) => sum + tool.cutting_parameters.length, 0);
  renderMagazine(occupied);
}

function renderMagazine(occupiedCount) {
  const center = document.querySelector("#magazine-center");
  const groupSelect = document.querySelector("#magazine-group-select");
  const previousButton = document.querySelector("#magazine-group-previous");
  const nextButton = document.querySelector("#magazine-group-next");
  magazineCarousel.querySelectorAll(".carousel-slot").forEach(item => item.remove());
  const total = state.tools.length;
  const groupCount = Math.max(1, Math.ceil(total / MAGAZINE_GROUP_SIZE));
  state.magazineGroup = Math.min(Math.max(0, state.magazineGroup), groupCount - 1);
  const groupStart = state.magazineGroup * MAGAZINE_GROUP_SIZE + 1;
  const groupEnd = Math.min(total, groupStart + MAGAZINE_GROUP_SIZE - 1);
  const visibleTools = state.tools.filter(tool => tool.slot >= groupStart && tool.slot <= groupEnd);
  groupSelect.innerHTML = Array.from({length:groupCount}, (_, index) => {
    const start = index * MAGAZINE_GROUP_SIZE + 1;
    const end = Math.min(total, start + MAGAZINE_GROUP_SIZE - 1);
    return `<option value="${index}">${start}–${end}</option>`;
  }).join("");
  groupSelect.value = String(state.magazineGroup);
  previousButton.disabled = state.magazineGroup === 0;
  nextButton.disabled = state.magazineGroup === groupCount - 1;
  visibleTools.forEach((tool, index) => {
    const button = document.createElement("button");
    const issues = state.validation.warnings.some(item => item.slots.includes(tool.slot));
    button.type = "button";
    button.className = `carousel-slot ${isOccupied(tool) ? "occupied" : "free"} ${issues ? "warning" : ""} ${tool.slot === state.dashboardSlot ? "selected" : ""} ${visibleTools.length > 24 ? "compact" : ""}`;
    button.style.setProperty("--slot-angle", `${(index * 360) / Math.max(visibleTools.length, 1)}deg`);
    button.textContent = tool.slot;
    button.setAttribute("aria-label", `Posizione ${tool.slot}: ${isOccupied(tool) ? tool.description || tool.tool_type || "utensile montato" : "libera"}`);
    button.addEventListener("click", () => {
      state.dashboardSlot = tool.slot;
      renderMagazine(occupiedCount);
    });
    magazineCarousel.insertBefore(button, center);
  });
  document.querySelector("#carousel-occupied-count").textContent = occupiedCount;
  document.querySelector("#magazine-title").textContent = `${total} ${total === 1 ? "posizione reale" : "posizioni reali"}`;
  document.querySelector("#magazine-center-count").textContent = groupStart === groupEnd ? `Posto ${groupStart}` : `${groupStart}–${groupEnd}`;
  renderDashboardTool();
}

function selectMagazineGroup(index) {
  const groupCount = Math.max(1, Math.ceil(state.tools.length / MAGAZINE_GROUP_SIZE));
  state.magazineGroup = Math.min(Math.max(0, Number(index) || 0), groupCount - 1);
  const firstSlot = state.magazineGroup * MAGAZINE_GROUP_SIZE + 1;
  const lastSlot = Math.min(state.tools.length, firstSlot + MAGAZINE_GROUP_SIZE - 1);
  if (state.dashboardSlot < firstSlot || state.dashboardSlot > lastSlot) state.dashboardSlot = firstSlot;
  renderMagazine(state.tools.filter(isOccupied).length);
}

function revealMagazineSlot(slot) {
  if (!Number.isInteger(slot) || slot < 1 || slot > state.tools.length) return;
  state.dashboardSlot = slot;
  state.magazineGroup = Math.floor((slot - 1) / MAGAZINE_GROUP_SIZE);
  renderMagazine(state.tools.filter(isOccupied).length);
}

function renderDashboardTool() {
  const tool = state.tools.find(item => item.slot === state.dashboardSlot) || state.tools[0];
  if (!tool) return;
  state.dashboardSlot = tool.slot;
  const occupied = isOccupied(tool);
  document.querySelector("#dashboard-position").textContent = `Posizione ${tool.slot}`;
  document.querySelector("#dashboard-description").textContent = occupied ? tool.description || tool.tool_type || "Utensile montato" : "Posizione libera";
  document.querySelector("#dashboard-tool-icon").innerHTML = occupied ? toolIcon(tool.icon, "card-tool-icon") : `<span class="empty-tool-icon">＋</span>`;
  document.querySelector("#dashboard-t").textContent = tool.t_number ?? "—";
  document.querySelector("#dashboard-d").textContent = tool.d_offset ?? "—";
  document.querySelector("#dashboard-h").textContent = tool.h_offset ?? "—";
  document.querySelector("#dashboard-measure").textContent = occupied ? `Ø ${tool.diameter_mm ?? "—"} mm · L ${tool.length_mm ?? "—"} mm${tool.thread_pitch_mm ? ` · Passo ${tool.thread_pitch_mm} mm` : ""}` : "Nessun utensile montato";
  document.querySelector("#dashboard-materials").innerHTML = occupied ? tool.cutting_parameters.slice(0, 5).map(item => `<button class="dashboard-material" type="button" data-id="${item.id}"><strong>${esc(item.material)}</strong><span>F ${esc(item.feed_mm_min ?? "—")}</span><span>S ${esc(item.rpm ?? "—")}</span></button>`).join("") : "";
  document.querySelectorAll("#dashboard-materials .dashboard-material").forEach(button => button.addEventListener("click", () => openMaterial(tool.slot, Number(button.dataset.id))));
  document.querySelector("#dashboard-open-tool").hidden = !occupied;
  document.querySelector("#dashboard-mount-tool").hidden = occupied;
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
    ${occupied ? "" : `<button class="button secondary mount-tool-card" type="button">Monta utensile</button>`}
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
      <div class="form-actions"><button class="button edit-popup-material" type="button">Modifica parametri</button></div>
    </article>`;
  materialsDialogList.querySelector(".edit-popup-material").addEventListener("click", () => {
    materialsDialog.close();
    openTool(slot);
    editCutting(materialId);
  });
  materialsDialog.showModal();
}

async function loadTools(showMessage = false) {
  try {
    const [data, templateData, inventoryData, validationData] = await Promise.all([
      request("api/tools"), request("api/material-templates"), request("api/inventory"), request("api/validation")
    ]);
    state.tools = data.tools;
    state.machine = data.machine;
    if (!state.tools.some(tool => tool.slot === state.dashboardSlot)) state.dashboardSlot = state.tools[0]?.slot || 1;
    state.templates = templateData.templates;
    state.inventory = inventoryData.inventory;
    state.validation = validationData;
    document.querySelector("#machine-name").textContent = data.machine.machine_name;
    document.querySelector("#filter option[value='all']").textContent = `Tutte le ${data.machine.magazine_slots} posizioni`;
    machineSettingsForm.elements.magazine_slots.value = data.machine.magazine_slots;
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
      else if (Number.isInteger(slot) && slot >= 1 && slot <= state.tools.length) openTool(slot, historyId);
    }
    if (showMessage) toast("Dati aggiornati");
  } catch (error) { toast(error.message, true); }
}

function openTool(slot, historyId = null) {
  revealMagazineSlot(slot);
  state.activeSlot = slot;
  const tool = state.tools.find(item => item.slot === slot);
  document.querySelector("#slot").value = slot;
  document.querySelector("#dialog-title").textContent = `Posto ${slot}`;
  fields.forEach(field => { toolForm.elements[field].value = tool[field] ?? ""; });
  renderSelectedIcon(tool.icon);
  updateThreadPitchVisibility(toolForm, "#thread-pitch-field");
  renderPresetPicker("#tool-preset-list", tool.icon);
  renderTemplateSelect(tool.icon);
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

function renderTemplateSelect(icon = toolForm.elements.icon.value) {
  const select = document.querySelector("#material-template");
  const current = select.value;
  select.innerHTML = `<option value="">Inserimento manuale</option>${templatesForIcon(icon).map(item => `<option value="${item.id}">${esc(item.name)}</option>`).join("")}`;
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
    renderPresetPicker("#tool-preset-list", icon);
    renderTemplateSelect(icon);
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
    const presets = selectedPresetCuts("#tool-preset-list", toolForm);
    for (const material of presets) {
      await request(`api/tools/${state.activeSlot}/cutting`, {method:"PUT", body:JSON.stringify(material)});
    }
    await loadTools();
    openRefresh();
    toast(`Utensile del posto ${state.activeSlot} salvato${presets.length ? ` · ${presets.length} materiali aggiunti` : ""}`);
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
  renderPresetPicker("#tool-preset-list", tool.icon);
  renderTemplateSelect(tool.icon);
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
  const value = prompt(`In quale posizione vuoi duplicare l'utensile del posto ${state.activeSlot}? Inserisci un numero da 1 a ${state.tools.length}.`);
  if (value === null) return;
  const target = Number(value);
  if (!Number.isInteger(target) || target < 1 || target > state.tools.length || target === state.activeSlot) {
    toast(`Scegli una posizione diversa, compresa tra 1 e ${state.tools.length}`, true);
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
  if (!Number.isInteger(target) || target < 1 || target > state.tools.length || target === state.activeSlot) {
    toast(`Scegli una posizione diversa, compresa tra 1 e ${state.tools.length}`, true);
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
  const value = prompt(`Da quale posizione vuoi copiare i materiali nel posto ${state.activeSlot}? Inserisci un numero da 1 a ${state.tools.length}.`);
  if (value === null) return;
  const source = Number(value);
  if (!Number.isInteger(source) || source < 1 || source > state.tools.length || source === state.activeSlot) {
    toast(`Scegli una posizione di origine diversa, compresa tra 1 e ${state.tools.length}`, true);
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
  if ((icon === "tap" || icon === "roll_tap") && rpm > 0 && pitch > 0) {
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
    : icon === "roll_tap"
      ? `Maschio a rullare: F = S × passo${pitch > 0 ? ` (${pitch} mm)` : ""}. Controlla i valori prima di salvarli`
    : icon === "thread_comb"
      ? `Pettine: F = S × Z × Fz; passo elica ${pitch || "non inserito"} mm per giro di interpolazione`
      : "Giri e avanzamento calcolati: controlla i valori prima di salvarli";
  toast(calculated ? message : (isThreadingIcon(icon) && !pitch ? "Inserisci il passo della filettatura" : "Inserisci diametro e Vc, oppure giri, taglienti e Fz"), !calculated);
});

const importFile = document.querySelector("#import-file");
const fileManagerDialog = document.querySelector("#file-manager-dialog");
document.querySelector("#manage-files-button").addEventListener("click", () => fileManagerDialog.showModal());
document.querySelector("#close-file-manager-dialog").addEventListener("click", () => fileManagerDialog.close());
fileManagerDialog.addEventListener("click", event => {
  if (event.target.closest(".file-manager-action")) fileManagerDialog.close();
}, true);
fileManagerDialog.addEventListener("click", event => {
  if (event.target === fileManagerDialog) fileManagerDialog.close();
});
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
    if (data.schema_version !== 1 || !Array.isArray(data.tools) || data.tools.length < 1 || data.tools.length > 250) {
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
document.querySelector("#inventory-tool-icon").innerHTML = inventoryIconSelect.innerHTML;
document.querySelector("#template-tool-icon").innerHTML = `<option value="">Generico per tutti</option>${TOOL_ICONS.map(item => `<option value="${item.id}">${esc(item.label)}</option>`).join("")}`;
document.querySelector("#template-filter-icon").innerHTML = `<option value="all">Tutti i tipi</option><option value="">Generici</option>${TOOL_ICONS.map(item => `<option value="${item.id}">${esc(item.label)}</option>`).join("")}`;
inventoryIconSelect.addEventListener("change", () => {
  setToolTypeFromIcon(inventoryForm, inventoryIconSelect.value);
  updateThreadPitchVisibility(inventoryForm, "#inventory-thread-pitch-field");
  renderPresetPicker("#inventory-preset-list", inventoryIconSelect.value);
});
renderPresetPicker("#inventory-preset-list", "");

async function loadInventory() {
  const data = await request("api/inventory");
  state.inventory = data.inventory;
  renderInventory();
}

function openInventoryDeepLink(id) {
  inventoryDialog.close();
  openInventoryTool(id);
}

function renderInventory() {
  inventoryList.innerHTML = state.inventory.length ? state.inventory.map(tool => `
    <article class="inventory-card" data-id="${tool.inventory_id}">
      <div class="inventory-head">${toolIcon(tool.icon, "history-tool-icon")}<div><strong>${esc(tool.description || tool.tool_type)}</strong><small>D${esc(tool.d_offset ?? "—")} · H${esc(tool.h_offset ?? "—")} · ${esc(tool.tool_type || "Tipo non indicato")} · Ø ${esc(tool.diameter_mm ?? "—")} mm${tool.thread_pitch_mm ? ` · P${esc(tool.thread_pitch_mm)} mm` : ""} · Z${esc(tool.flutes ?? "—")}</small></div></div>
      <div class="material-chips">${(tool.cutting_parameters || []).map(item => `<button class="chip inventory-material-chip" data-index="${item.inventory_cut_index}" type="button">${esc(item.material)}</button>`).join("")}</div>
      <div class="inventory-attachments">${attachmentMarkup(tool.attachments || [])}</div>
      <div class="row-actions inventory-actions"><button class="mini-button open-inventory" type="button">Apri scheda</button><button class="mini-button mount-inventory" type="button">Monta</button><label class="mini-button file-button">Allega<input class="inventory-file" type="file" accept="application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif,text/plain" hidden></label><button class="mini-button delete delete-inventory" type="button">Elimina</button></div>
    </article>`).join("") : `<p class="subtitle">Non ci sono utensili nel magazzino Officina.</p>`;
  inventoryList.querySelectorAll(".open-inventory").forEach(button => button.addEventListener("click", () => openInventoryTool(Number(button.closest("article").dataset.id))));
  inventoryList.querySelectorAll(".inventory-material-chip").forEach(button => button.addEventListener("click", () => openInventoryMaterial(Number(button.closest("article").dataset.id), Number(button.dataset.index))));
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

function activeInventoryTool() {
  return state.inventory.find(item => item.inventory_id === state.activeInventoryId);
}

function renderInventoryTemplateSelect() {
  const select = document.querySelector("#inventory-material-template");
  const icon = inventoryToolForm.elements.icon.value;
  select.innerHTML = `<option value="">Inserimento manuale</option>${templatesForIcon(icon).map(item => `<option value="${item.id}">${esc(item.name)}</option>`).join("")}`;
}

function clearInventoryCutting() {
  inventoryCuttingForm.reset();
  inventoryCuttingForm.elements.original_material.value = "";
  renderInventoryTemplateSelect();
}

function renderInventoryCutting() {
  const tool = activeInventoryTool();
  const cuts = tool?.cutting_parameters || [];
  inventoryCuttingList.innerHTML = cuts.length ? cuts.map(item => `
    <article class="cutting-row" data-index="${item.inventory_cut_index}">
      <div><strong>${esc(item.material)}</strong><small>${esc(item.coolant || "Senza refrigerazione indicata")}</small></div>
      <div><small>Vc</small>${esc(item.vc_m_min ?? "—")} m/min</div>
      <div><small>S</small>${esc(item.rpm ?? "—")} rpm</div>
      <div><small>Fz</small>${esc(item.fz_mm_tooth ?? "—")}</div>
      <div><small>F</small>${esc(item.feed_mm_min ?? "—")} mm/min</div>
      <div class="row-actions"><button class="mini-button edit-inventory-cutting" type="button">Modifica</button><button class="mini-button delete delete-inventory-cutting" type="button">Elimina</button></div>
    </article>`).join("") : `<p class="subtitle">Nessun materiale inserito per questo utensile.</p>`;
  inventoryCuttingList.querySelectorAll(".edit-inventory-cutting").forEach(button => button.addEventListener("click", () => {
    const item = activeInventoryTool().cutting_parameters.find(value => value.inventory_cut_index === Number(button.closest("article").dataset.index));
    inventoryCuttingForm.elements.original_material.value = item.material;
    cuttingFields.filter(field => field !== "id").forEach(field => { inventoryCuttingForm.elements[field].value = item[field] ?? ""; });
    inventoryCuttingForm.elements.material.focus();
  }));
  inventoryCuttingList.querySelectorAll(".delete-inventory-cutting").forEach(button => button.addEventListener("click", async () => {
    if (!confirm("Eliminare questi parametri di taglio dall’utensile in Officina?")) return;
    try {
      await request(`api/inventory/${state.activeInventoryId}/cutting/${button.closest("article").dataset.index}`, {method:"DELETE"});
      await loadInventory();
      renderInventoryCutting();
      clearInventoryCutting();
      toast("Parametri eliminati");
    } catch (error) { toast(error.message, true); }
  }));
}

function openInventoryTool(id) {
  const tool = state.inventory.find(item => item.inventory_id === id);
  if (!tool) return;
  state.activeInventoryId = id;
  document.querySelector("#inventory-tool-title").textContent = tool.description || tool.tool_type || "Utensile Officina";
  inventoryDetailFields.forEach(field => { inventoryToolForm.elements[field].value = tool[field] ?? ""; });
  updateThreadPitchVisibility(inventoryToolForm, "#inventory-tool-thread-pitch-field");
  renderInventoryTemplateSelect();
  clearInventoryCutting();
  renderInventoryCutting();
  if (!inventoryToolDialog.open) inventoryToolDialog.showModal();
}

function openInventoryMaterial(id, cuttingIndex) {
  const tool = state.inventory.find(item => item.inventory_id === id);
  const item = tool?.cutting_parameters.find(value => value.inventory_cut_index === cuttingIndex);
  if (!tool || !item) return;
  document.querySelector("#materials-dialog-title").textContent = item.material;
  document.querySelector("#materials-dialog-tool").textContent = `Officina · ${tool.description || tool.tool_type || "Utensile"}`;
  document.querySelector("#materials-dialog-icon").innerHTML = toolIcon(tool.icon, "popup-tool-icon");
  materialsDialogList.innerHTML = `
    <article class="material-detail"><div class="material-detail-head"><h3>Parametri di taglio</h3><span class="chip">${esc(item.coolant || "Refrigerazione non indicata")}</span></div>
      <div class="parameter-grid">
        <div><small>Velocità Vc</small><strong>${parameterValue(item.vc_m_min, " m/min")}</strong></div><div><small>Giri S</small><strong>${parameterValue(item.rpm, " rpm")}</strong></div>
        <div><small>Avanzamento Fz</small><strong>${parameterValue(item.fz_mm_tooth, " mm/dente")}</strong></div><div><small>Avanzamento F</small><strong>${parameterValue(item.feed_mm_min, " mm/min")}</strong></div>
        <div><small>Profondità ap</small><strong>${parameterValue(item.ap_mm, " mm")}</strong></div><div><small>Larghezza ae</small><strong>${parameterValue(item.ae_mm, " mm")}</strong></div>
      </div>${item.notes ? `<p class="material-notes"><strong>Note:</strong> ${esc(item.notes)}</p>` : ""}
      <div class="form-actions"><button class="button edit-inventory-popup-material" type="button">Modifica parametri</button></div>
    </article>`;
  materialsDialogList.querySelector(".edit-inventory-popup-material").addEventListener("click", () => {
    materialsDialog.close();
    openInventoryTool(id);
    const editButton = inventoryCuttingList.querySelector(`[data-index="${cuttingIndex}"] .edit-inventory-cutting`);
    editButton?.click();
  });
  materialsDialog.showModal();
}

document.querySelector("#inventory-tool-icon").addEventListener("change", event => {
  setToolTypeFromIcon(inventoryToolForm, event.target.value);
  updateThreadPitchVisibility(inventoryToolForm, "#inventory-tool-thread-pitch-field");
  renderInventoryTemplateSelect();
});

document.querySelector("#inventory-material-template").addEventListener("change", event => {
  const template = state.templates.find(item => item.id === Number(event.target.value));
  if (!template) return;
  const mapping = {material:"name", vc_m_min:"vc_m_min", fz_mm_tooth:"fz_mm_tooth", ap_mm:"ap_mm", ae_mm:"ae_mm", coolant:"coolant", notes:"notes"};
  Object.entries(mapping).forEach(([field, source]) => { inventoryCuttingForm.elements[field].value = template[source] ?? ""; });
});

inventoryToolForm.addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await request(`api/inventory/${state.activeInventoryId}`, {method:"PUT", body:JSON.stringify(formData(inventoryToolForm, inventoryDetailFields))});
    await loadInventory();
    openInventoryTool(state.activeInventoryId);
    toast("Scheda utensile Officina salvata");
  } catch (error) { toast(error.message, true); }
});

inventoryCuttingForm.addEventListener("submit", async event => {
  event.preventDefault();
  const payload = formData(inventoryCuttingForm, ["original_material", ...cuttingFields.filter(field => field !== "id")]);
  try {
    await request(`api/inventory/${state.activeInventoryId}/cutting`, {method:"PUT", body:JSON.stringify(payload)});
    await loadInventory();
    renderInventoryCutting();
    clearInventoryCutting();
    toast("Materiale Officina salvato");
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#clear-inventory-cutting").addEventListener("click", clearInventoryCutting);
document.querySelector("#inventory-tool-mount").addEventListener("click", () => mountInventory(state.activeInventoryId));
document.querySelector("#close-inventory-tool-dialog").addEventListener("click", () => inventoryToolDialog.close());

async function mountInventory(id) {
  const value = prompt(`In quale posizione vuoi montare l'utensile? Inserisci un numero da 1 a ${state.tools.length}.`);
  if (value === null) return;
  const target = Number(value);
  if (!Number.isInteger(target) || target < 1 || target > state.tools.length) return toast("Posizione non valida", true);
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

function renderMountFromWorkshop() {
  mountFromWorkshopList.innerHTML = state.inventory.length ? state.inventory.map(tool => `
    <article class="mount-workshop-card" data-id="${tool.inventory_id}">
      <div class="inventory-head">${toolIcon(tool.icon, "history-tool-icon")}<div><strong>${esc(tool.description || tool.tool_type || "Utensile")}</strong><small>D${esc(tool.d_offset ?? "—")} · H${esc(tool.h_offset ?? "—")} · Ø ${esc(tool.diameter_mm ?? "—")} mm${tool.thread_pitch_mm ? ` · P${esc(tool.thread_pitch_mm)} mm` : ""}</small></div></div>
      <button class="button mount-workshop-tool" type="button">Monta qui</button>
    </article>`).join("") : `<div class="empty-workshop-choice"><strong>Nessun utensile disponibile in Officina</strong><p>Aggiungi prima un utensile nella sezione Officina.</p></div>`;
  mountFromWorkshopList.querySelectorAll(".mount-workshop-tool").forEach(button => button.addEventListener("click", async () => {
    const inventoryId = Number(button.closest("article").dataset.id);
    try {
      await request(`api/inventory/${inventoryId}/mount`, {method:"POST", body:JSON.stringify({target_slot:state.mountTargetSlot})});
      const target = state.mountTargetSlot;
      mountFromWorkshopDialog.close();
      await Promise.all([loadTools(), loadInventory()]);
      toast(`Utensile montato nella posizione ${target}`);
    } catch (error) { toast(error.message, true); }
  }));
}

function openMountFromWorkshop(slot) {
  state.mountTargetSlot = slot;
  document.querySelector("#mount-from-workshop-title").textContent = `Monta utensile nella posizione ${slot}`;
  renderMountFromWorkshop();
  mountFromWorkshopDialog.showModal();
}

document.querySelector("#close-mount-from-workshop-dialog").addEventListener("click", () => mountFromWorkshopDialog.close());
mountFromWorkshopDialog.addEventListener("click", event => {
  if (event.target === mountFromWorkshopDialog) mountFromWorkshopDialog.close();
});

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
    const payload = formData(inventoryForm, inventoryFields);
    payload.cutting_parameters = selectedPresetCuts("#inventory-preset-list", inventoryForm);
    const result = await request("api/inventory", {method:"POST", body:JSON.stringify(payload)});
    inventoryForm.reset();
    updateThreadPitchVisibility(inventoryForm, "#inventory-thread-pitch-field");
    await loadInventory();
    renderPresetPicker("#inventory-preset-list", "");
    toast(`Utensile aggiunto in Officina${payload.cutting_parameters.length ? ` · ${payload.cutting_parameters.length} materiali` : ""}`);
    openInventoryTool(result.inventory_id);
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#inventory-button").addEventListener("click", async () => {
  try { await loadInventory(); inventoryDialog.showModal(); } catch (error) { toast(error.message, true); }
});
document.querySelector("#close-inventory-dialog").addEventListener("click", () => inventoryDialog.close());

document.querySelector("#empty-all-button").addEventListener("click", async () => {
  const occupied = state.tools.filter(isOccupied).length;
  if (!occupied) {
    toast("Il magazzino macchina è già vuoto");
    return;
  }
  if (!confirm(`Spostare tutti i ${occupied} utensili montati in Officina?\n\nLe ${state.tools.length} posizioni macchina verranno liberate. Nessun utensile sarà eliminato.`)) return;
  try {
    const result = await request("api/tools/empty-all", {method:"POST"});
    await loadTools();
    toast(`${result.moved} utensili spostati in Officina`);
  } catch (error) { toast(error.message, true); }
});

function clearTemplateForm() {
  templateForm.reset();
  templateForm.elements.id.value = "";
}

function renderTemplateList() {
  const filterIcon = document.querySelector("#template-filter-icon").value;
  const visibleTemplates = state.templates.filter(item => filterIcon === "all" || item.tool_icon === filterIcon);
  templateList.innerHTML = visibleTemplates.map(item => `
    <article class="template-row" data-id="${item.id}"><div class="template-identity">${toolIcon(item.tool_icon, "history-tool-icon")}<div><strong>${esc(item.name)}</strong><small>${esc(item.tool_icon ? iconLabel(item.tool_icon) : "Generico per tutti")} · Vc ${esc(item.vc_m_min ?? "—")} · Fz ${esc(item.fz_mm_tooth ?? "—")} · ap ${esc(item.ap_mm ?? "—")} · ae ${esc(item.ae_mm ?? "—")}</small></div></div><div class="row-actions"><button class="mini-button edit-template" type="button">Modifica</button><button class="mini-button delete delete-template" type="button">Elimina</button></div></article>`).join("") || `<p class="subtitle">Nessun modello per questo tipo utensile.</p>`;
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
document.querySelector("#template-filter-icon").addEventListener("change", renderTemplateList);
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

const machineTableDialog = document.querySelector("#machine-table-dialog");
const machineTableForm = document.querySelector("#machine-table-form");
const toolTypeColorList = document.querySelector("#tool-type-color-list");

function renderToolTypeColors(values) {
  toolTypeColorList.innerHTML = TOOL_ICONS.map(item => `
    <label class="tool-type-color" data-icon="${item.id}">
      ${toolIcon(item.id, "color-tool-icon")}
      <span>${esc(item.label)}</span>
      <input type="color" value="${esc(values[item.id] || "#7B8794")}" aria-label="Colore ${esc(item.label)}">
      <code>${esc(values[item.id] || "#7B8794")}</code>
    </label>`).join("");
  toolTypeColorList.querySelectorAll("input[type=color]").forEach(input => input.addEventListener("input", () => {
    input.closest("label").querySelector("code").textContent = input.value.toUpperCase();
  }));
}

function selectedToolTypeColors() {
  return Object.fromEntries([...toolTypeColorList.querySelectorAll(".tool-type-color")].map(row => [
    row.dataset.icon, row.querySelector("input").value.toUpperCase()
  ]));
}

async function saveTableColors(showMessage = true) {
  const data = await request("api/tool-type-colors", {
    method:"PUT", body:JSON.stringify({colors:selectedToolTypeColors()})
  });
  if (showMessage) toast("Colori della tabella salvati");
  return data.colors;
}

document.querySelector("#machine-table-button").addEventListener("click", async () => {
  try {
    const data = await request("api/tool-type-colors");
    renderToolTypeColors(data.colors);
    machineTableDialog.showModal();
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#save-table-colors").addEventListener("click", async () => {
  try { await saveTableColors(); } catch (error) { toast(error.message, true); }
});

machineTableForm.addEventListener("submit", async event => {
  event.preventDefault();
  try {
    await saveTableColors(false);
    const paperFormat = machineTableForm.elements.paper_format.value;
    const response = await fetch(`api/export/machine-table.pdf?format=${encodeURIComponent(paperFormat)}`);
    if (!response.ok) throw new Error(`Errore HTTP ${response.status}`);
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `tabella-generale-utensili-${paperFormat.toLowerCase()}-${new Date().toISOString().slice(0,10)}.pdf`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    toast(`Tabella generale PDF ${paperFormat} generata`);
  } catch (error) { toast(error.message, true); }
});

document.querySelector("#close-machine-table-dialog").addEventListener("click", () => machineTableDialog.close());

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
document.querySelector("#dashboard-open-tool").addEventListener("click", () => openTool(state.dashboardSlot));
document.querySelector("#dashboard-mount-tool").addEventListener("click", () => openMountFromWorkshop(state.dashboardSlot));
document.querySelector("#magazine-center").addEventListener("click", () => openTool(state.dashboardSlot));
document.querySelector("#magazine-group-select").addEventListener("change", event => selectMagazineGroup(event.target.value));
document.querySelector("#magazine-group-previous").addEventListener("click", () => selectMagazineGroup(state.magazineGroup - 1));
document.querySelector("#magazine-group-next").addEventListener("click", () => selectMagazineGroup(state.magazineGroup + 1));
document.querySelector("#machine-settings-button").addEventListener("click", () => {
  machineSettingsForm.elements.magazine_slots.value = state.tools.length;
  machineSettingsDialog.showModal();
});
document.querySelector("#close-machine-settings-dialog").addEventListener("click", () => machineSettingsDialog.close());
machineSettingsDialog.addEventListener("click", event => { if (event.target === machineSettingsDialog) machineSettingsDialog.close(); });
machineSettingsForm.addEventListener("submit", async event => {
  event.preventDefault();
  const requested = Number(machineSettingsForm.elements.magazine_slots.value);
  if (!Number.isInteger(requested) || requested < 1 || requested > 250) return toast("Inserisci un numero di posizioni da 1 a 250", true);
  if (requested < state.tools.length && !confirm(`Ridurre il magazzino da ${state.tools.length} a ${requested} posizioni?\n\nGli utensili e lo storico delle posizioni eliminate verranno trasferiti in Officina.`)) return;
  try {
    const result = await request("api/machine", {method:"PUT", body:JSON.stringify({magazine_slots:requested})});
    machineSettingsDialog.close();
    await loadTools();
    toast(result.moved_to_inventory ? `${result.magazine_slots} posizioni salvate · ${result.moved_to_inventory} utensili trasferiti in Officina` : `${result.magazine_slots} posizioni salvate`);
  } catch (error) { toast(error.message, true); }
});
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
