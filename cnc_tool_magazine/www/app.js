"use strict";

const state = { tools: [], activeSlot: null };
const grid = document.querySelector("#tool-grid");
const dialog = document.querySelector("#tool-dialog");
const toolForm = document.querySelector("#tool-form");
const cuttingForm = document.querySelector("#cutting-form");
const cuttingList = document.querySelector("#cutting-list");
const fields = ["t_number","d_offset","h_offset","diameter_mm","length_mm","description","tool_type","flutes","notes"];
const cuttingFields = ["id","material","coolant","vc_m_min","rpm","fz_mm_tooth","feed_mm_min","ap_mm","ae_mm","notes"];

function esc(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);
}

async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: {"Content-Type":"application/json", ...(options.headers || {})} });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Errore HTTP ${response.status}`);
  return data;
}

function isOccupied(tool) {
  return Boolean(tool.description || tool.tool_type || tool.diameter_mm || tool.length_mm);
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
  grid.querySelectorAll(".tool-card").forEach(button => button.addEventListener("click", () => openTool(Number(button.dataset.slot))));

  const occupied = state.tools.filter(isOccupied).length;
  document.querySelector("#occupied-count").textContent = occupied;
  document.querySelector("#free-count").textContent = 30 - occupied;
  document.querySelector("#material-count").textContent = state.tools.reduce((sum, tool) => sum + tool.cutting_parameters.length, 0);
}

function toolCard(tool) {
  const occupied = isOccupied(tool);
  const title = tool.description || "Posizione libera";
  const materials = tool.cutting_parameters.slice(0, 3).map(item => `<span class="chip">${esc(item.material)}</span>`).join("");
  return `<button class="tool-card ${occupied ? "" : "free"}" data-slot="${tool.slot}">
    <div class="card-head"><span class="slot">${tool.slot}</span><span class="status">${occupied ? "Occupato" : "Libero"}</span></div>
    <h3>${esc(title)}</h3>
    <div class="offsets"><span>T<b>${esc(tool.t_number ?? "—")}</b></span><span>D<b>${esc(tool.d_offset ?? "—")}</b></span><span>H<b>${esc(tool.h_offset ?? "—")}</b></span></div>
    <p class="measure">Ø ${esc(tool.diameter_mm ?? "—")} mm · L ${esc(tool.length_mm ?? "—")} mm${tool.flutes ? ` · Z${esc(tool.flutes)}` : ""}</p>
    <div class="material-chips">${materials}</div>
  </button>`;
}

async function loadTools(showMessage = false) {
  try {
    const data = await request("api/tools");
    state.tools = data.tools;
    document.querySelector("#machine-name").textContent = data.machine.machine_name;
    render();
    if (showMessage) toast("Dati aggiornati");
  } catch (error) { toast(error.message, true); }
}

function openTool(slot) {
  state.activeSlot = slot;
  const tool = state.tools.find(item => item.slot === slot);
  document.querySelector("#slot").value = slot;
  document.querySelector("#dialog-title").textContent = `Posto ${slot}`;
  fields.forEach(field => { toolForm.elements[field].value = tool[field] ?? ""; });
  clearCutting();
  renderCutting(tool);
  dialog.showModal();
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
  renderCutting(tool);
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
dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });

loadTools();
