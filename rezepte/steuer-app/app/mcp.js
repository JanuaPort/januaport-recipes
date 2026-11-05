let sequence = 0;
let ready;
const pending = new Map();
let bridge;

function bridgeError(code) {
  const messages = {
    abgelehnt: "Anfrage abgewiesen. Rechte prüfen.",
    antwort_ungueltig: "Ungültige Antwort des PC-Fensters.",
    args: "Ungültige Werkzeug-Eingabe.",
    befehl: "Befehl im PC-Fenster nicht verfügbar.",
    fehler: "Werkzeug-Anfrage fehlgeschlagen.",
    nicht_angemeldet: "Im PC-Fenster anmelden und erneut versuchen.",
    nicht_erreichbar: "Anlage nicht erreichbar. Verbindung prüfen.",
    umschlag: "Ungültige Nachricht an das PC-Fenster.",
    zu_gross: "Werkzeug-Anfrage ist zu groß.",
    zu_viele: "Zu viele offene Anfragen. Kurz warten."
  };
  return typeof code === "string" && Object.hasOwn(messages, code) ? messages[code] : messages.fehler;
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function bridgeCall(name, args) {
  const webview = globalThis.chrome.webview;
  if (!bridge) {
    webview.addEventListener("message", event => {
      if (typeof event.data !== "string") return;
      let message;
      try { message = JSON.parse(event.data); } catch { return; }
      if (!isObject(message)) return;
      // Der Host sendet auch den unveränderten Auftrag als Echo zurück.
      if (!Object.hasOwn(message, "ok")) return;
      // Ohne ID ist keine Zuordnung möglich; andere Aufrufe bleiben offen.
      if (message.id === null) return;
      const finish = pending.get(message.id);
      if (!finish) return;
      if (message.ok === true) finish(null, message.ergebnis);
      else if (message.ok === false) finish(new Error(bridgeError(message.fehler)));
      else finish(new Error(bridgeError("antwort_ungueltig")));
    });
    bridge = webview;
  }
  if (typeof name !== "string" || !/^[A-Za-z0-9_.-]{1,128}$/.test(name)) throw new Error(bridgeError("args"));
  if (!isObject(args)) throw new Error(bridgeError("args"));
  const id = `rezept.${++sequence}`;
  let body;
  try {
    body = JSON.stringify({ id, befehl: "werkzeug", args: { name, arguments: args } });
    if (!isObject(JSON.parse(body).args.arguments)) throw new Error();
  } catch { throw new Error(bridgeError("args")); }
  if (new TextEncoder().encode(body).length > 256 * 1024) throw new Error(bridgeError("zu_gross"));
  return new Promise((resolve, reject) => {
    const finish = (error, result) => {
      pending.delete(id);
      clearTimeout(timer);
      if (error) reject(error); else resolve(result);
    };
    // Etwas mehr als die 60 Sekunden des Hosts; kein automatischer Neuversand.
    const timer = setTimeout(() => {
      finish(new Error("Keine Antwort vom PC-Fenster. Stand prüfen."));
    }, 65000);
    pending.set(id, finish);
    try { webview.postMessage(body); }
    catch { finish(new Error(bridgeError("nicht_erreichbar"))); }
  });
}

async function rpc(method, params, notification = false) {
  const request = { jsonrpc: "2.0", method, params };
  if (!notification) request.id = ++sequence;
  const response = await fetch("/mcp", {
    method: "POST",
    redirect: "error",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream",
      "MCP-Protocol-Version": "2025-03-26",
      "X-Jnpt-App": "1"
    },
    body: JSON.stringify(request)
  });
  // 401 heißt: Die Sitzung ist vorbei, etwa nach einem Fassungswechsel. Der App-Host hat sie verworfen.
  if (response.status === 401) throw new Error("Anmeldung beendet. Seite neu laden, um dich neu anzumelden.");
  if (!response.ok) throw new Error(`Anfrage abgewiesen (HTTP ${response.status}).`);
  if (notification) return;
  const text = await response.text();
  const messages = response.headers.get("content-type")?.includes("text/event-stream")
    ? text.split(/\r?\n\r?\n/).filter(Boolean).flatMap(event => {
      const data = event.split(/\r?\n/).filter(line => line.startsWith("data:")).map(line => line.slice(5).trimStart()).join("\n");
      return data ? [JSON.parse(data)] : [];
    }) : [JSON.parse(text)];
  const message = messages.find(value => value.id === request.id);
  if (!message || message.error) throw new Error("Werkzeug-Anfrage fehlgeschlagen.");
  return message.result;
}

export async function callTool(name, args) {
  const result = await toolResult(name, args);
  try { return unpack(result); }
  catch (error) {
    if (!globalThis.chrome?.webview || result?.isError) throw error;
    throw new Error(bridgeError("antwort_ungueltig"));
  }
}

function unpack(result) {
  if (result.isError) throw new Error("Werkzeug-Auftrag abgewiesen. Rechte und aktuellen Stand prüfen.");
  if (result.structuredContent !== undefined) return result.structuredContent;
  const text = result.content?.filter(part => part.type === "text").map(part => part.text).join("\n");
  if (!text) throw new Error("Werkzeug-Antwort fehlt.");
  return JSON.parse(text);
}

async function toolResult(name, args) {
  if (globalThis.chrome?.webview) return bridgeCall(name, args);
  ready ||= (async () => {
    await rpc("initialize", { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "rezept-app", version: "0.1.0" } });
    await rpc("notifications/initialized", {}, true);
  })().catch(error => { ready = null; throw error; });
  await ready;
  return rpc("tools/call", { name, arguments: args });
}
