// Echter mcp.js-Adapter in isoliertem JS-Kontext; nur Host, HTTP und Uhr sind Fakes.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { test } from "node:test";
import vm from "node:vm";

const root = resolve(import.meta.dirname, "../..");
const sources = ["steuer-app", "monitor-app"].map(name =>
  readFileSync(resolve(root, "rezepte", name, "app/mcp.js")));
const mutations = {
  echo: ['if (!Object.hasOwn(message, "ok")) return;', '// Echo-Sperre entfernt'],
  null: ['if (message.id === null) return;', 'if (message.id === null) { pending.clear(); return; }'],
  correlation: ['pending.get(message.id)', 'pending.values().next().value'],
  failure: ['if (message.ok === true)', 'if (true)'],
  isError: ['if (result.isError)', 'if (false)'],
  deadline: ['}, 65000);', '}, 60000);'],
  cleanup: ['pending.delete(id);', '// Map-Eintrag bleibt'],
  timer: ['clearTimeout(timer);', '// Timer bleibt'],
  name: ['if (typeof name !== "string" || !/^[A-Za-z0-9_.-]{1,128}$/.test(name))', 'if (false)'],
  args: ['if (!isObject(args))', 'if (false)'],
  wireArgs: ['if (!isObject(JSON.parse(body).args.arguments))', 'if (false)'],
  size: ['if (new TextEncoder().encode(body).length > 256 * 1024)', 'if (false)'],
  raw: ['new Error(bridgeError(message.fehler))', 'new Error(message.fehler)'],
  fetch: ['if (globalThis.chrome?.webview)', 'if (false)'],
  initialize: ['if (globalThis.chrome?.webview) return bridgeCall(name, args);', 'if (globalThis.chrome?.webview) { await rpc("initialize", {}); return bridgeCall(name, args); }'],
  string: ['webview.postMessage(body);', 'webview.postMessage(JSON.parse(body));'],
  responseString: ['if (typeof event.data !== "string") return;', 'if (typeof event.data !== "string") event = { data: JSON.stringify(event.data) };'],
  status: ['else finish(new Error(bridgeError("antwort_ungueltig")));', 'else finish(null, message.ergebnis);'],
  resultError: ['throw new Error(bridgeError("antwort_ungueltig"));', 'throw error;'],
  eval: ['return JSON.parse(text);', 'return eval(JSON.parse(text));'],
  repeat: ['webview.postMessage(body);', 'webview.postMessage(body); webview.postMessage(body);'],
  unknown: ['JSON.stringify({ id, befehl:', 'JSON.stringify({ extra: true, id, befehl:'],
  duplicate: ['webview.postMessage(body);', `webview.postMessage(body.replace('{"id":', '{"id":"doppelt","id":'));`],
};

function fixture({ browser = false, sse = false, sendError = false, httpStatus = 200 } = {}) {
  let source = sources[0].toString();
  const mutation = process.env.MCP_MUTATION;
  if (mutation) {
    const [before, after] = mutations[mutation] || [];
    assert.ok(before && source.includes(before), `Mutationsanker fehlt: ${mutation}`);
    source = source.replace(before, after);
    // Argumentprüfung vor und nach JSON-Serialisierung sind zwei Sperrwege.
    if (mutation === "args") source = source.replace(mutations.wireArgs[0], mutations.wireArgs[1]);
  }
  const sent = [], http = [], timers = new Map(), maps = [];
  let listener, now = 0, timerID = 0;
  const webview = {
    addEventListener(type, fn) {
      assert.equal(type, "message");
      assert.equal(listener, undefined, "Genau ein Listener je Adapter");
      listener = fn;
    },
    postMessage(body) {
      assert.equal(typeof body, "string", "Host erhält einen JSON-String");
      const request = JSON.parse(body);
      assert.equal(body, JSON.stringify(request), "Keine doppelten Schlüssel im Umschlag");
      assert.deepEqual(Object.keys(request).sort(), ["args", "befehl", "id"]);
      assert.match(request.id, /^[A-Za-z0-9_.-]{1,64}$/);
      assert.equal(request.befehl, "werkzeug", "Kein initialize im PC-Fenster");
      assert.deepEqual(Object.keys(request.args).sort(), ["arguments", "name"]);
      assert.match(request.args.name, /^[A-Za-z0-9_.-]{1,128}$/);
      assert.ok(request.args.arguments && typeof request.args.arguments === "object" && !Array.isArray(request.args.arguments));
      assert.ok(Buffer.byteLength(body) <= 256 * 1024);
      if (sendError) throw new Error("private Hostdaten");
      sent.push(request);
    }
  };
  const context = vm.createContext({
    chrome: browser ? undefined : { webview }, TextEncoder,
    Map: class extends Map { constructor(...args) { super(...args); maps.push(this); } },
    setTimeout(fn, delay) { const id = ++timerID; timers.set(id, { fn, at: now + delay, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    async fetch(url, options) {
      assert.ok(browser, "Kein fetch im Brückenweg");
      const request = JSON.parse(options.body);
      http.push({ url, options, request });
      if (httpStatus !== 200) return { ok: false, status: httpStatus };
      const message = { jsonrpc: "2.0", id: request.id, result: { content: [{ type: "text", text: '{"browser":true}' }] } };
      return { ok: true, headers: { get: () => sse ? "text/event-stream" : "application/json" },
        text: async () => sse ? `event: message\ndata: ${JSON.stringify(message)}\n\n` : JSON.stringify(message) };
    }
  });
  // Nur den ES-Modul-Export entfernen, der Adapter selbst bleibt unverändert.
  const callTool = vm.runInContext(source.replace("export async function callTool", "async function callTool") + "\ncallTool;", context);
  function call(name = "probe_read", args = {}) {
    const state = { status: "pending" };
    state.done = callTool(name, args).then(value => { state.status = "ok"; state.value = value; }, error => { state.status = "error"; state.error = error; });
    return state;
  }
  return { call, sent, http, timers, maps, executed: () => context.executed,
    emit(message) { listener?.({ data: JSON.stringify(message) }); },
    raw(data) { listener?.({ data }); },
    async flush() { for (let i = 0; i < 12; i++) await Promise.resolve(); },
    advance(ms) { now += ms; for (const [id, timer] of timers) if (timer.at <= now) { timers.delete(id); timer.fn(); } }
  };
}
const result = value => ({ content: [{ type: "text", text: JSON.stringify(value) }] });
const answer = (f, index, value) => f.emit({ id: f.sent[index].id, ok: true, ergebnis: result(value) });
function errorIs(state, message) { assert.equal(state.status, "error"); assert.equal(state.error.message, message); }
function clean(f) { assert.ok(f.maps.every(map => map.size === 0), "Offene Map geleert"); assert.equal(f.timers.size, 0, "Timer entfernt"); }

test("Beide mcp.js sind byte-identisch", () => assert.deepEqual(sources[0], sources[1]));
test("Textteile und structuredContent; nur werkzeug, String, kein fetch", async () => {
  const f = fixture();
  const a = f.call("probe_read", { text: "Grüße" });
  assert.equal(f.sent.length, 1);
  assert.deepEqual(f.sent[0].args, { name: "probe_read", arguments: { text: "Grüße" } });
  f.emit({ id: f.sent[0].id, ok: true, ergebnis: { content: [{ type: "text", text: '{"wert":' }, { type: "image" }, { type: "text", text: '3}' }] } });
  await a.done;
  assert.equal(JSON.stringify(a.value), '{"wert":3}');
  for (const value of [{ zahl: 4 }, false, null, 0]) {
    const b = f.call();
    f.emit({ id: f.sent.at(-1).id, ok: true, ergebnis: { structuredContent: value, content: [{ type: "text", text: "unlesbar" }] } });
    await b.done;
    assert.equal(JSON.stringify(b.value), JSON.stringify(value));
  }
  assert.equal(f.http.length, 0);
  clean(f);
});
test("ECHO ohne ok bleibt offen, danach echte Antwort", async () => {
  const f = fixture(), a = f.call();
  f.emit(f.sent[0]);
  await f.flush();
  assert.equal(a.status, "pending", "Echo darf den Aufruf nicht beenden");
  assert.equal(f.maps[0].size, 1);
  answer(f, 0, { echt: true });
  await a.done;
  assert.equal(a.status, "ok");
  clean(f);
});
test("JavaScript im Antworttext bleibt Daten und wird nicht ausgeführt", async () => {
  const f = fixture(), a = f.call();
  answer(f, 0, "globalThis.executed = true");
  await a.done;
  assert.equal(a.value, "globalThis.executed = true");
  assert.equal(f.executed(), undefined);
  clean(f);
});
test("Acht offene Aufrufe, Antworten in umgekehrter Reihenfolge, unbekannte und doppelte ID", async () => {
  const f = fixture(), calls = Array.from({ length: 8 }, () => f.call());
  assert.equal(new Set(f.sent.map(m => m.id)).size, 8);
  const ninth = f.call();
  f.emit({ id: f.sent[8].id, ok: false, fehler: "zu_viele" });
  await f.flush();
  errorIs(ninth, "Zu viele offene Anfragen. Kurz warten.");
  assert.equal(f.maps[0].size, 8, "Abweisung betrifft nur den neunten Aufruf");
  f.emit({ id: "fremd", ok: true, ergebnis: result("fremd") });
  for (let i = 7; i >= 0; i--) answer(f, i, i);
  f.emit({ id: f.sent[0].id, ok: false, fehler: "fehler" });
  await Promise.all(calls.map(a => a.done));
  assert.deepEqual(calls.map(a => a.value), [0, 1, 2, 3, 4, 5, 6, 7]);
  clean(f);
});
const errors = {
  abgelehnt: "Anfrage abgewiesen. Rechte prüfen.",
  antwort_ungueltig: "Ungültige Antwort des PC-Fensters.",
  args: "Ungültige Werkzeug-Eingabe.", befehl: "Befehl im PC-Fenster nicht verfügbar.",
  fehler: "Werkzeug-Anfrage fehlgeschlagen.",
  nicht_angemeldet: "Im PC-Fenster anmelden und erneut versuchen.",
  nicht_erreichbar: "Anlage nicht erreichbar. Verbindung prüfen.",
  umschlag: "Ungültige Nachricht an das PC-Fenster.",
  zu_gross: "Werkzeug-Anfrage ist zu groß.",
  zu_viele: "Zu viele offene Anfragen. Kurz warten.",
};
for (const [code, message] of Object.entries(errors)) test(`ok:false ${code}`, async () => {
  const f = fixture(), a = f.call();
  f.emit({ id: f.sent[0].id, ok: false, fehler: code, ergebnis: { structuredContent: { verboten: true } } });
  await a.done;
  errorIs(a, message);
  clean(f);
});
test("Unbekannte Fehler und Prototypnamen geben keine Rohdaten aus", async () => {
  for (const code of ["private Hostdaten", "constructor", "__proto__", { detail: "private Hostdaten" }]) {
    const f = fixture(), a = f.call();
    f.emit({ id: f.sent[0].id, ok: false, fehler: code });
    await a.done;
    errorIs(a, errors.fehler);
    clean(f);
  }
});
test("isError weist auch mit structuredContent ab", async () => {
  const f = fixture(), a = f.call();
  f.emit({ id: f.sent[0].id, ok: true, ergebnis: { isError: true, structuredContent: { verboten: true } } });
  await a.done;
  errorIs(a, "Werkzeug-Auftrag abgewiesen. Rechte und aktuellen Stand prüfen.");
  clean(f);
});
test("Eigene Frist je Aufruf über 60 s; späte Antwort ohne Wirkung", async () => {
  const f = fixture(), a = f.call();
  assert.equal(f.timers.size, 1);
  const delay = [...f.timers.values()][0].delay;
  assert.ok(delay > 60000 && delay <= 70000);
  f.advance(30000);
  const b = f.call();
  f.advance(30000);
  await f.flush();
  assert.equal(a.status, "pending");
  f.advance(delay - 60000);
  await a.done;
  errorIs(a, "Keine Antwort vom PC-Fenster. Stand prüfen.");
  assert.equal(f.sent.length, 2, "Kein Neuversand nach Frist");
  assert.equal(b.status, "pending");
  assert.equal(f.maps[0].size, 1);
  answer(f, 0, "zu spät");
  answer(f, 1, "aktuell");
  await b.done;
  assert.equal(b.value, "aktuell");
  clean(f);
});
test("id:null verwirft die Antwort und erhält alle zuordenbaren Aufrufe", async () => {
  const f = fixture(), a = f.call(), b = f.call();
  f.emit({ id: null, ok: false, fehler: "umschlag" });
  await f.flush();
  assert.equal(a.status, "pending");
  assert.equal(b.status, "pending");
  assert.equal(f.maps[0].size, 2);
  answer(f, 1, "b"); answer(f, 0, "a");
  await Promise.all([a.done, b.done]);
  assert.equal(a.value, "a"); assert.equal(b.value, "b");
  clean(f);
});
test("Unlesbare Nachrichten und Objekt statt JSON-String bleiben ohne Wirkung", async () => {
  const f = fixture(), a = f.call();
  for (const data of ["{", "null", "[]", JSON.stringify("text"), { id: f.sent[0].id, ok: true, ergebnis: result("verboten") }]) f.raw(data);
  await f.flush();
  assert.equal(a.status, "pending");
  answer(f, 0, "echt"); await a.done;
  assert.equal(a.value, "echt"); clean(f);
});
test("ok muss boolesch sein", async () => {
  const f = fixture(), a = f.call();
  f.emit({ id: f.sent[0].id, ok: "true", ergebnis: result("verboten") });
  await a.done; errorIs(a, errors.antwort_ungueltig); clean(f);
});
test("Ungültiges Werkzeug-Ergebnis zeigt feste Fehlertexte ohne Antwortdaten", async () => {
  for (const value of [null, {}, { content: [{ type: "text", text: "private Hostdaten" }] }, { content: "private Hostdaten" }]) {
    const f = fixture(), a = f.call();
    f.emit({ id: f.sent[0].id, ok: true, ergebnis: value });
    await a.done; errorIs(a, errors.antwort_ungueltig); clean(f);
  }
});
test("Ungültige Namen, Argumente, Serialisierung und UTF-8-Übergröße werden vor Versand abgewiesen", async () => {
  const cyclic = {}; cyclic.self = cyclic;
  for (const [name, args, message] of [
    ["", {}, errors.args], ["a/b", {}, errors.args], ["a".repeat(129), {}, errors.args],
    [17, {}, errors.args], [{ toString: () => "probe" }, {}, errors.args],
    ["probe", null, errors.args], ["probe", [], errors.args], ["probe", "text", errors.args],
    ["probe", { toJSON: () => [] }, errors.args], ["probe", cyclic, errors.args],
    ["probe", { text: "ä".repeat(132000) }, errors.zu_gross],
  ]) {
    const f = fixture(), a = f.call(name, args);
    await a.done; errorIs(a, message);
    assert.equal(f.sent.length, 0); clean(f);
  }
});
test("postMessage-Ausnahme räumt auf und zeigt keine Rohdaten", async () => {
  const f = fixture({ sendError: true }), a = f.call();
  await a.done; errorIs(a, errors.nicht_erreichbar); clean(f);
});
for (const sse of [false, true]) test(`Ohne webview unveränderter fetch-Weg (${sse ? "SSE" : "JSON"})`, async () => {
  const f = fixture({ browser: true, sse }), a = f.call("probe_read", { days: 2 }), b = f.call();
  await Promise.all([a.done, b.done]);
  assert.equal(JSON.stringify(a.value), '{"browser":true}');
  assert.equal(b.status, "ok");
  assert.deepEqual(f.http.map(m => m.request.method), ["initialize", "notifications/initialized", "tools/call", "tools/call"]);
  for (const { url, options } of f.http) {
    assert.equal(url, "/mcp"); assert.equal(options.method, "POST"); assert.equal(options.redirect, "error");
    assert.equal(options.headers["X-Jnpt-App"], "1");
    assert.equal(options.headers["MCP-Protocol-Version"], "2025-03-26");
  }
  assert.deepEqual(f.http[2].request.params, { name: "probe_read", arguments: { days: 2 } });
  assert.equal(f.sent.length, 0); clean(f);
});

test("401 nennt das Neuladen, andere Abweisungen bleiben beim Status", async () => {
  const ended = fixture({ browser: true, httpStatus: 401 }), a = ended.call();
  await a.done;
  errorIs(a, "Anmeldung beendet. Seite neu laden, um dich neu anzumelden.");
  const denied = fixture({ browser: true, httpStatus: 403 }), b = denied.call();
  await b.done;
  errorIs(b, "Anfrage abgewiesen (HTTP 403).");
});
