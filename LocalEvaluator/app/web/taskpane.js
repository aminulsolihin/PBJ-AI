/* Local Evaluator task pane. Talks only to the engine on this computer (same origin). */
"use strict";

const $ = (id) => document.getElementById(id);
let workbook = null;     // full path of the workbook this pane belongs to
let layout = null;       // last answer of /api/layout
let pollTimer = null;

async function api(path, body) {
  const opt = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Local-Evaluator": "1" },
    body: JSON.stringify(Object.assign({ workbook, sheet: layout && layout.sheet }, body)),
  };
  let resp;
  try { resp = await fetch(path, opt); }
  catch (e) { throw new Error("The engine is not answering. Start \"Local Evaluator engine\" from the Start menu."); }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || resp.statusText);
  return data;
}

function el(tag, props, ...kids) {
  const node = Object.assign(document.createElement(tag), props || {});
  kids.flat().forEach((k) => node.append(k));
  return node;
}

function banner(text, note) {
  const b = $("banner");
  b.hidden = !text;
  b.textContent = text || "";
  b.className = "banner" + (note ? " note" : "");
}

/* window.confirm does not work inside Office panes, so questions are asked in the page. */
function ask(text, options) {
  return new Promise((resolve) => {
    $("ask-text").textContent = text;
    const box = $("ask-buttons");
    box.replaceChildren(...options.map(([label, value, cls]) =>
      el("button", { className: cls || "", textContent: label, onclick: () => { $("ask").hidden = true; resolve(value); } })));
    $("ask").hidden = false;
  });
}

async function guard(button, fn) {
  if (button) button.disabled = true;
  banner("");
  try { await fn(); } catch (e) { banner(e.message); }
  finally { if (button) button.disabled = false; }
}

/* ------------------------------------------------------------------ status */
async function refreshStatus() {
  let s;
  try { s = await api("/api/status"); }
  catch (e) { $("l-engine").className = "light bad"; banner(e.message); return null; }
  $("l-engine").className = "light ok";
  $("l-model").className = "light " + (s.ollama && s.models.length ? "ok" : "bad");
  $("l-excel").className = "light " + (s.excelLink ? "" : "bad");
  const sel = $("s-model");
  sel.replaceChildren(...s.models.map((m) => el("option", { value: m, textContent: m })));
  if (s.models.includes(s.settings.model)) sel.value = s.settings.model;
  $("s-expand").checked = !!s.settings.expandKeywords;
  $("s-chars").value = String(s.settings.excerptChars);
  if (!s.ollama) banner("The local model service (Ollama) is not running. Start Ollama, then reopen this pane.");
  else if (!s.models.length) banner("No local model is installed in Ollama.");
  else if (!s.models.includes(s.settings.model)) banner(`Model "${s.settings.model}" is not installed. Choose another under Settings.`, true);
  if (s.job === "running") startPolling();
  return s;
}

/* ------------------------------------------------------------------ layout */
async function refreshLayout() {
  try { layout = await api("/api/layout", { sheet: null }); }   // always the sheet the user is looking at
  catch (e) {
    $("l-excel").className = "light bad";
    $("crit-info").textContent = e.message;
    $("crit-rows").hidden = true;
    $("bidders").replaceChildren();
    $("bidder-tools").replaceChildren();
    return;
  }
  $("l-excel").className = "light ok";
  const p = layout.profile;
  const rows = $("crit-rows");
  if (!p) {
    $("crit-info").textContent = `Sheet "${layout.sheet}" has no criteria table (a header row with "No." and "Requirement"). Open a criteria sheet, or add one below.`;
    rows.hidden = true;
    $("crit-new").open = true;
    $("bidder-tools").replaceChildren();
    $("bidder-new").hidden = true;
    $("bidders").replaceChildren(el("p", { className: "hint", textContent: "Bidders appear here once the sheet has criteria." }));
    return;
  }
  const named = p.targets.filter((t) => t.bidder);
  $("crit-info").textContent = p.mode === "stacked"
    ? `Sheet "${p.sheet}" (${p.title}): one block per bidder, ${named.length} bidder(s), ${p.toEvaluate} requirement(s) each. Verdict words: ${Object.values(p.labels).join(" / ")}.`
    : `Sheet "${p.sheet}": ${p.toEvaluate} requirement(s) will be evaluated. Headings and grouped rows are skipped.`;
  rows.hidden = false;
  rows.replaceChildren(...p.table.rows.map((r) => r.kind === "section"
    ? el("li", { className: "skip" }, el("span", { className: "no", textContent: "" }), el("span", { textContent: r.text }))
    : el("li", { className: r.group ? "skip" : "" },
        el("span", { className: "no", textContent: r.no }),
        el("span", { textContent: r.requirement.length > 110 ? r.requirement.slice(0, 110) + "…" : r.requirement }))));
  renderBidders(p);
}

function bidderCard(t, p) {
  const done = t.filled.length;
  const chips = !t.col ? [el("span", { className: "chip none", textContent: "no AI columns yet" })]
    : done ? Object.entries(t.counts).filter(([, n]) => n).map(([k, n]) => el("span", { className: "chip " + k.split(" ")[0], textContent: `${p.labels[k]}: ${n}` }))
    : [el("span", { className: "chip none", textContent: "not evaluated yet" })];
  const evalBtn = el("button", { textContent: done ? "Evaluate again" : "Evaluate", disabled: !t.col });
  evalBtn.onclick = () => guard(evalBtn, () => evaluate([t], p));
  const folderBtn = el("button", { className: "ghost", textContent: t.folder ? "Change folder" : "Choose folder" });
  folderBtn.onclick = () => guard(folderBtn, async () => {
    const r = await api("/api/pick", { kind: "folder" });
    if (!r.path) return;
    layout = await api("/api/bidder/folder", { name: t.bidder, folder: r.path });
    renderBidders(layout.profile);
  });
  return el("div", { className: "card" },
    el("h3", { textContent: t.bidder }),
    el("div", { className: "folder", textContent: t.folder || "No documents folder chosen" }),
    el("div", { className: "chips" }, chips),
    el("div", { className: "actions" }, evalBtn, folderBtn));
}

function renderBidders(p) {
  const box = $("bidders"), tools = $("bidder-tools");
  const named = p.targets.filter((t) => t.bidder);
  const stacked = p.mode === "stacked";
  $("bidder-new").hidden = false;
  $("b-hint").hidden = !stacked;
  $("b-hint").textContent = stacked
    ? "This workbook has one block per bidder. Adding a bidder creates a new block on every bidder sheet and a new row on the summary sheet. Existing rows are not changed, and a copy of the workbook is saved first."
    : "";
  $("b-add").textContent = stacked ? "Add bidder to the workbook" : "Add bidder columns";
  const buttons = [];
  if (stacked && p.targets.some((t) => !t.col)) {
    const prep = el("button", { textContent: "Add AI Evaluation columns" });
    prep.onclick = () => guard(prep, async () => { layout = await api("/api/prepare", {}); renderBidders(layout.profile); });
    buttons.push(prep);
  }
  if (named.length > 1) {
    const auto = el("button", { className: "ghost", textContent: "Find folders automatically" });
    auto.title = "Choose the folder that holds one sub-folder per bidder; names are matched.";
    auto.onclick = () => guard(auto, async () => {
      const r = await api("/api/pick", { kind: "folder" });
      if (!r.path) return;
      layout = await api("/api/bidder/automatch", { folder: r.path });
      renderBidders(layout.profile);
      banner(`${layout.matched} bidder folder(s) matched by name. Check each one before evaluating.`, true);
    });
    const all = el("button", { className: "ghost", textContent: "Evaluate all" });
    all.onclick = () => guard(all, () => evaluate(layout.profile.targets.filter((t) => t.bidder && t.col && t.folder), layout.profile));
    buttons.push(auto, all);
  }
  tools.replaceChildren(...buttons);
  if (stacked && p.targets.some((t) => !t.col)) {
    tools.append(el("p", { className: "hint", textContent: "Adds three columns to the right of your table for every bidder block: REMARKS, NOTES and ATTACHED DOCUMENT, each marked (AI Evaluation). Your own columns are not changed." }));
  }
  if (!named.length) {
    box.replaceChildren(el("p", { className: "hint", textContent: stacked
      ? "No bidder names were found in the \"Name of Bidder\" rows."
      : "No bidder on this sheet yet. Add one below; it gets three AI Evaluation columns to the right of the table." }));
    if (!stacked) $("bidder-new").open = true;
    return;
  }
  box.replaceChildren(...named.map((t) => bidderCard(t, p)));
}

/* -------------------------------------------------------------- evaluation */
async function evaluate(targets, p) {
  if (!targets.length) throw new Error("No bidder is ready: each needs AI Evaluation columns and a documents folder.");
  const missing = targets.filter((t) => !t.folder);
  if (missing.length) throw new Error(`Choose the documents folder for ${missing[0].bidder} first.`);
  const filled = targets.reduce((n, t) => n + t.filled.length, 0);
  const total = targets.reduce((n, t) => n + t.toEvaluate, 0);
  const edited = targets.flatMap((t) => t.edited);
  const who = targets.length === 1 ? targets[0].bidder : `${targets.length} bidders`;
  let mode = "all";
  if (filled || total > 12) {
    let text = `${who}: ${total} requirement row(s), roughly ${fmt(total * 300)} on this laptop.`;
    if (filled) text += `\n\n${filled} row(s) are already evaluated.`;
    if (edited.length) text += `\n${edited.length} of them look edited by hand (rows ${edited.slice(0, 12).join(", ")}${edited.length > 12 ? ", …" : ""}); evaluating again overwrites them.`;
    const options = [];
    if (filled && total - filled > 0) options.push([`Only the ${total - filled} empty row(s)`, "empty"]);
    options.push([filled ? "Evaluate all rows again" : "Start", "all"], ["Cancel", null, "ghost"]);
    mode = await ask(text, options);
    if (!mode) return;
  }
  await api("/api/evaluate", { bidders: targets.map((t) => t.bidder), mode });
  startPolling();
}

function startPolling() {
  $("run").hidden = false;
  if (pollTimer) return;
  const tick = async () => {
    let j;
    try { j = await api("/api/job"); } catch (e) { return; }
    renderJob(j);
    if (j.state !== "running") { clearInterval(pollTimer); pollTimer = null; refreshLayout(); }
  };
  pollTimer = setInterval(tick, 2000);
  tick();
}

function fmt(sec) {
  if (sec == null) return "";
  const m = Math.round(sec / 60);
  return m < 1 ? "under a minute" : m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`;
}

function renderJob(j) {
  $("run-title").textContent = j.title ? "· " + j.title : "";
  $("run-bar").style.width = (j.total ? Math.round((100 * j.done) / j.total) : 0) + "%";
  const running = j.state === "running";
  $("run-stop").hidden = !running;
  const last = j.log.length ? j.log[j.log.length - 1].replace(/^\S+\s+/, "") : "";
  $("run-info").textContent = running
    ? `${j.done} of ${j.total || "?"} done` + (j.eta != null ? ` · about ${fmt(j.eta)} left` : "") + (last ? ` · ${last}` : "")
    : j.state === "done" ? `Finished in ${fmt(j.elapsed)}. Draft only: review each row, then save the workbook.`
    : j.state === "cancelled" ? "Stopped." : j.state === "error" ? "Stopped: " + j.error : "";
  const many = new Set(j.results.map((r) => r.bidder)).size > 1;
  $("run-results").replaceChildren(...j.results.slice().reverse().map((r) => el("li", {},
    el("span", { className: "no", textContent: r.no }),
    el("span", {}, el("span", { className: "chip " + r.label.split(" ")[0], textContent: r.shown || r.label }),
      many ? el("span", { className: "q", textContent: r.bidder }) : "",
      r.question ? el("span", { className: "q", textContent: r.question }) : ""))));
  $("run-log").textContent = j.log.join("\n");
}

/* ------------------------------------------------------------------- wiring */
function wire() {
  $("crit-browse").onclick = (e) => guard(e.target, async () => { const r = await api("/api/pick", { kind: "file" }); if (r.path) $("crit-path").value = r.path; });
  $("crit-import").onclick = (e) => guard(e.target, async () => {
    layout = await api("/api/criteria/import", { path: $("crit-path").value, title: $("crit-title").value.trim() });
    $("crit-new").open = false; await refreshLayout();
  });
  $("crit-pastebtn").onclick = (e) => guard(e.target, async () => {
    if (!$("crit-paste").value.trim()) throw new Error("Paste the criteria table first.");
    layout = await api("/api/criteria/import", { text: $("crit-paste").value, title: $("crit-title").value.trim() });
    $("crit-paste").value = ""; $("crit-new").open = false; await refreshLayout();
  });
  $("b-browse").onclick = (e) => guard(e.target, async () => { const r = await api("/api/pick", { kind: "folder" }); if (r.path) $("b-folder").value = r.path; });
  $("b-add").onclick = (e) => guard(e.target, async () => {
    const name = $("b-name").value.trim();
    if (!name) throw new Error("Type the new bidder's name.");
    if (!(layout && layout.profile && layout.profile.mode === "stacked")) {
      layout = await api("/api/bidder/add", { name, folder: $("b-folder").value });
      $("b-name").value = ""; $("b-folder").value = ""; $("bidder-new").open = false; await refreshLayout();
      return;
    }
    // one block per bidder: show exactly what will be added, then add it
    const plan = await api("/api/bidder/plan-block", {});
    const lines = plan.sheets.map((s) => `• ${s.sheet}: a new block in rows ${s.rows}`);
    if (plan.summary) lines.push(`• ${plan.summary.sheet}: a new row ${plan.summary.row}`);
    const ok = await ask(`Add "${name}" as bidder ${plan.number}?\n\n${lines.join("\n")}\n\nExisting rows are not changed. A copy of the workbook as it is now is saved first.`,
      [["Add bidder", true], ["Cancel", false, "ghost"]]);
    if (!ok) return;
    const done = await api("/api/bidder/add-block", { name, folder: $("b-folder").value });
    $("b-name").value = ""; $("b-folder").value = ""; $("bidder-new").open = false;
    await refreshLayout();
    const r = done.report;
    let note = `${r.bidder} added as bidder ${r.number}.`;
    if (r.notExtended.length) note += ` Not added on: ${r.notExtended.join(", ")} (those sheets have a fixed number of bidder slots).`;
    if (r.summary) note += ` Check the formulas in row ${r.summary.row} of ${r.summary.sheet}.`;
    if (r.wiringProblems.length) note += ` Note: some existing formulas on ${r.wiringProblems[0].sheet} (columns ${r.wiringProblems.map((w) => w.column).join(", ")}) do not point at their own bidder's rows.`;
    banner(note, true);
  });
  $("run-stop").onclick = (e) => guard(e.target, () => api("/api/cancel", {}));
  $("attach").onclick = (e) => guard(e.target, async () => {
    const r = await api("/api/attach", {});
    if (r.result === "cancelled") return;
    banner(r.result === "present"
      ? `${r.name} already has the pane; it is opening now.`
      : `${r.name} now has its own Local Evaluator pane and is opening. Use the pane in that workbook.`, true);
  });
  const saveSettings = () => guard(null, () => api("/api/settings", {
    model: $("s-model").value, expandKeywords: $("s-expand").checked, excerptChars: Number($("s-chars").value) }));
  $("s-model").onchange = $("s-expand").onchange = $("s-chars").onchange = saveSettings;
  window.addEventListener("focus", () => { if (!pollTimer) refreshLayout(); });
}

async function start() {
  wire();
  if (await refreshStatus()) await refreshLayout();
}

function boot() {
  const inOffice = window.Office && Office.context && Office.context.document;
  if (inOffice) {
    workbook = Office.context.document.url || null;
    if (!workbook) {  // without a file path the engine cannot tell this workbook from other open ones
      wire();
      banner("Save this workbook first, then close and reopen this pane.", true);
      $("crit-info").textContent = "Waiting for the workbook to be saved.";
      return;
    }
    try {  // refresh when the user switches sheet
      Excel.run(async (ctx) => { ctx.workbook.worksheets.onActivated.add(async () => { layout = null; await refreshLayout(); }); await ctx.sync(); });
    } catch (e) { /* older Excel: the pane still refreshes on focus */ }
    try {  // remember this pane in the workbook: once the workbook is saved, the pane opens with it next time
      const s = Office.context.document.settings;
      if (s.get("Office.AutoShowTaskpaneWithDocument") !== true) {
        s.set("Office.AutoShowTaskpaneWithDocument", true);
        s.saveAsync();
      }
    } catch (e) { /* not essential */ }
  } else {
    // opened in a plain browser for testing: ?wb=<full path of an open workbook>
    workbook = new URLSearchParams(location.search).get("wb") || null;
  }
  start();
}

if (window.Office && Office.onReady) Office.onReady(boot); else boot();
