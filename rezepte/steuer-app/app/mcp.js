let sequence = 0;
let ready;

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
  ready ||= (async () => {
    await rpc("initialize", { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "rezept-app", version: "0.1.0" } });
    await rpc("notifications/initialized", {}, true);
  })().catch(error => { ready = null; throw error; });
  await ready;
  const result = await rpc("tools/call", { name, arguments: args });
  if (result.isError) throw new Error("Werkzeug-Auftrag abgewiesen. Rechte und aktuellen Stand prüfen.");
  if (result.structuredContent !== undefined) return result.structuredContent;
  const text = result.content?.filter(part => part.type === "text").map(part => part.text).join("\n");
  if (!text) throw new Error("Werkzeug-Antwort fehlt.");
  return JSON.parse(text);
}
