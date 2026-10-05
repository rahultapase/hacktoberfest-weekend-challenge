// Drive the UI in headless Chrome over CDP (no npm deps; Node 22 has WebSocket built in).
// Runs the main flow (write -> cards -> save green -> confirm tray -> dues -> reminder -> ask)
// and saves phone-sized screenshots.
//
// Usage: node tools/ui_flow.mjs <outDir> [baseUrl] [line]
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const OUT = process.argv[2] || "shots";
const BASE = process.argv[3] || "http://127.0.0.1:8000";
const LINE = process.argv[4] || "riya aur karan nahi aaye, neha absent, aman ne 1500 diye oct ke, baaki 500 next week";
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9333;
mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = mkdtempSync(join(tmpdir(), "tr-chrome-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, "--remote-allow-origins=*",
  `--user-data-dir=${profile}`, "--no-first-run", "--disable-extensions", "about:blank"], { stdio: "ignore" });

let ws, seq = 0;
const pending = new Map();
function send(method, params = {}) {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((res, rej) => pending.set(id, { res, rej }));
}
async function evaluate(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " " + (r.exceptionDetails.exception?.description || ""));
  return r.result.value;
}
async function waitFor(expr, ms = 120000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await evaluate(expr).catch(() => false)) return true;
    await sleep(250);
  }
  throw new Error("timeout waiting for " + expr);
}
// Full shots: grow the viewport to the page height so the fixed bottom nav lands at the
// bottom of the image, like a long phone screenshot.
async function shot(name, full = true, scrollSel = null) {
  await evaluate(`document.querySelector("#toast").hidden = true; ${scrollSel
    ? `(() => { const el = document.querySelector(${JSON.stringify(scrollSel)}); window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 120); })();`
    : "window.scrollTo(0, 0);"} true`);
  await sleep(450); // let entrance transitions settle
  if (full) {
    const hgt = await evaluate("Math.ceil(document.documentElement.scrollHeight)");
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: Math.min(Math.max(hgt, 844), 2600), deviceScaleFactor: 2, mobile: true });
    await sleep(300);
  }
  const r = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(OUT, name + ".png"), Buffer.from(r.data, "base64"));
  if (full) await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  console.log("saved", name);
}
const click = (sel) => evaluate(`(() => { const el = document.querySelector(${JSON.stringify(sel)}); if (!el) throw new Error("no ${sel}"); el.click(); return true; })()`);

try {
  let target;
  for (let i = 0; i < 40; i++) {
    try { target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(BASE + "/")}`, { method: "PUT" })).json(); break; }
    catch { await sleep(250); }
  }
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  ws.addEventListener("message", (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { const p = pending.get(d.id); pending.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); }
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await send("Page.navigate", { url: BASE + "/" });
  await waitFor(`document.querySelector("#status-chip")?.textContent.includes("offline OK")`, 30000);
  console.log("chip:", await evaluate(`document.querySelector("#status-chip").textContent`));

  // Likho
  await evaluate(`document.querySelector("#line").value = ${JSON.stringify(LINE)}; true`);
  await click("#read-btn");
  await waitFor(`document.querySelectorAll("#cards .card").length > 0`);
  console.log("cards:", JSON.stringify(await evaluate(`[...document.querySelectorAll("#cards .card")].map(c => c.className + " | " + c.querySelector(".card-top").textContent + " | " + [...c.querySelectorAll(".question span")].map(l => l.textContent).join(";"))`)));
  console.log("status:", await evaluate(`document.querySelector("#parse-status").textContent`));
  await shot("likho");

  await click("#save-green");
  await waitFor(`!document.querySelector("#toast").hidden`);
  console.log("toast:", await evaluate(`document.querySelector("#toast").textContent`));
  await waitFor(`document.querySelectorAll("#today-list li:not(.empty)").length > 0`);
  console.log("tray count:", await evaluate(`document.querySelector("#tray-count").textContent`));

  // Check karo: fix the Neha card by picking the first candidate
  await click("#tab-check");
  await waitFor(`document.querySelectorAll("#tray .card").length > 0`);
  await shot("check");
  const fixed = await evaluate(`(() => {
    const card = document.querySelector("#tray .card");
    const sel = card.querySelector(".editor select:nth-of-type(1)") || card.querySelector("select");
    const stu = card.querySelectorAll("select")[0];
    stu.selectedIndex = 1; stu.dispatchEvent(new Event("change"));
    const btn = card.querySelector(".card-actions .primary");
    return !btn.disabled;
  })()`);
  console.log("tray card fixable:", fixed);
  if (fixed) {
    await click("#tray .card .card-actions .primary");
    await sleep(800);
    console.log("tray after accept:", await evaluate(`document.querySelectorAll("#tray .card").length`));
  }

  // Baaki
  await click("#tab-baaki");
  await waitFor(`document.querySelectorAll("#dues-list li").length > 0`);
  console.log("dues total:", await evaluate(`document.querySelector("#dues-total").textContent`));
  await shot("baaki");
  await evaluate(`([...document.querySelectorAll("#dues-list .row-btn")].find(b => b.dataset.name === (process_name)) || document.querySelector("#dues-list .row-btn")).click(); true`.replace("process_name", JSON.stringify(process.env.TR_SHOT_STUDENT || "Riya")));
  await waitFor(`!document.querySelector("#student-detail").hidden`);
  await evaluate(`[...document.querySelectorAll("#student-detail button")].find(b => b.classList.contains("primary")).click(); true`);
  await waitFor(`document.querySelector("#rem-text")?.textContent.length > 0`);
  console.log("reminder:", await evaluate(`document.querySelector("#rem-text").textContent`));
  await shot("reminder", false, "#student-detail .ledger");

  // Bachche
  await click("#tab-bachche");
  await waitFor(`document.querySelectorAll("#students-list li").length > 0`);
  await shot("bachche");

  // Poocho
  await click("#tab-poocho");
  await evaluate(`document.querySelector("#ask-examples button").click(); true`);
  await waitFor(`document.querySelector("#answer .a-bubble:last-child p:not(.row-sub)")`);
  console.log("answer:", await evaluate(`document.querySelector("#answer").textContent`));
  await shot("poocho");

  // English toggle
  await click("#lang-en");
  await click("#tab-likho");
  await shot("likho-en", false);
  console.log("OK");
} catch (e) {
  console.error("FAIL:", e.message);
  process.exitCode = 1;
} finally {
  try { ws?.close(); } catch {}
  chrome.kill();
}
