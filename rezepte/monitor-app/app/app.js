import { callTool } from "./mcp.js";

const items = document.querySelector("#items");
const status = document.querySelector("#status");
const button = document.querySelector("#refresh");

document.querySelector("#query").addEventListener("submit", async event => {
  event.preventDefault();
  if (button.disabled) return;
  button.disabled = true;
  items.replaceChildren();
  status.textContent = "Lade …";
  try {
    const args = { days: Number(document.querySelector("#days").value) };
    const ref = document.querySelector("#ref").value.trim();
    if (ref) args.ref = ref;
    const result = await callTool("usecase_monitor", args);
    const views = Array.isArray(result) ? result : [result];
    for (const view of views) {
      const card = document.createElement("article");
      const title = document.createElement("h2");
      title.textContent = view.name;
      card.append(title);
      const counts = document.createElement("p");
      counts.textContent = `Grün: ${view.green} · Rot: ${view.red} · Wartend: ${view.waiting} · Geplante Kettenstarts: ${view.paused ? "pausiert" : "aktiv"}`;
      card.append(counts);
      for (const text of [view.last_error, view.assumption, ...(view.notices || [])]) {
        if (!text) continue;
        const paragraph = document.createElement("p");
        paragraph.textContent = text;
        card.append(paragraph);
      }
      items.append(card);
    }
    status.textContent = views.length ? "Stand geladen. Zähler hängen von der Aufbewahrung der Quellen ab." : "Keine sichtbaren Use Cases.";
  } catch (error) {
    items.replaceChildren();
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
