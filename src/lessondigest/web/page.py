from __future__ import annotations

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LessonDigest</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         background: #f4f6f8; color: #1c2530; }
  header { background: #12263f; color: #fff; padding: 18px 20px; }
  header h1 { margin: 0; font-size: 20px; }
  header p { margin: 4px 0 0; color: #a9bad0; font-size: 13px; }
  main { max-width: 900px; margin: 0 auto; padding: 20px; }
  .card { background: #fff; border: 1px solid #dde3ea; border-radius: 12px; padding: 18px;
          margin-bottom: 18px; }
  h2 { font-size: 16px; margin: 0 0 12px; }
  label { display: block; font-size: 13px; color: #46566b; margin-bottom: 6px; }
  input[type=text], input[type=file] { width: 100%; padding: 10px; border: 1px solid #cfd8e3;
          border-radius: 8px; font-size: 14px; background: #fff; }
  input[type=file] { padding: 8px; }
  button { margin-top: 12px; background: #1f6feb; color: #fff; border: 0; padding: 11px 18px;
           border-radius: 8px; font-size: 15px; cursor: pointer; }
  button:disabled { background: #97b3d8; cursor: default; }
  .row { margin-bottom: 14px; }
  .status { margin-top: 14px; padding: 12px 14px; border-radius: 8px; background: #eef4ff;
            border: 1px solid #cfe0ff; font-size: 14px; }
  .status .tag { font-weight: 600; }
  .err { color: #a01717; }
  .muted { color: #6b7a8c; font-size: 13px; }
  .run { display: flex; gap: 8px; align-items: center; padding: 8px 0; border-bottom: 1px solid #eef1f5;
         font-size: 14px; }
  .run:last-child { border-bottom: 0; }
  .run a { color: #1f6feb; text-decoration: none; }
  .subj { color: #6b7a8c; font-size: 12px; }
  .tag { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #e8eef6; color: #33475f; }
  .tag.done { background: #dff3e3; color: #1c6b34; }
  .tag.failed { background: #fbe0e0; color: #a01717; }
  .tag.running { background: #fff2d8; color: #8a5a00; }
  #progressWrap { margin-top: 12px; }
  .bar { height: 10px; background: #e3e8ef; border-radius: 999px; overflow: hidden; position: relative; }
  .bar-fill { height: 100%; width: 0; background: #1f6feb; border-radius: 999px;
              transition: width .4s ease; }
  .bar.indeterminate .bar-fill { width: 35%; animation: ind 1.1s ease-in-out infinite alternate; }
  @keyframes ind { from { margin-left: 0; } to { margin-left: 65%; } }
  .pct { margin-top: 6px; font-size: 13px; color: #46566b; }
  .md { line-height: 1.55; }
  .md h1 { font-size: 22px; }
  .md h2 { font-size: 16px; margin-top: 20px; color: #12263f; }
  .md ul, .md ol { padding-left: 22px; }
  .md hr { border: 0; border-top: 1px solid #e3e8ef; margin: 18px 0; }
</style>
</head>
<body>
<header>
  <h1>LessonDigest</h1>
  <p>Загрузите аудиозапись урока — получите структурированный конспект</p>
</header>
<main>
  <section class="card">
    <h2>Новый урок</h2>
    <form id="form">
      <div class="row">
        <label for="file">Аудиофайл (m4a, mp3, wav, ogg, flac)</label>
        <input id="file" name="file" type="file" accept="audio/*,.m4a,.mp3,.wav,.ogg,.flac" required>
      </div>
      <div class="row">
        <label for="subject">Предмет (необязательно)</label>
        <input id="subject" name="subject" type="text" placeholder="алгебра, физика, история…">
      </div>
      <button id="submit" type="submit">Обработать</button>
    </form>
    <div id="status"></div>
    <div id="progressWrap" style="display:none">
      <div class="bar" id="bar"><div class="bar-fill" id="barfill"></div></div>
      <div class="pct" id="pct"></div>
    </div>
  </section>

  <section class="card">
    <h2>Результат</h2>
    <div id="result"><p class="muted">Пока ничего не обработано.</p></div>
  </section>

  <section class="card">
    <h2>История прогонов</h2>
    <div id="recent"><p class="muted">Загрузка…</p></div>
  </section>
</main>
<script>
const $ = (sel) => document.querySelector(sel);
const form = $("#form"), submitBtn = $("#submit");
let polling = null;

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.status + " " + res.statusText;
    try { const j = await res.json(); if (j.detail) detail = j.detail; } catch (e) {}
    throw new Error(detail);
  }
  return res;
}

function setStatus(html) {
  $("#status").innerHTML = `<div class="status">${html}</div>`;
}

function setProgress(percent) {
  const wrap = $("#progressWrap"), bar = $("#bar"), fill = $("#barfill"), pct = $("#pct");
  wrap.style.display = "block";
  if (percent === null || percent === undefined) {
    bar.classList.add("indeterminate");
    fill.style.width = "";
    pct.textContent = "обработка…";
  } else {
    bar.classList.remove("indeterminate");
    fill.style.width = percent + "%";
    pct.textContent = percent + "%";
  }
}

async function loadRecent() {
  try {
    const runs = await (await api("/api/runs")).json();
    const box = $("#recent");
    if (!runs.length) { box.innerHTML = '<p class="muted">Прогонов пока нет.</p>'; return; }
    box.innerHTML = "";
    for (const run of runs.slice(0, 25)) {
      const el = document.createElement("div");
      el.className = "run";
      el.innerHTML = `<a href="#" data-id="${run.run_id}">${run.run_id}</a>` +
        `<span class="tag ${run.status}">${run.stage_label}</span>` +
        `<span class="subj">${run.subject || ""}</span>`;
      el.querySelector("a").onclick = (e) => { e.preventDefault(); showRun(run.run_id); };
      box.appendChild(el);
    }
  } catch (e) {
    $("#recent").innerHTML = `<p class="err">Не удалось получить список: ${e.message}</p>`;
  }
}

async function showRun(runId, wait) {
  const box = $("#result");
  if (!wait) box.innerHTML = '<p class="muted">Загрузка…</p>';
  const st = await (await api(`/api/runs/${runId}`)).json();
  if (wait) {
    setStatus(`<span class="tag ${st.status}">${st.stage_label}</span> · ${runId}`);
    setProgress(st.percent);
    if (st.status === "queued" || st.status === "running") {
      polling = setTimeout(() => showRun(runId, true), 2000);
      return;
    }
    clearTimeout(polling);
    submitBtn.disabled = false;
    if (st.status === "failed") {
      box.innerHTML = `<p class="err">Ошибка: ${st.error || "неизвестно"}</p>`;
      setStatus(`<span class="err">Ошибка обработки</span>`);
      setProgress(null);
      loadRecent();
      return;
    }
    setStatus(`<span class="tag done">Готово</span> · ${runId}`);
    setProgress(100);
  }
  if (st.digest_available) {
    const d = await (await api(`/api/runs/${runId}/digest`)).json();
    box.innerHTML = `<article class="md">${d.html}</article>` +
      `<p><a href="/api/runs/${runId}/digest.md" download>Скачать .md</a> · ` +
      `<a href="/api/runs/${runId}/transcript" download>Скачать транскрипт</a></p>`;
  } else if (!wait) {
    box.innerHTML = `<p class="muted">Для этого прогона дайджест недоступен.</p>`;
  }
  loadRecent();
}

form.onsubmit = async (e) => {
  e.preventDefault();
  const file = $("#file").files[0];
  if (!file) return;
  submitBtn.disabled = true;
  setStatus("Загружаю файл…");
  setProgress(0);
  $("#result").innerHTML = '<p class="muted">Обработка…</p>';
  const data = new FormData();
  data.append("file", file);
  data.append("subject", $("#subject").value || "");
  try {
    const res = await api("/api/runs", { method: "POST", body: data });
    const job = await res.json();
    polling = setTimeout(() => showRun(job.run_id, true), 1000);
  } catch (err) {
    submitBtn.disabled = false;
    setStatus(`<span class="err">Не удалось загрузить: ${err.message}</span>`);
    setProgress(null);
  }
};

loadRecent();
</script>
</body>
</html>
"""
