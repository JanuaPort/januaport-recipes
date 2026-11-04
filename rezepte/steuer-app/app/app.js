import { callTool } from "./mcp.js";

const status = document.querySelector("#status");
const items = document.querySelector("#items");
const confirmation = document.querySelector("#confirmation");
let pending = null;
let busy = false;

function clearPending() {
  pending = null;
  confirmation.hidden = true;
}

function propose(tool, args, question) {
  pending = { tool, args };
  document.querySelector("#question").textContent = question;
  confirmation.hidden = false;
  document.querySelector("#confirm").focus();
}

async function load() {
  clearPending();
  items.replaceChildren();
  const view = await callTool("run_control_read", {});
  if (!Array.isArray(view.items)) throw new Error("Unerwartete Zielsicht.");
  for (const item of view.items) {
    const card = document.createElement("article");
    const title = document.createElement("h2");
    title.textContent = item.name;
    card.append(title);
    const detail = document.createElement("p");
    detail.textContent = item.kind === "schedule"
      ? `${item.cron || ""} · ${item.timezone || ""} · ${item.enabled ? "an" : "aus"}`
      : `Geräte-Setup · ${item.device || ""}`;
    card.append(detail);
    const button = document.createElement("button");
    button.type = "button";
    button.disabled = !item.covered;
    if (item.kind === "schedule") {
      button.textContent = item.enabled ? "Ausschalten …" : "Einschalten …";
      button.addEventListener("click", () => propose("run_control_set_schedule",
        { name: item.name, basis: item.basis, enabled: !item.enabled },
        `Zeitplan ${item.name} ${item.enabled ? "ausschalten" : "einschalten"}?`));
    } else if (item.kind === "setup") {
      button.textContent = "Auslösen …";
      button.addEventListener("click", () => propose("run_control_trigger_setup",
        { device: item.device, pin: item.pin, setup: item.name, frei: {} },
        `Setup ${item.name} auf Gerät ${item.device} einmal auslösen? Die Auslösung hat keinen Rückweg. Freie Eingabewerte bleiben leer.`));
    } else {
      continue;
    }
    card.append(button);
    items.append(card);
  }
  status.textContent = view.items.length ? "Stand geladen. Fehlende Schreibdeckung: Schaltfläche gesperrt." : "Keine aufrufbaren Ziele.";
}

async function action(fn) {
  if (busy) return;
  busy = true;
  document.querySelector("#refresh").disabled = true;
  document.querySelector("#confirm").disabled = true;
  try {
    await fn();
  } catch (error) {
    clearPending();
    items.replaceChildren();
    status.textContent = `${error.message} Stand neu laden. Nach unklarem Versand zuerst den Monitor prüfen.`;
  } finally {
    busy = false;
    document.querySelector("#refresh").disabled = false;
    document.querySelector("#confirm").disabled = false;
  }
}

document.querySelector("#refresh").addEventListener("click", () => action(load));
document.querySelector("#cancel").addEventListener("click", clearPending);
document.querySelector("#confirm").addEventListener("click", () => action(async () => {
  const command = pending;
  clearPending();
  if (!command) return;
  items.replaceChildren();
  await callTool(command.tool, command.args);
  await load();
}));
