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
  date_label: ["Kis din ka", "For the day"],
  read_btn: ["Samjho", "Read it"],
  reading: ["Padh raha hai…", "Reading…"],
  heard: ["Aapne likha", "You wrote"],
  checked_n: ["pakka", "checked"],
  look_n: ["dekhna hai", "to look at"],
  save_n_green: ["pakki entries save karo", "checked entries: save"],
  save_note: ["dekhne wali entries “Check karo” mein chali jayengi", "to look at will go to Confirm"],
  today_saved: ["Is din save hua", "Saved for this day"],
  nothing_saved: ["Abhi kuch save nahi hua. Upar ek line likho.", "Nothing saved yet. Write a line above."],
  tray_help: ["Yeh entries pakki nahi thi. Ek baar dekh lo, phir save karo.", "These weren't certain. Take a look, fix if needed, then save."],
  tray_empty: ["Sab saaf. Kuch check karna baaki nahi hai.", "All clear. Nothing to check."],
  from_line: ["Line", "Line"],
  month_label: ["Mahina", "Month"],
  add_student: ["Naya bachcha jodo", "Add a student"],
  s_name: ["Naam", "Name"],
  s_aliases: ["Doosre naam (comma se)", "Nicknames (comma separated)"],
  s_batch: ["Batch", "Batch"],
  s_fee: ["Mahine ki fees (₹)", "Monthly fee (₹)"],
  s_start: ["Kab se", "Start month"],
  save: ["Bachcha save karo", "Save student"],
  import_csv: ["CSV se list laao", "Import from CSV"],
  csv_label: ["CSV file (name,aliases,batch,monthly_fee,start_month)", "CSV file (name,aliases,batch,monthly_fee,start_month)"],
  import_btn: ["List import karo", "Import list"],
  ask_label: ["Kuch bhi poocho", "Ask a question"],
  ask_btn: ["Poocho", "Ask"],
  ask_hint: ["Yeh 4 tarah ke sawaal samajhta hai. Jawab register se, hisaab code se.", "It understands 4 kinds of questions. Answers come from the register, sums from code."],
  pin_label: ["PIN daalo", "Enter PIN"],
  pin_go: ["Kholo", "Open"],
  footer: ["Sab kuch isi computer par. Internet ki zaroorat nahi.", "Everything stays on this computer. No internet needed."],
  accept: ["Sahi hai, save karo", "Looks right, save"],
  discard: ["Hatao", "Remove"],
  edit: ["Badlo", "Edit"],
  undo: ["Undo", "Undo"],
  saved_n: ["save hui", "saved"],
  moved_n: ["check karne ke liye bheji", "sent to Confirm"],
  no_events: ["Is line mein koi entry nahi mili. Kuch save nahi hoga.", "No entries in this line. Nothing will be saved."],
  student: ["Bachcha", "Student"],
  pick: ["— chuno —", "— pick —"],
  type: ["Kya hua", "What"],
  status: ["Haazri", "Attendance"],
  amount: ["Rakam (₹)", "Amount (₹)"],
  for_month: ["Kis mahine ki", "For month"],
  on_date: ["Tarikh", "Date"],
  note: ["Note", "Note"],
  due: ["Fees", "Due"],
  paid: ["Mili", "Paid"],
  balance: ["Baaki", "Owes"],
  outstanding: ["Kul baaki", "Total owed"],
  advance: ["Advance", "Advance"],
  pending_in: ["baaki", "pending"],
  of_students: ["bachchon ki fees baaki", "students still owe"],
  collected: ["mil gaye", "collected"],
  of_total: ["kul", "of"],
  owes_group: ["Fees baaki", "Still owe"],
  clear_group: ["Fees aa gayi", "Paid up"],
  all_clear: ["Clear", "Paid"],
  everyone_paid: ["Is mahine sabki fees aa gayi.", "Everyone has paid this month."],
  promised: ["Vaada", "Promised"],
  overdue: ["tarikh nikal gayi", "overdue"],
  reminder: ["Yaad dilane ka message", "Reminder message"],
  lang: ["Bhasha", "Language"],
  tone: ["Andaaz", "Tone"],
  preview: ["Message banao", "Write message"],
  copy: ["Copy karo", "Copy message"],
  copied: ["Copy ho gaya. WhatsApp mein paste kar do.", "Copied. Paste it into WhatsApp."],
  wa_link: ["WhatsApp mein kholo", "Open in WhatsApp"],
  wa_note: ["(internet chahiye)", "(needs internet)"],
  src_model: ["Shabd Gemma ne likhe, rakam code ne bhari.", "Wording by Gemma, amount filled in by code."],
  src_cached: ["Pehle bana message, rakam code ne bhari.", "Saved wording, amount filled in by code."],
  src_fallback: ["Taiyaar message, rakam code ne bhari.", "Built-in wording, amount filled in by code."],
  month_col: ["Mahina", "Month"],
  absent_col: ["Nahi aaye", "Absent"],
  left: ["chhod diya", "left"],
  per_month: ["/mahina", "/month"],
  since: ["se", "since"],
  pick_student: ["Kaun sa bachcha?", "Which student?"],
  model_off: ["Model band hai: Ollama chalao", "Model off: start Ollama"],
  local_ok: ["isi computer par · offline OK", "on this computer · offline OK"],
  error: ["Gadbad hui", "Something went wrong"],
  try_line: ["Jaise:", "Try:"],
};
const TYPE_LABEL = {
  attendance: ["Haazri", "Attendance"], payment: ["Fees mili", "Payment"], promise: ["Baad mein denge", "Promise"],
  fee_set: ["Nayi fees", "Fee change"], note: ["Note", "Note"], missing: ["Chhoot gaya?", "Missed?"],
};
const TYPE_IC = { attendance: "H", payment: "₹", promise: "⏳", fee_set: "₹", note: "✎", missing: "?" };
const STATUS_LABEL = { present: ["aaye", "present"], absent: ["nahi aaye", "absent"], late: ["late aaye", "late"] };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const MODEL_NAMES = { "gemma4:e2b": "Gemma 4 E2B", "gemma3:1b": "Gemma 3 1B", "gemma3:4b": "Gemma 3 4B" };

const S = {
  lang: localStorage.getItem("tr_lang") || "hi",
  pin: sessionStorage.getItem("tr_pin") || "",
  today: new Date().toISOString().slice(0, 10),
  students: [],
  parsed: null, // {line, entry_date, model, seconds, cards: []}
  tray: JSON.parse(localStorage.getItem("tr_tray") || "[]"),
};

const $ = (sel) => document.querySelector(sel);
const L = (k) => (T[k] ? T[k][S.lang === "hi" ? 0 : 1] : k);
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
const dayLabel = (iso) => {
  if (!iso) return "";
  const [, m, d] = iso.split("-");
  return `${Number(d)} ${MONTHS[Number(m) - 1].slice(0, 3)}`;
};
const byDate = (iso) => (S.lang === "hi" ? `${dayLabel(iso)} tak` : `by ${dayLabel(iso)}`);
const monthsLabel = (fm) => (fm || "").split(",").filter(Boolean).map((m) => monthName(m, false)).join(" + ");
const batchClass = (b) => (b ? "b" + String(b).replace(/\D/g, "") : "");
const initials = (name) => name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();

function svgIcon(path) {
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  s.setAttribute("aria-hidden", "true");
  const p = document.createElementNS(ns, "path");
  p.setAttribute("d", path);
  p.setAttribute("fill", "none");
  p.setAttribute("stroke", "currentColor");
  p.setAttribute("stroke-width", "2");
  p.setAttribute("stroke-linecap", "round");
  p.setAttribute("stroke-linejoin", "round");
  s.append(p);
  return s;
}
const CHEVRON = "M9 6l6 6-6 6";

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
  $("#lang-hi").setAttribute("aria-pressed", S.lang === "hi" ? "true" : "false");
  $("#lang-en").setAttribute("aria-pressed", S.lang === "en" ? "true" : "false");
}

function setLang(lang) {
  if (S.lang === lang) return;
  S.lang = lang;
  localStorage.setItem("tr_lang", lang);
  applyLang();
  renderParsed();
  renderAskHint();
  const sel = document.querySelector('[role="tab"][aria-selected="true"]');
  if (sel) showTab(sel.dataset.tab);
  loadToday();
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
  window.scrollTo(0, 0);
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
  const text = chip.querySelector(".status-text");
  try {
    const hl = await api("/api/health");
    S.today = hl.today || S.today;
    S.model = hl.model;
    const name = MODEL_NAMES[hl.model] || hl.model;
    if (hl.ollama && hl.model_available) {
      text.textContent = `${name} · offline OK`;
      chip.title = `${name} running locally in Ollama`;
      chip.className = "status";
    } else {
      text.textContent = `${name} · ${L("model_off")}`;
      chip.className = "status bad";
    }
    if (hl.pin_required && !S.pin) showPin();
  } catch (e) {
    text.textContent = L("error");
    chip.className = "status bad";
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
  if (c.type === "fee_set") parts.push(c.amount ? inr(c.amount) : "₹?", c.for_month ? monthName(c.for_month, false) : "");
  if (c.type === "note") parts.push(c.note || "");
  return parts.filter(Boolean).join(" · ");
}

// The value shown on the right of a card: what code worked out from her words.
function cardValue(c) {
  if (c.type === "attendance") return { cls: c.status === "absent" ? "absent" : "", big: c.status ? pick(STATUS_LABEL[c.status]) : "?", small: dayLabel(c.on_date) };
  if (c.type === "payment") return { cls: "money", big: c.amount ? inr(c.amount) : "₹?", small: monthsLabel(c.for_month) || (S.lang === "hi" ? "purana baaki pehle" : "oldest due first") };
  if (c.type === "promise") return { cls: "money", big: c.amount ? inr(c.amount) : "₹?", small: c.on_date ? byDate(c.on_date) : (S.lang === "hi" ? "baad mein" : "later") };
  if (c.type === "fee_set") return { cls: "money", big: c.amount ? inr(c.amount) + L("per_month") : "₹?", small: c.for_month ? `${S.lang === "hi" ? "" : "from "}${monthName(c.for_month, false)}${S.lang === "hi" ? " se" : ""}` : "" };
  if (c.type === "note") return { cls: "", big: "", small: c.note || "" };
  return { cls: "", big: "", small: "" };
}

function field(id, labelKey, input, cls = "") {
  input.id = id;
  return h("div", { class: cls }, h("label", { for: id, text: L(labelKey) }), input);
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

  const fStu = field(id + "s", "student", stuSel);
  const fType = field(id + "t", "type", typeSel);
  const fStatus = field(id + "st", "status", statusSel);
  const fAmt = field(id + "a", "amount", amt);
  const fMonth = field(id + "m", "for_month", month);
  const fDate = field(id + "d", "on_date", date);
  const fNote = field(id + "n", "note", note, "span2");
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

function renderCard(c, ctx, { onSaved, onDiscard }, index = 0) {
  const isOk = c.verdict === "ok";
  let edited = Object.assign({}, c);

  const nameEl = h("div", { class: "card-name" });
  const valBig = h("strong");
  const valSmall = h("span");
  const valBox = h("div", { class: "card-val" }, valBig, valSmall);
  function paint(x) {
    nameEl.replaceChildren(x.student_name ? x.student_name : h("span", { class: "guess", text: `“${x.student_text || "?"}”` }));
    const v = cardValue(x);
    valBox.className = `card-val ${v.cls}`;
    valBig.textContent = v.big;
    valSmall.textContent = v.small;
  }
  paint(c);

  const body = h("div");
  const art = h("article", { class: `card ${isOk ? "ok" : "confirm"}`, "aria-label": `${pick(TYPE_LABEL[c.type])}: ${cardSummary(c)}` },
    h("div", { class: "card-top" },
      h("span", { class: "badge-ic", "aria-hidden": "true", text: isOk ? "✓" : "!" }),
      h("div", { class: "card-main" },
        h("div", { class: "card-kind", text: pick(TYPE_LABEL[c.type] || ["?", "?"]) }),
        nameEl),
      valBox),
    c.reasons && c.reasons.length ? h("div", { class: "question" },
      c.reasons.map((r) => h("span", { text: S.lang === "hi" ? r.hi : r.en }))) : null,
    body);
  art.style.animationDelay = Math.min(index, 6) * 40 + "ms";

  const acceptBtn = h("button", { type: "button", class: "btn primary", text: L("accept") });
  const discardBtn = h("button", { type: "button", class: "btn quiet", text: L("discard"), onclick: () => onDiscard() });

  function openEditor() {
    body.replaceChildren(editor(c, (patch) => {
      edited = Object.assign({}, c, patch);
      paint(edited);
      acceptBtn.disabled = !validEdit(edited);
    }));
  }
  acceptBtn.addEventListener("click", async () => {
    if (!validEdit(edited)) return;
    acceptBtn.disabled = true;
    acceptBtn.setAttribute("aria-busy", "true");
    try {
      const ids = await saveEvents(ctx, [edited], true);
      toast(`1 ${L("saved_n")}`, () => undo(ids));
      onSaved();
    } catch (e) { toast(`${L("error")}: ${e.message}`); acceptBtn.disabled = false; acceptBtn.removeAttribute("aria-busy"); }
  });

  if (!isOk) {
    openEditor();
    art.append(h("div", { class: "card-actions" }, acceptBtn, discardBtn));
  } else {
    const editBtn = h("button", { type: "button", class: "btn text", text: L("edit"), onclick: () => {
      openEditor(); c.verdict = "confirm"; art.className = "card confirm";
      art.querySelector(".badge-ic").textContent = "!";
      editBtn.remove(); actions.prepend(acceptBtn); acceptBtn.focus();
    } });
    const delBtn = h("button", { type: "button", class: "btn text", text: L("discard"), onclick: () => onDiscard() });
    const actions = h("div", { class: "card-actions inline" }, editBtn, delBtn);
    art.querySelector(".card-main").append(actions);
  }
  return art;
}

// Show her line with the words the model picked out highlighted (green = checked, amber = look).
function highlightLine(line, cards) {
  const lower = line.toLowerCase();
  const marks = [];
  for (const c of cards) {
    for (const span of [c.student_text, c.amount_text, c.month_text, c.date_text]) {
      if (!span) continue;
      const s = span.toLowerCase();
      let from = 0, at;
      while ((at = lower.indexOf(s, from)) !== -1) {
        const end = at + s.length;
        if (!marks.some((m) => at < m.end && end > m.start)) { marks.push({ start: at, end, cls: c.verdict === "ok" ? "ok" : "confirm" }); break; }
        from = end;
      }
    }
  }
  marks.sort((a, b) => a.start - b.start);
  const out = h("p", { class: "heard-line" });
  let pos = 0;
  for (const m of marks) {
    if (m.start > pos) out.append(line.slice(pos, m.start));
    out.append(h("mark", { class: m.cls, text: line.slice(m.start, m.end) }));
    pos = m.end;
  }
  out.append(line.slice(pos));
  return out;
}

function renderParsed() {
  const box = $("#cards");
  const heard = $("#heard");
  const p = S.parsed;
  box.replaceChildren();
  $("#cards-actions").hidden = true;
  heard.hidden = true;
  if (!p) { $("#parse-status").replaceChildren(); return; }

  const ok = p.cards.filter((c) => c.verdict === "ok").length;
  const amber = p.cards.length - ok;
  $("#parse-status").replaceChildren(
    ok ? h("span", { class: "pill ok", text: `✓ ${ok} ${L("checked_n")}` }) : null,
    amber ? h("span", { class: "pill warn", text: `! ${amber} ${L("look_n")}` }) : null,
    h("span", { text: `${p.seconds}s · ${MODEL_NAMES[p.model] || p.model}` }));

  heard.replaceChildren(h("p", { class: "heard-label", text: L("heard") }), highlightLine(p.line, p.cards));
  heard.hidden = false;

  if (!p.cards.length) { box.append(h("p", { class: "lede", text: L("no_events") })); return; }
  p.cards.forEach((c, i) => box.append(renderCard(c, p, {
    onSaved: () => { p.cards.splice(i, 1); renderParsed(); loadToday(); },
    onDiscard: () => { p.cards.splice(i, 1); renderParsed(); },
  }, i)));
  $("#cards-actions").hidden = false;
  const btn = $("#save-green");
  btn.textContent = ok ? `${ok} ${L("save_n_green")}` : `${amber} → ${L("tab_check")}`;
  $("#save-note").textContent = ok && amber ? `${amber} ${L("save_note")}` : "";
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
  if (!S.tray.length) { box.append(h("ul", { class: "list" }, h("li", { class: "empty", text: `✓ ${L("tray_empty")}` }))); return; }
  S.tray.forEach((item, i) => {
    const ctx = { line: item.line, entry_date: item.entry_date, model: item.model };
    const remove = () => { S.tray = S.tray.filter((x) => x.key !== item.key); saveTray(); renderTray(); };
    box.append(h("div", { class: "heard" },
      h("p", { class: "heard-label", text: `${L("from_line")} · ${dayLabel(item.entry_date)}` }),
      highlightLine(item.line, [item.card])));
    box.append(renderCard(item.card, ctx, { onSaved: () => { remove(); loadToday(); }, onDiscard: remove }, i));
  });
}

// ---------- Likho ----------
async function onRead(e) {
  e.preventDefault();
  const line = $("#line").value.trim();
  if (!line) return;
  const btn = $("#read-btn");
  btn.disabled = true;
  btn.setAttribute("aria-busy", "true");
  $("#parse-status").replaceChildren(h("span", { class: "pill muted", text: L("reading") }));
  try {
    const r = await api("/api/parse", { method: "POST", json: { line, entry_date: $("#entry-date").value || null } });
    S.parsed = { line: r.line, entry_date: r.entry_date, model: r.model, seconds: r.seconds, cards: r.events };
    renderParsed();
  } catch (err) {
    $("#parse-status").replaceChildren(h("span", { class: "pill due", text: `${L("error")}: ${err.message}` }));
  } finally { btn.disabled = false; btn.removeAttribute("aria-busy"); }
}

async function loadToday() {
  const d = $("#entry-date").value;
  const ul = $("#today-list");
  try {
    const rows = await api(`/api/entries?entry_date=${encodeURIComponent(d)}`);
    ul.replaceChildren();
    if (!rows.length) { ul.append(h("li", { class: "empty", text: L("nothing_saved") })); return; }
    rows.forEach((e) => {
      const c = Object.assign({}, e);
      const v = cardValue(c);
      ul.append(h("li", {},
        h("span", { class: "type-ic", "aria-hidden": "true", text: TYPE_IC[e.type] || "•" }),
        h("div", { class: "row-main" },
          h("div", { class: "row-title", text: e.student_name || "?" }),
          h("div", { class: "row-sub", text: `${pick(TYPE_LABEL[e.type])}${e.verdict === "confirmed_by_user" ? (S.lang === "hi" ? " · aapne pakka kiya" : " · confirmed by you") : ""}` })),
        h("div", { class: "row-end" }, h("strong", { text: v.big }), h("span", { class: "row-sub", text: v.small })),
        h("button", { type: "button", class: "btn text", text: "✕", "aria-label": `${L("discard")} ${cardSummary(c)}`,
          onclick: async () => { await api(`/api/entries/${e.id}`, { method: "DELETE" }); loadToday(); } })));
    });
  } catch (err) { /* PIN or server down: shown in the status line */ }
}

// ---------- Baaki ----------
function promiseTag(p) {
  if (!p) return null;
  const late = p.status === "overdue";
  return h("span", { class: `promise ${late ? "overdue" : ""}`,
    text: `${late ? "⏰" : "🤝"} ${L("promised")} ${inr(p.amount)}${p.on_date ? " " + byDate(p.on_date) : ""}${late ? " · " + L("overdue") : ""}` });
}

function parkDetail() {
  const box = $("#student-detail");
  box.hidden = true;
  $("#panel-baaki").append(box);
  document.querySelectorAll("#dues-list .row-btn[aria-expanded]").forEach((b) => b.setAttribute("aria-expanded", "false"));
}

async function loadDues() {
  const month = $("#dues-month").value || S.today.slice(0, 7);
  const wrap = $("#dues-list");
  try {
    const d = await api(`/api/dues?month=${encodeURIComponent(month)}`);
    parkDetail();
    const owes = d.rows.filter((r) => r.balance > 0);
    const clear = d.rows.filter((r) => r.balance <= 0);
    const pct = d.total_due ? Math.round((100 * d.total_paid) / d.total_due) : 0;

    const meter = h("div", { class: "meter", role: "img", "aria-label": `${pct}% ${L("collected")}` }, h("span"));
    $("#dues-total").replaceChildren(
      h("div", { class: `summary-big ${owes.length ? "" : "clear"}` },
        h("strong", { text: owes.length ? inr(d.total_balance) : "✓" }),
        h("span", { text: owes.length ? `${monthName(month)} ${L("pending_in")} · ${owes.length} ${L("of_students")}` : L("everyone_paid") })),
      meter,
      h("div", { class: "summary-foot" },
        h("span", {}, h("b", { text: inr(d.total_paid) }), ` ${L("collected")}`),
        h("span", { text: `${L("of_total")} ${inr(d.total_due)} · ${pct}%` })));
    meter.firstChild.style.width = pct + "%";

    const row = (r) => {
      const btn = h("button", { type: "button", class: "row-btn", "aria-expanded": "false", "data-name": r.name },
        h("span", { class: `avatar ${batchClass(r.batch)}`, "aria-hidden": "true", text: initials(r.name) }),
        h("div", { class: "row-main" },
          h("div", { class: "row-title", text: r.name }),
          h("div", { class: "row-sub", text: `${r.batch || ""} · ${L("due")} ${inr(r.due)} · ${L("paid")} ${inr(r.paid)}` }),
          promiseTag(r.promise)),
        h("div", { class: "row-end" }, r.balance > 0
          ? h("strong", { class: "due", text: inr(r.balance) })
          : h("strong", { class: "clear", text: `✓ ${L("all_clear")}` })),
        svgIcon(CHEVRON));
      btn.querySelector("svg:last-child").setAttribute("class", "chev");
      const li = h("li", { class: "has-btn" }, btn);
      btn.addEventListener("click", () => toggleStudent(li, btn, r.student_id, month));
      return li;
    };

    wrap.replaceChildren(
      owes.length ? h("h3", { class: "group-title", text: `${L("owes_group")} · ${owes.length}` }) : null,
      owes.length ? h("ul", { class: "list" }, owes.map(row)) : null,
      clear.length ? h("h3", { class: "group-title", text: `${L("clear_group")} · ${clear.length}` }) : null,
      clear.length ? h("ul", { class: "list" }, clear.map(row)) : null);
  } catch (err) { $("#dues-total").textContent = `${L("error")}: ${err.message}`; }
}

async function toggleStudent(li, btn, sid, month) {
  const box = $("#student-detail");
  if (btn.getAttribute("aria-expanded") === "true") { parkDetail(); return; }
  parkDetail();
  btn.setAttribute("aria-expanded", "true");
  li.append(box);
  await renderStudent(box, sid, month);
  box.hidden = false;
}

async function renderStudent(box, sid, month) {
  const d = await api(`/api/students/${sid}/ledger`);
  const rows = d.months.slice().reverse().slice(0, 6).map((m) => h("tr", {},
    h("td", { text: monthName(m.month, false) }), h("td", { text: inr(m.due) }), h("td", { text: inr(m.paid) }),
    h("td", { class: m.balance > 0 ? "owes" : "ok", text: m.balance > 0 ? inr(m.balance) : "✓" }),
    h("td", { text: m.attendance.absent })));
  const langSel = h("select", { id: "rem-lang" }, h("option", { value: "hinglish", text: "Hinglish" }),
    h("option", { value: "hi", text: "हिंदी" }), h("option", { value: "en", text: "English" }));
  const toneSel = h("select", { id: "rem-tone" }, h("option", { value: "gentle", text: S.lang === "hi" ? "Pyaar se" : "Gentle" }),
    h("option", { value: "normal", text: S.lang === "hi" ? "Seedha" : "Normal" }),
    h("option", { value: "firm-but-polite", text: S.lang === "hi" ? "Thoda sakht, par izzat se" : "Firm but polite" }));
  const bubble = h("div", { id: "rem-text", class: "bubble", "aria-label": L("reminder") });
  const src = h("p", { class: "rem-src", role: "status", "aria-live": "polite" });
  const wa = h("a", { class: "btn text", href: "#", hidden: true, target: "_blank", rel: "noopener noreferrer" }, L("wa_link"), " ", h("small", { text: L("wa_note") }));
  const remMonth = (d.months.find((m) => m.month === month && m.balance > 0) || d.months.slice().reverse().find((m) => m.balance > 0) || {}).month;

  const previewBtn = h("button", { type: "button", class: "btn primary", text: L("preview"), disabled: !remMonth });
  const copyBtn = h("button", { type: "button", class: "btn quiet", text: L("copy"), hidden: true });
  previewBtn.addEventListener("click", async () => {
    previewBtn.disabled = true;
    previewBtn.setAttribute("aria-busy", "true");
    src.textContent = L("reading");
    try {
      const r = await api("/api/reminders", { method: "POST", json: { student_id: sid, month: remMonth, lang: langSel.value, tone: toneSel.value } });
      bubble.textContent = r.text;
      src.textContent = L("src_" + r.source);
      wa.href = "https://wa.me/?text=" + encodeURIComponent(r.text);
      wa.hidden = false;
      copyBtn.hidden = false;
    } catch (e) { src.textContent = `${L("error")}: ${e.message}`; }
    previewBtn.disabled = false;
    previewBtn.removeAttribute("aria-busy");
  });
  copyBtn.addEventListener("click", async () => {
    if (!bubble.textContent) return;
    try { await navigator.clipboard.writeText(bubble.textContent); src.textContent = L("copied"); }
    catch (e) { src.textContent = L("error"); }
  });

  box.replaceChildren(h("div", { class: "detail" },
    h("div", { class: "detail-head" },
      h("span", { class: "row-sub", text: `${L("outstanding")}${d.advance ? " · " + L("advance") + " " + inr(d.advance) : ""}` }),
      h("strong", { class: d.outstanding > 0 ? "" : "clear", text: d.outstanding > 0 ? inr(d.outstanding) : "✓" })),
    h("table", { class: "ledger" },
      h("thead", {}, h("tr", {}, h("th", { text: L("month_col") }), h("th", { text: L("due") }),
        h("th", { text: L("paid") }), h("th", { text: L("balance") }), h("th", { text: L("absent_col") }))),
      h("tbody", {}, rows)),
    remMonth ? h("div", { class: "rem" },
      h("h3", { text: `${L("reminder")} · ${monthName(remMonth, false)}` }),
      h("div", { class: "rem-opts" },
        h("div", {}, h("label", { for: "rem-lang", text: L("lang") }), langSel),
        h("div", {}, h("label", { for: "rem-tone", text: L("tone") }), toneSel)),
      bubble, src,
      h("div", { class: "rem-actions" }, previewBtn, copyBtn, wa)) : null));
}

// ---------- Bachche ----------
async function loadStudents() {
  S.students = await api("/api/students");
  const ul = $("#students-list");
  if (!ul) return;
  ul.replaceChildren();
  S.students.forEach((s) => {
    ul.append(h("li", {},
      h("span", { class: `avatar ${batchClass(s.batch)}`, "aria-hidden": "true", text: initials(s.name) }),
      h("div", { class: "row-main" },
        h("div", { class: "row-title" }, s.name, s.aliases.length ? h("span", { class: "row-sub", text: ` · ${s.aliases.join(", ")}` }) : null),
        h("div", { class: "row-sub", text: `${s.batch || ""} · ${inr(s.monthly_fee)}${L("per_month")} · ${S.lang === "hi" ? monthName(s.start_month) + " " + L("since") : L("since") + " " + monthName(s.start_month)}${s.end_month ? " · " + L("left") + " " + monthName(s.end_month) : ""}` })),
      h("div", { class: "row-end" }, s.outstanding > 0
        ? h("strong", { class: "due", text: inr(s.outstanding) })
        : h("strong", { class: "clear", text: "✓" }))));
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

function renderAskHint() {
  const t = $("#answer");
  if (!t.children.length || t.dataset.hint === "1") {
    t.dataset.hint = "1";
    t.replaceChildren(h("div", { class: "a-bubble" }, h("p", { text: L("ask_hint") })));
  }
}

async function ask(question, studentId = null) {
  const t = $("#answer");
  if (t.dataset.hint === "1") { t.replaceChildren(); t.dataset.hint = "0"; }
  t.append(h("div", { class: "q-bubble", text: question }));
  const a = h("div", { class: "a-bubble" }, h("p", { class: "row-sub", text: L("reading") }));
  t.append(a);
  try {
    const r = await api("/api/ask", { method: "POST", json: { question, student_id: studentId } });
    a.replaceChildren(h("p", { text: S.lang === "hi" ? r.hi : r.en }));
    if (r.candidates && r.candidates.length) {
      a.append(h("div", { class: "chips", role: "group", "aria-label": L("pick_student") },
        r.candidates.map((c) => h("button", { type: "button", text: c.name, onclick: () => ask(question, c.id) }))));
    }
  } catch (err) { a.replaceChildren(h("p", { text: `${L("error")}: ${err.message}` })); }
  a.scrollIntoView({ block: "nearest" });
}

// ---------- init ----------
function init() {
  applyLang();
  setupTabs();
  saveTray();
  $("#lang-hi").addEventListener("click", () => setLang("hi"));
  $("#lang-en").addEventListener("click", () => setLang("en"));
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
  $("#ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("#question").value.trim();
    if (q) { ask(q); $("#question").value = ""; }
  });
  const ex = $("#ask-examples");
  EXAMPLES.forEach((q) => ex.append(h("button", { type: "button", text: q, onclick: () => ask(q) })));
  renderAskHint();
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
