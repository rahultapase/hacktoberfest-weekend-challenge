// Tuition Register UI. Vanilla JS, no build step. All user/model text goes through textContent.
"use strict";

// ---------- strings: [hinglish, english] ----------
const T = {
  tab_likho: ["Likho", "Write"],
  tab_check: ["Check karo", "Confirm"],
  tab_baaki: ["Baaki", "Dues"],
  tab_bachche: ["Bachche", "Students"],
  tab_poocho: ["Poocho", "Ask"],
  write_label: ["Register mein jaise likhti ho, waise likho", "Write it the way you write in your register"],
  date_label: ["Tarikh", "Date"],
  read_btn: ["Samjho", "Read it"],
  reading: ["Padh raha hai…", "Reading…"],
  save_green: ["Sab hara save karo", "Save all green"],
  today_saved: ["Is din save hua", "Saved for this day"],
  nothing_saved: ["Abhi kuch save nahi hua.", "Nothing saved yet."],
  tray_help: ["Yeh entries pakki nahi thi. Dekh ke sahi karo, phir save karo.", "These weren't certain. Check, fix if needed, then save."],
  tray_empty: ["Kuch check karna baaki nahi hai.", "Nothing to check."],
  month_label: ["Mahina", "Month"],
  add_student: ["Naya bachcha jodo", "Add a student"],
  s_name: ["Naam", "Name"],
  s_aliases: ["Doosre naam (comma se)", "Nicknames (comma separated)"],
  s_batch: ["Batch", "Batch"],
  s_fee: ["Mahine ki fees (₹)", "Monthly fee (₹)"],
  s_start: ["Kab se", "Start month"],
  save: ["Save karo", "Save"],
  import_csv: ["CSV se list laao", "Import from CSV"],
  csv_label: ["CSV file (name,aliases,batch,monthly_fee,start_month)", "CSV file (name,aliases,batch,monthly_fee,start_month)"],
  import_btn: ["Import karo", "Import"],
  ask_label: ["Kuch bhi poocho", "Ask a question"],
  ask_btn: ["Poocho", "Ask"],
  pin_label: ["PIN daalo", "Enter PIN"],
  pin_go: ["Kholo", "Open"],
  footer: ["Sab kuch isi computer par. Internet ki zaroorat nahi.", "Everything stays on this computer. No internet needed."],
  accept: ["Sahi hai, save karo", "Looks right, save"],
  discard: ["Hatao", "Discard"],
  edit: ["Badlo", "Edit"],
  undo: ["Undo", "Undo"],
  saved_n: ["save hua", "saved"],
  moved_n: ["check karne ke liye bheja", "sent to Confirm"],
  no_events: ["Is line mein koi entry nahi mili.", "No entries found in this line."],
  student: ["Bachcha", "Student"],
  pick: ["— chuno —", "— pick —"],
  type: ["Kya hua", "What"],
  status: ["Haazri", "Attendance"],
  amount: ["Rakam (₹)", "Amount (₹)"],
  for_month: ["Kis mahine ki", "For month"],
  on_date: ["Tarikh", "Date"],
  note: ["Note", "Note"],
  read_as: ["Padha:", "Read as:"],
  due: ["Fees", "Due"],
  paid: ["Mili", "Paid"],
  balance: ["Baaki", "Balance"],
  outstanding: ["Kul baaki", "Total owed"],
  advance: ["Advance", "Advance"],
  total_for: ["Is mahine kul baaki", "Total pending this month"],
  all_clear: ["Sab clear", "All clear"],
  promised: ["Vaada", "Promised"],
  overdue: ["tarikh nikal gayi", "overdue"],
  by: ["tak", "by"],
  reminder: ["Yaad dilao (message)", "Reminder message"],
  lang: ["Bhasha", "Language"],
  tone: ["Andaaz", "Tone"],
  preview: ["Message banao", "Make message"],
  copy: ["Copy karo", "Copy"],
  copied: ["Copy ho gaya", "Copied"],
  wa_link: ["WhatsApp mein kholo (internet chahiye)", "Open in WhatsApp (needs internet)"],
  close: ["Band karo", "Close"],
  month_col: ["Mahina", "Month"],
  absent_col: ["Nahi aaye", "Absent"],
  history: ["Entries", "Entries"],
  left: ["chhod diya", "left"],
  pick_student: ["Kaun sa bachcha?", "Which student?"],
  model_off: ["Model band hai: Ollama chalao", "Model off: start Ollama"],
  error: ["Gadbad hui", "Something went wrong"],
  examples: ["Jaise:", "Try:"],
};
const TYPE_LABEL = {
  attendance: ["Haazri", "Attendance"], payment: ["Fees mili", "Payment"], promise: ["Baad mein denge", "Promise"],
  fee_set: ["Nayi fees", "Fee change"], note: ["Note", "Note"], missing: ["Chhoot gaya?", "Missed?"],
};
const STATUS_LABEL = { present: ["aaye", "present"], absent: ["nahi aaye", "absent"], late: ["late aaye", "late"] };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const MODEL_NAMES = { "gemma4:e2b": "Gemma 4 E2B", "gemma3:1b": "Gemma 3 1B", "gemma3:4b": "Gemma 3 4B" };

const S = {
  lang: localStorage.getItem("tr_lang") || "hi",
  pin: sessionStorage.getItem("tr_pin") || "",
  today: new Date().toISOString().slice(0, 10),
  students: [],
  parsed: null, // {line, entry_date, model, cards: []}
  tray: JSON.parse(localStorage.getItem("tr_tray") || "[]"),
};

const $ = (sel) => document.querySelector(sel);
const L = (k) => (T[k] ? T[k][S.lang === "hi" ? 0 : 1] : k);
const L2 = (k) => (T[k] ? T[k][S.lang === "hi" ? 1 : 0] : "");
const pick = (pair) => pair[S.lang === "hi" ? 0 : 1];

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

const inr = (n) => "₹" + Number(n || 0).toLocaleString("en-IN");
const monthName = (ym, year = true) => {
  if (!ym) return "";
  const [y, m] = ym.split("-");
  return MONTHS[Number(m) - 1] + (year ? " " + y : "");
};
const byDate = (iso) => (S.lang === "hi" ? `${dayLabel(iso)} tak` : `by ${dayLabel(iso)}`);
const monthsLabel = (fm) => (fm || "").split(",").filter(Boolean).map((m) => monthName(m, false)).join(" + ");
const dayLabel = (iso) => {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${Number(d)} ${MONTHS[Number(m) - 1].slice(0, 3)}`;
};

// ---------- API ----------
async function api(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  if (S.pin) headers["X-TR-PIN"] = S.pin;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
  }
  const r = await fetch(path, { method: opts.method || "GET", headers, body: opts.body });
  if (r.status === 401) { showPin(); throw new Error("PIN required"); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join("; ") : `HTTP ${r.status}`);
  }
  return data;
}

// ---------- i18n + tabs ----------
function applyLang() {
  document.documentElement.lang = S.lang === "hi" ? "hi-Latn" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = L(el.dataset.i18n)));
  document.querySelectorAll("[data-i18n2]").forEach((el) => (el.textContent = L2(el.dataset.i18n2)));
  const btn = $("#lang-toggle");
  btn.textContent = S.lang === "hi" ? "English" : "Hinglish";
  btn.setAttribute("aria-pressed", S.lang === "en" ? "true" : "false");
  btn.setAttribute("aria-label", S.lang === "hi" ? "Switch to English" : "Switch to Hinglish");
}

function showTab(name, focus = false) {
  document.querySelectorAll('[role="tab"]').forEach((t) => {
    const on = t.dataset.tab === name;
    t.setAttribute("aria-selected", on ? "true" : "false");
    t.tabIndex = on ? 0 : -1;
    if (on && focus) t.focus();
  });
  document.querySelectorAll('[role="tabpanel"]').forEach((p) => (p.hidden = p.id !== "panel-" + name));
  if (name === "check") renderTray();
  if (name === "baaki") loadDues();
  if (name === "bachche") loadStudents();
}

function setupTabs() {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => showTab(t.dataset.tab));
    t.addEventListener("keydown", (e) => {
      let j = null;
      if (e.key === "ArrowRight") j = (i + 1) % tabs.length;
      if (e.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
      if (e.key === "Home") j = 0;
      if (e.key === "End") j = tabs.length - 1;
      if (j !== null) { e.preventDefault(); showTab(tabs[j].dataset.tab, true); }
    });
  });
}

// ---------- toast ----------
let toastTimer = null;
function toast(msg, undoFn) {
  const el = $("#toast");
  el.replaceChildren(h("span", { text: msg }));
  if (undoFn) el.append(h("button", { type: "button", text: L("undo"), onclick: async () => { el.hidden = true; await undoFn(); } }));
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 8000);
}

// ---------- health / PIN ----------
async function loadHealth() {
  const chip = $("#status-chip");
  try {
    const hl = await api("/api/health");
    S.today = hl.today || S.today;
    const name = MODEL_NAMES[hl.model] || hl.model;
    if (hl.ollama && hl.model_available) {
      chip.textContent = `${name} · local · offline OK`;
      chip.className = "chip";
    } else {
      chip.textContent = `${name} · ${L("model_off")}`;
      chip.className = "chip bad";
    }
    if (hl.pin_required && !S.pin) showPin();
  } catch (e) {
    chip.textContent = L("error");
    chip.className = "chip bad";
  }
}

function showPin() {
  $("#pin-box").hidden = false;
  $("#pin-input").focus();
}

// ---------- cards ----------
function cardSummary(c) {
  const name = c.student_name || (c.student_text ? `“${c.student_text}”` : "?");
  const parts = [name];
  if (c.type === "attendance") parts.push(c.status ? pick(STATUS_LABEL[c.status]) : "?", c.on_date ? dayLabel(c.on_date) : "");
  if (c.type === "payment") parts.push(c.amount ? inr(c.amount) : "₹?", monthsLabel(c.for_month));
  if (c.type === "promise") parts.push(c.amount ? inr(c.amount) : "₹?", c.on_date ? byDate(c.on_date) : "");
  if (c.type === "fee_set") parts.push(c.amount ? inr(c.amount) : "₹?", c.for_month ? `from ${monthName(c.for_month, false)}` : "");
  if (c.type === "note") parts.push(c.note || "");
  return parts.filter(Boolean).join(" · ");
}

function spansText(c) {
  const s = [c.student_text, c.amount_text, c.month_text, c.date_text].filter(Boolean).map((x) => `“${x}”`);
  return s.length ? `${L("read_as")} ${s.join(" ")}` : "";
}

function field(id, labelKey, input) {
  input.id = id;
  return h("div", {}, h("label", { for: id, text: L(labelKey) }), input);
}

let uid = 0;
function editor(c, onChange) {
  const id = "ed" + ++uid;
  const wrap = h("div", { class: "editor" });
  const typeSel = h("select", {}, ...["attendance", "payment", "promise", "fee_set", "note"].map((t) =>
    h("option", { value: t, selected: c.type === t, text: pick(TYPE_LABEL[t]) })));
  if (c.type === "missing") typeSel.prepend(h("option", { value: "", selected: true, text: L("pick") }));

  const cands = c.candidates || [];
  const stuSel = h("select", {}, h("option", { value: "", text: L("pick") }));
  const listed = new Set();
  cands.forEach((x) => { listed.add(x.id); stuSel.append(h("option", { value: x.id, selected: c.student_id === x.id, text: x.name })); });
  S.students.filter((s) => !listed.has(s.id)).forEach((s) =>
    stuSel.append(h("option", { value: s.id, selected: c.student_id === s.id, text: s.name })));

  const statusSel = h("select", {}, h("option", { value: "", text: L("pick") }),
    ...["absent", "present", "late"].map((v) => h("option", { value: v, selected: c.status === v, text: pick(STATUS_LABEL[v]) })));
  const amt = h("input", { type: "number", min: "1", max: "1000000", inputmode: "numeric", value: c.amount || "" });
  const multi = (c.for_month || "").includes(",");
  const month = multi ? h("input", { type: "text", value: c.for_month, pattern: "\\d{4}-\\d{2}(,\\d{4}-\\d{2})*" })
    : h("input", { type: "month", value: c.for_month || "" });
  const date = h("input", { type: "date", value: c.on_date || "" });
  const note = h("input", { type: "text", maxlength: "500", value: c.note || "" });

  const fType = field(id + "t", "type", typeSel);
  const fStu = field(id + "s", "student", stuSel);
  const fStatus = field(id + "st", "status", statusSel);
  const fAmt = field(id + "a", "amount", amt);
  const fMonth = field(id + "m", "for_month", month);
  const fDate = field(id + "d", "on_date", date);
  const fNote = field(id + "n", "note", note);
  wrap.append(fStu, fType, fStatus, fAmt, fMonth, fDate, fNote);

  function sync() {
    const t = typeSel.value;
    fStatus.hidden = t !== "attendance";
    fAmt.hidden = !["payment", "promise", "fee_set"].includes(t);
    fMonth.hidden = !["payment", "fee_set"].includes(t);
    fDate.hidden = !["attendance", "promise"].includes(t);
    fNote.hidden = t !== "note";
    const sid = stuSel.value ? Number(stuSel.value) : null;
    const s = S.students.find((x) => x.id === sid);
    onChange({
      type: t || c.type, student_id: sid, student_name: s ? s.name : null, status: statusSel.value || null,
      amount: amt.value ? Number(amt.value) : null, for_month: month.value || null, on_date: date.value || null,
      note: note.value || null,
    });
  }
  [typeSel, stuSel, statusSel, amt, month, date, note].forEach((el) => el.addEventListener("input", sync));
  [typeSel, stuSel, statusSel].forEach((el) => el.addEventListener("change", sync));
  sync();
  return wrap;
}

function validEdit(c) {
  if (!c.student_id || !c.type || c.type === "missing") return false;
  if (["payment", "promise", "fee_set"].includes(c.type) && !(c.amount > 0)) return false;
  if (c.type === "attendance" && !c.status) return false;
  return true;
}

function toPayload(c, confirmed) {
  return {
    type: c.type, student_id: c.student_id, status: c.type === "attendance" ? c.status : null,
    amount: ["payment", "promise", "fee_set"].includes(c.type) ? c.amount : null,
    for_month: ["payment", "fee_set"].includes(c.type) ? c.for_month : null,
    on_date: ["attendance", "promise"].includes(c.type) ? c.on_date : null,
    note: c.note, confirmed,
  };
}

async function saveEvents(ctx, cards, confirmed) {
  const r = await api("/api/entries", {
    method: "POST",
    json: { raw_line: ctx.line, entry_date: ctx.entry_date, model: ctx.model, events: cards.map((c) => toPayload(c, confirmed)) },
  });
  return r.ids;
}

async function undo(ids) {
  for (const id of ids) await api(`/api/entries/${id}`, { method: "DELETE" }).catch(() => {});
  loadToday();
}

function renderCard(c, ctx, { onSaved, onDiscard, showSave = false }) {
  const isOk = c.verdict === "ok";
  let edited = Object.assign({}, c);
  const body = h("div");
  const summary = h("span", { class: "summary", text: cardSummary(c) });
  const art = h("article", { class: `card ${isOk ? "ok" : "confirm"}`, "aria-label": `${pick(TYPE_LABEL[c.type])}: ${cardSummary(c)}` },
    h("div", { class: "head" },
      h("span", { class: "icon", "aria-hidden": "true", text: isOk ? "✓" : "⚠" }),
      h("span", { class: "kind", text: pick(TYPE_LABEL[c.type] || ["?", "?"]) }),
      summary),
    spansText(c) ? h("div", { class: "spans", text: spansText(c) }) : null,
    c.reasons && c.reasons.length ? h("ul", { class: "reasons" }, c.reasons.map((r) => h("li", { text: S.lang === "hi" ? r.hi : r.en }))) : null,
    body);

  const acceptBtn = h("button", { type: "button", class: "primary", text: L("accept") });
  const discardBtn = h("button", { type: "button", class: "ghost", text: L("discard"), onclick: () => onDiscard() });

  function openEditor() {
    body.replaceChildren(editor(c, (patch) => {
      edited = Object.assign({}, c, patch);
      summary.textContent = cardSummary(edited);
      acceptBtn.disabled = !validEdit(edited);
    }));
  }
  acceptBtn.addEventListener("click", async () => {
    if (!validEdit(edited)) return;
    acceptBtn.disabled = true;
    try {
      const ids = await saveEvents(ctx, [edited], !isOk || edited !== c);
      toast(`1 ${L("saved_n")}`, () => undo(ids));
      onSaved();
    } catch (e) { toast(`${L("error")}: ${e.message}`); acceptBtn.disabled = false; }
  });

  if (!isOk) {
    openEditor();
    art.append(h("div", { class: "actions" }, acceptBtn, discardBtn));
  } else {
    const editBtn = h("button", { type: "button", class: "ghost", text: L("edit"), onclick: () => {
      openEditor(); c.verdict = "confirm"; art.className = "card confirm"; editBtn.remove(); acceptBtn.hidden = false; acceptBtn.focus();
    } });
    acceptBtn.hidden = !showSave;
    art.append(h("div", { class: "actions" }, acceptBtn, editBtn, discardBtn));
  }
  return art;
}

function renderParsed() {
  const box = $("#cards");
  const p = S.parsed;
  box.replaceChildren();
  $("#cards-actions").hidden = true;
  if (!p) return;
  if (!p.cards.length) { box.append(h("p", { class: "muted", text: L("no_events") })); return; }
  p.cards.forEach((c, i) => box.append(renderCard(c, p, {
    onSaved: () => { p.cards.splice(i, 1); renderParsed(); loadToday(); },
    onDiscard: () => { p.cards.splice(i, 1); renderParsed(); },
  })));
  const greens = p.cards.filter((c) => c.verdict === "ok").length;
  $("#cards-actions").hidden = false;
  const btn = $("#save-green");
  btn.textContent = `${L("save_green")} (${greens})` + (p.cards.length > greens ? ` · ⚠ ${p.cards.length - greens} → ${L("tab_check")}` : "");
}

async function saveAllGreen() {
  const p = S.parsed;
  if (!p) return;
  const greens = p.cards.filter((c) => c.verdict === "ok");
  const ambers = p.cards.filter((c) => c.verdict !== "ok");
  let ids = [];
  try {
    if (greens.length) ids = await saveEvents(p, greens, false);
  } catch (e) { toast(`${L("error")}: ${e.message}`); return; }
  ambers.forEach((c) => S.tray.push({ key: Date.now() + Math.random(), card: c, line: p.line, entry_date: p.entry_date, model: p.model }));
  saveTray();
  S.parsed = null;
  renderParsed();
  $("#line").value = "";
  const msg = [`${greens.length} ${L("saved_n")}`];
  if (ambers.length) msg.push(`${ambers.length} ${L("moved_n")}`);
  toast(msg.join(" · "), ids.length ? () => undo(ids) : null);
  loadToday();
  $("#line").focus();
}

// ---------- tray ----------
function saveTray() {
  localStorage.setItem("tr_tray", JSON.stringify(S.tray));
  const n = S.tray.length;
  const el = $("#tray-count");
  el.hidden = !n;
  el.textContent = n;
  el.setAttribute("aria-label", `${n} to check`);
}

function renderTray() {
  const box = $("#tray");
  box.replaceChildren();
  if (!S.tray.length) { box.append(h("p", { text: L("tray_empty") })); return; }
  S.tray.forEach((item) => {
    const ctx = { line: item.line, entry_date: item.entry_date, model: item.model };
    const remove = () => { S.tray = S.tray.filter((x) => x.key !== item.key); saveTray(); renderTray(); };
    box.append(h("p", { class: "muted", text: `${dayLabel(item.entry_date)}: “${item.line}”` }));
    box.append(renderCard(item.card, ctx, { onSaved: () => { remove(); loadToday(); }, onDiscard: remove }));
  });
}

// ---------- Likho ----------
async function onRead(e) {
  e.preventDefault();
  const line = $("#line").value.trim();
  if (!line) return;
  const btn = $("#read-btn");
  btn.disabled = true;
  $("#parse-status").textContent = L("reading");
  try {
    const r = await api("/api/parse", { method: "POST", json: { line, entry_date: $("#entry-date").value || null } });
    S.parsed = { line: r.line, entry_date: r.entry_date, model: r.model, cards: r.events };
    const ok = r.events.filter((c) => c.verdict === "ok").length;
    $("#parse-status").textContent = `✓ ${ok} · ⚠ ${r.events.length - ok} · ${r.seconds}s`;
    renderParsed();
  } catch (err) {
    $("#parse-status").textContent = `${L("error")}: ${err.message}`;
  } finally { btn.disabled = false; }
}

async function loadToday() {
  const d = $("#entry-date").value;
  const ul = $("#today-list");
  try {
    const rows = await api(`/api/entries?entry_date=${encodeURIComponent(d)}`);
    ul.replaceChildren();
    if (!rows.length) { ul.append(h("li", { class: "muted", text: L("nothing_saved") })); return; }
    rows.forEach((e) => {
      const c = Object.assign({}, e, { student_name: e.student_name });
      ul.append(h("li", { class: "student-item" },
        h("span", {}, h("strong", { text: pick(TYPE_LABEL[e.type]) + ": " }), cardSummary(c),
          e.verdict === "confirmed_by_user" ? h("span", { class: "badge", text: "✔ you" }) : null),
        h("button", { type: "button", class: "link", text: L("discard"), "aria-label": `${L("discard")} ${cardSummary(c)}`,
          onclick: async () => { await api(`/api/entries/${e.id}`, { method: "DELETE" }); loadToday(); } })));
    });
  } catch (err) { /* PIN or server down: shown elsewhere */ }
}

// ---------- Baaki ----------
async function loadDues() {
  const month = $("#dues-month").value || S.today.slice(0, 7);
  const ul = $("#dues-list");
  try {
    const d = await api(`/api/dues?month=${encodeURIComponent(month)}`);
    $("#dues-total").textContent = `${L("total_for")} (${monthName(month)}): ${inr(d.total_balance)} · ${L("paid")} ${inr(d.total_paid)} / ${inr(d.total_due)}`;
    ul.replaceChildren();
    d.rows.forEach((r) => {
      const badge = r.promise ? h("span", { class: `badge ${r.promise.status === "overdue" ? "overdue" : ""}`,
        text: `${r.promise.status === "overdue" ? "⏰ " : "🤝 "}${L("promised")} ${inr(r.promise.amount)}${r.promise.on_date ? " " + byDate(r.promise.on_date) : ""}${r.promise.status === "overdue" ? " (" + L("overdue") + ")" : ""}` }) : null;
      ul.append(h("li", { class: "dues-item" },
        h("div", {},
          h("button", { type: "button", class: "name", text: r.name, onclick: () => openStudent(r.student_id, month) }),
          h("div", { class: "muted", text: `${r.batch || ""} · ${L("due")} ${inr(r.due)} · ${L("paid")} ${inr(r.paid)}` }),
          badge),
        h("span", { class: `amt ${r.balance > 0 ? "due" : "clear"}`, text: r.balance > 0 ? `${inr(r.balance)} ${L("balance")}` : `✓ ${L("all_clear")}` })));
    });
  } catch (err) { $("#dues-total").textContent = `${L("error")}: ${err.message}`; }
}

async function openStudent(sid, month) {
  const box = $("#student-detail");
  const d = await api(`/api/students/${sid}/ledger`);
  const s = d.student;
  const rows = d.months.slice().reverse().map((m) => h("tr", {},
    h("td", { text: monthName(m.month) }), h("td", { class: "num", text: inr(m.due) }),
    h("td", { class: "num", text: inr(m.paid) }), h("td", { class: "num", text: m.balance > 0 ? inr(m.balance) : "✓" }),
    h("td", { class: "num", text: m.attendance.absent })));
  const langSel = h("select", { id: "rem-lang" }, h("option", { value: "hinglish", text: "Hinglish" }),
    h("option", { value: "hi", text: "हिंदी" }), h("option", { value: "en", text: "English" }));
  const toneSel = h("select", { id: "rem-tone" }, h("option", { value: "gentle", text: S.lang === "hi" ? "Pyaar se (gentle)" : "Gentle" }),
    h("option", { value: "normal", text: S.lang === "hi" ? "Seedha (normal)" : "Normal" }),
    h("option", { value: "firm-but-polite", text: S.lang === "hi" ? "Thoda sakht (firm but polite)" : "Firm but polite" }));
  const out = h("textarea", { id: "rem-text", class: "reminder-text", readonly: true, "aria-label": L("reminder") });
  const status = h("p", { class: "muted", role: "status", "aria-live": "polite" });
  const wa = h("a", { href: "#", hidden: true, target: "_blank", rel: "noopener noreferrer", text: L("wa_link") });
  const remMonth = (d.months.find((m) => m.month === month && m.balance > 0) || d.months.slice().reverse().find((m) => m.balance > 0) || {}).month;

  const previewBtn = h("button", { type: "button", class: "primary", text: L("preview"), disabled: !remMonth });
  previewBtn.addEventListener("click", async () => {
    previewBtn.disabled = true;
    status.textContent = L("reading");
    try {
      const r = await api("/api/reminders", { method: "POST", json: { student_id: sid, month: remMonth, lang: langSel.value, tone: toneSel.value } });
      out.value = r.text;
      status.textContent = r.source === "fallback" ? "template: built-in" : `template: ${r.source}`;
      wa.href = "https://wa.me/?text=" + encodeURIComponent(r.text);
      wa.hidden = false;
    } catch (e) { status.textContent = `${L("error")}: ${e.message}`; }
    previewBtn.disabled = false;
  });
  const copyBtn = h("button", { type: "button", class: "ghost", text: L("copy"), onclick: async () => {
    if (!out.value) return;
    try { await navigator.clipboard.writeText(out.value); } catch (e) { out.select(); document.execCommand("copy"); }
    status.textContent = L("copied");
  } });

  box.replaceChildren(h("div", { class: "detail" },
    h("h2", { text: `${s.name}${s.batch ? " · " + s.batch : ""}` }),
    h("p", {}, `${L("outstanding")}: `, h("strong", { text: inr(d.outstanding) }), d.advance ? ` · ${L("advance")}: ${inr(d.advance)}` : ""),
    h("table", {}, h("thead", {}, h("tr", {}, h("th", { text: L("month_col") }), h("th", { class: "num", text: L("due") }),
      h("th", { class: "num", text: L("paid") }), h("th", { class: "num", text: L("balance") }), h("th", { class: "num", text: L("absent_col") }))),
      h("tbody", {}, rows)),
    h("h3", { text: `${L("reminder")}${remMonth ? " · " + monthName(remMonth) : ""}` }),
    h("div", { class: "row" },
      h("div", {}, h("label", { for: "rem-lang", text: L("lang") }), langSel),
      h("div", {}, h("label", { for: "rem-tone", text: L("tone") }), toneSel)),
    h("div", { class: "row" }, previewBtn, copyBtn),
    out, status, wa,
    h("p", {}, h("button", { type: "button", class: "link", text: L("close"), onclick: () => { box.hidden = true; } }))));
  box.hidden = false;
  box.querySelector("h2").tabIndex = -1;
  box.querySelector("h2").focus();
}

// ---------- Bachche ----------
async function loadStudents() {
  S.students = await api("/api/students");
  const ul = $("#students-list");
  if (!ul) return;
  ul.replaceChildren();
  S.students.forEach((s) => {
    ul.append(h("li", { class: "student-item" },
      h("div", {}, h("strong", { text: s.name }), s.aliases.length ? ` (${s.aliases.join(", ")})` : "",
        h("div", { class: "muted", text: `${s.batch || ""} · ${inr(s.monthly_fee)}/mo · from ${monthName(s.start_month)}${s.end_month ? " · " + L("left") + " " + monthName(s.end_month) : ""}` })),
      h("span", { class: `amt ${s.outstanding > 0 ? "due" : "clear"}`, text: s.outstanding > 0 ? inr(s.outstanding) : "✓" })));
  });
}

async function onAddStudent(e) {
  e.preventDefault();
  const body = {
    name: $("#s-name").value.trim(),
    aliases: $("#s-aliases").value.split(",").map((x) => x.trim()).filter(Boolean),
    batch: $("#s-batch").value.trim() || null,
    monthly_fee: Number($("#s-fee").value),
    start_month: $("#s-start").value,
  };
  try {
    const s = await api("/api/students", { method: "POST", json: body });
    $("#students-msg").textContent = `✓ ${s.name}`;
    e.target.reset();
    loadStudents();
  } catch (err) { $("#students-msg").textContent = `${L("error")}: ${err.message}`; }
}

async function onImport(e) {
  e.preventDefault();
  const f = $("#csv-file").files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  try {
    const r = await api("/api/students/import", { method: "POST", body: fd });
    $("#students-msg").textContent = `✓ ${r.count}`;
    loadStudents();
  } catch (err) { $("#students-msg").textContent = `${L("error")}: ${err.message}`; }
}

// ---------- Poocho ----------
const EXAMPLES = ["kis kis ka october baaki hai?", "aman ka kitna baaki hai?", "riya kitne din nahi aayi is mahine?", "is mahine kisne fees de di?"];

async function ask(question, studentId = null) {
  const ans = $("#answer");
  ans.textContent = L("reading");
  try {
    const r = await api("/api/ask", { method: "POST", json: { question, student_id: studentId } });
    ans.replaceChildren(h("p", { text: S.lang === "hi" ? r.hi : r.en }));
    if (r.candidates && r.candidates.length) {
      ans.append(h("div", { class: "chips", role: "group", "aria-label": L("pick_student") },
        r.candidates.map((c) => h("button", { type: "button", text: c.name, onclick: () => ask(question, c.id) }))));
    }
  } catch (err) { ans.textContent = `${L("error")}: ${err.message}`; }
}

// ---------- init ----------
function init() {
  applyLang();
  setupTabs();
  saveTray();
  $("#lang-toggle").addEventListener("click", () => {
    S.lang = S.lang === "hi" ? "en" : "hi";
    localStorage.setItem("tr_lang", S.lang);
    applyLang();
    renderParsed();
    const sel = document.querySelector('[role="tab"][aria-selected="true"]');
    if (sel) showTab(sel.dataset.tab);
    loadToday();
  });
  $("#pin-form").addEventListener("submit", (e) => {
    e.preventDefault();
    S.pin = $("#pin-input").value;
    sessionStorage.setItem("tr_pin", S.pin);
    $("#pin-box").hidden = true;
    start();
  });
  $("#write-form").addEventListener("submit", onRead);
  $("#line").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) $("#write-form").requestSubmit();
  });
  $("#save-green").addEventListener("click", saveAllGreen);
  $("#entry-date").addEventListener("change", loadToday);
  $("#dues-month").addEventListener("change", loadDues);
  $("#student-form").addEventListener("submit", onAddStudent);
  $("#import-form").addEventListener("submit", onImport);
  $("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); const q = $("#question").value.trim(); if (q) ask(q); });
  const ex = $("#ask-examples");
  EXAMPLES.forEach((q) => ex.append(h("button", { type: "button", text: q, onclick: () => { $("#question").value = q; ask(q); } })));
  start();
}

async function start() {
  await loadHealth();
  $("#entry-date").value = S.today;
  $("#dues-month").value = S.today.slice(0, 7);
  try { await loadStudents(); } catch (e) { /* PIN */ }
  loadToday();
}

document.addEventListener("DOMContentLoaded", init);
