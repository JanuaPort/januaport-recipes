// Echter Headless-Browser und HTTP; synthetische MCP-Antworten, kein SSO-Anlagenbeleg.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { resolve, join, extname, sep } from "node:path";
import { setTimeout as pause } from "node:timers/promises";

const root = resolve(import.meta.dirname, "../..");
const edge = process.env.RECIPE_BROWSER;
if (!edge) throw new Error("RECIPE_BROWSER muss auf Chromium oder Edge zeigen.");
const mutation = process.argv[2];
const seen = [];
let covered = true;
let denied = false;
const server = createServer(async (req, res) => {
  try {
    if (req.url === "/mcp") {
      let body = "";
      for await (const chunk of req) body += chunk;
      const input = JSON.parse(body);
      assert.equal(req.headers["x-jnpt-app"], "1");
      if (!input.id) { res.writeHead(202).end(); return; }
      let result = { protocolVersion: "2025-03-26", capabilities: {}, serverInfo: { name: "probe", version: "1" } };
      if (input.method === "tools/call") {
        seen.push(input.params);
        let value = { basis: "neu" };
        if (input.params.name === "run_control_read") value = { items: [
          { kind: "schedule", name: "takt", pin: "beispiel_lauf", basis: "aktuell", enabled: true, cron: "* * * * *", timezone: "UTC", covered },
          { kind: "setup", name: "start", device: "geraet", pin: "beispiel_lauf", covered }
        ] };
        if (input.params.name === "usecase_monitor") value = [{ name: '<img src="x" onerror="window.injected=true">', green: 2, red: 1, waiting: 0, paused: false, last_error: "<b>Hinweis</b>", assumption: "Annahme", notices: [] }];
        result = denied ? { isError: true, content: [] } : { structuredContent: value };
      }
      res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify({ jsonrpc: "2.0", id: input.id, result }));
      return;
    }
    const path = decodeURIComponent(req.url.split("?")[0]);
    if (!/^\/(steuer-app|monitor-app)\/(index\.html|app\.js|mcp\.js|style\.css)$/.test(path)) { res.writeHead(404).end(); return; }
    const [name, file] = path.slice(1).split("/");
    let body = await readFile(join(root, "rezepte", name, "app", file), "utf8");
    if (mutation === "confirm" && name === "steuer-app" && file === "app.js") body = body.replace("pending = { tool, args };", "pending = { tool, args }; callTool(tool, args);");
    if (mutation === "covered" && name === "steuer-app" && file === "app.js") body = body.replace("button.disabled = !item.covered;", "button.disabled = false;");
    if (mutation === "text" && name === "monitor-app" && file === "app.js") body = body.replace("title.textContent = view.name;", "title.innerHTML = view.name;");
    if (mutation === "read" && name === "monitor-app" && file === "app.js") body = body.replace('callTool("usecase_monitor", args)', 'callTool("run_control_trigger_setup", args)');
    if (mutation === "repeat" && name === "steuer-app" && file === "app.js") body = body.replace("await callTool(command.tool, command.args);", "await callTool(command.tool, command.args); await callTool(command.tool, command.args);");
    res.writeHead(200, { "Content-Type": ({ ".js": "text/javascript", ".css": "text/css", ".html": "text/html" })[extname(file)] }).end(body);
  } catch (error) { res.writeHead(500).end(error.message); }
});
await new Promise(done => server.listen(0, "127.0.0.1", done));
const base = `http://127.0.0.1:${server.address().port}`;
const profile = await mkdtemp(join(root, ".arbeit", "browser-"));
const child = spawn(edge, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"], { windowsHide: true, stdio: "ignore" });
let socket;
let browser;
let sequence = 0;
const pending = new Map();
async function until(fn) {
  for (let i = 0; i < 200; i++) { if (await fn()) return; await pause(50); }
  throw new Error("Zeitlimit beim Browseraufbau");
}
function cdp(method, params = {}) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const value = await cdp("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (value.exceptionDetails) throw new Error(JSON.stringify(value.exceptionDetails));
  return value.result.value;
}
async function page(name) {
  await cdp("Page.navigate", { url: `${base}/${name}/index.html?probe=${sequence}` });
  await until(() => evaluate('document.readyState === "complete" && !!document.querySelector("#refresh")'));
}
async function click(selector) { await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); }
const writes = () => seen.filter(call => call.name !== "run_control_read" && call.name !== "usecase_monitor");
try {
  let port;
  await until(async () => { try { port = Number((await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]); return !!port; } catch { return false; } });
  browser = `http://127.0.0.1:${port}`;
  const tabs = await (await fetch(`${browser}/json/list`)).json();
  socket = new WebSocket(tabs.find(tab => tab.type === "page").webSocketDebuggerUrl);
  await new Promise((done, reject) => { socket.onopen = done; socket.onerror = reject; });
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!pending.has(message.id)) return;
    const request = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) request.reject(new Error(message.error.message)); else request.resolve(message.result);
  };
  await cdp("Page.enable");
  await page("steuer-app");
  await click("#refresh");
  await until(() => evaluate('document.querySelectorAll("article").length === 2'));
  await click("article button");
  await pause(200);
  assert.equal(writes().length, 0, "Schreibaufruf vor Bestätigung");
  await click("#cancel");
  await click("#confirm");
  await pause(100);
  assert.equal(writes().length, 0, "Abbrechen erlaubt Schreibaufruf");
  await click("article button");
  await evaluate('document.querySelector("#confirm").click(); document.querySelector("#confirm").click()');
  await until(() => evaluate('document.querySelectorAll("article").length === 2'));
  assert.equal(writes().length, 1, "Mehrfacher Schreibaufruf");
  assert.deepEqual(writes()[0], { name: "run_control_set_schedule", arguments: { name: "takt", basis: "aktuell", enabled: false } });
  await click("article:nth-child(2) button");
  await click("#confirm");
  await until(() => evaluate('document.querySelectorAll("article").length === 2'));
  assert.deepEqual(writes()[1], { name: "run_control_trigger_setup", arguments: { device: "geraet", pin: "beispiel_lauf", setup: "start", frei: {} } });
  covered = false;
  await click("#refresh");
  await until(() => evaluate('document.querySelectorAll("article").length === 2'));
  assert.equal(await evaluate('[...document.querySelectorAll("article button")].every(button => button.disabled)'), true, "Fehlende Deckung nicht gesperrt");
  covered = true;
  await click("#refresh");
  await until(() => evaluate('document.querySelectorAll("article").length === 2'));
  denied = true;
  const before = writes().length;
  await click("article button");
  await click("#confirm");
  await until(() => evaluate('document.querySelector("#status").textContent.includes("abgewiesen")'));
  await pause(300);
  assert.equal(writes().length, before + 1, "Abgewiesener Auftrag automatisch wiederholt");
  assert.equal(await evaluate('document.querySelectorAll("article").length'), 0);
  denied = false;
  seen.length = 0;
  await page("monitor-app");
  await click("#refresh");
  await until(() => evaluate('document.querySelectorAll("article").length === 1'));
  assert.equal(await evaluate('document.querySelectorAll("article img, article b").length'), 0, "Antwort als HTML ausgeführt");
  assert.equal(await evaluate('!!window.injected'), false);
  assert.deepEqual(seen, [{ name: "usecase_monitor", arguments: { days: 7 } }]);
  assert.equal(await evaluate('document.querySelectorAll("button").length'), 1);
  console.log("PASS: Browser-Bestätigung, Abbrechen, Einfachversand, Deckung, Abweisung, Monitor-Lesen und Textdarstellung");
} catch (error) {
  console.error((error.code === "ERR_ASSERTION" ? "FAIL: " : "ERROR: ") + error.message);
  process.exitCode = 1;
} finally {
  if (socket) { await cdp("Browser.close").catch(() => {}); socket.close(); }
  child.kill();
  server.closeAllConnections();
  await new Promise(done => server.close(done));
  await pause(300);
  assert.ok(resolve(profile).startsWith(resolve(root, ".arbeit") + sep));
  await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
