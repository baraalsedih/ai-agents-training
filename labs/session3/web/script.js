// Session 3 knowledge base — local web UI
// Talks to the Flask endpoints in webapp.py, no build step, no framework.
// The backend (webapp.py / ingest.py / ask.py / report.py) works with raw,
// language-neutral category keys (idea/decision/evidence/open_question).
// This file is the only place that translates them to Arabic for display,
// since this page is the trainee-facing interface and the documents are Arabic.

const CATEGORY_LABELS_AR = {
  idea: "فكرة",
  decision: "قرار",
  evidence: "دليل",
  open_question: "سؤال مفتوح",
  unclassified: "غير مصنف",
};

function categoryLabel(key) {
  return CATEGORY_LABELS_AR[key] || key;
}

const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanels = document.querySelectorAll(".tab-panel");

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabButtons.forEach((b) => b.classList.remove("active"));
    tabPanels.forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `فشل الطلب (${res.status})`);
  return data;
}

// ---------- Populate category filter dropdown ----------
(async () => {
  try {
    const categories = await fetchJSON("/api/categories");
    const select = document.getElementById("filterSelect");
    categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.value;
      opt.textContent = categoryLabel(c.value);
      select.appendChild(opt);
    });
  } catch (e) {
    // Non-fatal — the "كل الفئات" option still works.
  }
})();

// ---------- ASK TAB ----------
const questionInput = document.getElementById("questionInput");
const filterSelect = document.getElementById("filterSelect");
const askBtn = document.getElementById("askBtn");
const askStatus = document.getElementById("askStatus");
const askResult = document.getElementById("askResult");
const answerText = document.getElementById("answerText");
const sourcesList = document.getElementById("sourcesList");

async function runAsk() {
  const question = questionInput.value.trim();
  if (!question) return;

  askBtn.disabled = true;
  askStatus.className = "status";
  askStatus.textContent = "جارٍ البحث في أرشيفك وتوليد الإجابة...";
  askResult.style.display = "none";

  try {
    const data = await fetchJSON("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, filter: filterSelect.value || null }),
    });

    if (!data.found) {
      askStatus.className = "status error";
      askStatus.textContent = "لم يتم العثور على مقاطع ذات صلة بهذا السؤال.";
      return;
    }

    askStatus.textContent = "";
    answerText.textContent = data.answer;
    sourcesList.innerHTML = "";
    data.sources.forEach((s) => {
      const li = document.createElement("li");
      li.dir = "auto";
      li.innerHTML = `<span class="src-file">${escapeHTML(s.source)}</span><span class="src-cat">${escapeHTML(categoryLabel(s.category))}</span><span class="src-summary">${escapeHTML(s.summary)}</span>`;
      sourcesList.appendChild(li);
    });
    askResult.style.display = "block";
  } catch (e) {
    askStatus.className = "status error";
    askStatus.textContent = `خطأ: ${e.message}`;
  } finally {
    askBtn.disabled = false;
  }
}

askBtn.addEventListener("click", runAsk);
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runAsk();
});

// ---------- INGEST TAB ----------
const checkBtn = document.getElementById("checkBtn");
const runBtn = document.getElementById("runBtn");
const ingestPreview = document.getElementById("ingestPreview");
const ingestStatus = document.getElementById("ingestStatus");
const ingestLog = document.getElementById("ingestLog");
const ingestSummary = document.getElementById("ingestSummary");

checkBtn.addEventListener("click", async () => {
  checkBtn.disabled = true;
  ingestStatus.className = "status";
  ingestStatus.textContent = "جارٍ فحص مجلد المستندات...";
  ingestPreview.style.display = "none";
  runBtn.disabled = true;

  try {
    const data = await fetchJSON("/api/ingest/preview");
    ingestStatus.textContent = "";

    if (data.upToDate) {
      ingestPreview.style.display = "block";
      ingestPreview.textContent = `✅ كل شيء محدَّث (${data.totalFiles} ملف مفهرس).`;
      return;
    }

    const mins = Math.floor(data.estimatedSeconds / 60);
    const secs = data.estimatedSeconds % 60;
    ingestPreview.style.display = "block";
    ingestPreview.innerHTML = `
      <div><strong>ملفات جديدة/معدَّلة:</strong> ${data.toProcess.length}</div>
      <div dir="auto" style="margin:4px 0;">${data.toProcess.map(escapeHTML).join("، ") || "—"}</div>
      <div><strong>ملفات محذوفة:</strong> ${data.removed.length}</div>
      <div><strong>عدد المقاطع المقدَّر للتصنيف:</strong> ${data.estimatedChunks}</div>
      <div><strong>الوقت المقدَّر:</strong> ~${mins} د ${secs} ث</div>
    `;
    runBtn.disabled = false;
  } catch (e) {
    ingestStatus.className = "status error";
    ingestStatus.textContent = `خطأ: ${e.message}`;
  } finally {
    checkBtn.disabled = false;
  }
});

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  checkBtn.disabled = true;
  ingestStatus.className = "status";
  ingestStatus.textContent = "جارٍ بناء قاعدة المعرفة — قد يستغرق هذا بضع دقائق...";
  ingestLog.style.display = "none";
  ingestSummary.style.display = "none";

  try {
    const data = await fetchJSON("/api/ingest/run", { method: "POST" });
    ingestStatus.className = "status ok";
    ingestStatus.textContent = data.message ? "لا يوجد جديد — محدَّث بالفعل." : "اكتمل البناء.";

    if (data.log && data.log.length) {
      ingestLog.style.display = "block";
      ingestLog.innerHTML = data.log.map((l) => `<div dir="auto">${escapeHTML(l)}</div>`).join("");
      ingestLog.scrollTop = ingestLog.scrollHeight;
    }

    if (data.counts && Object.keys(data.counts).length) {
      ingestSummary.style.display = "block";
      ingestSummary.innerHTML =
        "<h3>ملخص التصنيف</h3>" +
        Object.entries(data.counts)
          .map(([label, n]) => `<div class="count-row"><span class="label">${escapeHTML(label)}</span><span class="value">${n}</span></div>`)
          .join("");
    }
  } catch (e) {
    ingestStatus.className = "status error";
    ingestStatus.textContent = `خطأ: ${e.message}`;
  } finally {
    runBtn.disabled = true; // re-enabled only after a fresh "check for changes"
    checkBtn.disabled = false;
  }
});

// ---------- REPORT TAB ----------
const reportBtn = document.getElementById("reportBtn");
const reportStatus = document.getElementById("reportStatus");
const reportResult = document.getElementById("reportResult");

reportBtn.addEventListener("click", async () => {
  reportBtn.disabled = true;
  reportStatus.className = "status";
  reportStatus.textContent = "جارٍ تحميل التقرير...";
  reportResult.style.display = "none";

  try {
    const data = await fetchJSON("/api/report");
    reportStatus.textContent = "";

    if (data.empty) {
      reportResult.style.display = "block";
      reportResult.textContent = "قاعدة المعرفة فارغة — لا مقاطع مفهرسة بعد.";
      return;
    }

    reportResult.style.display = "block";
    reportResult.innerHTML = renderReport(data);
  } catch (e) {
    reportStatus.className = "status error";
    reportStatus.textContent = `خطأ: ${e.message}`;
  } finally {
    reportBtn.disabled = false;
  }
});

function renderReport(data) {
  let html = `<div class="report-section"><strong>إجمالي المقاطع المفهرسة:</strong> ${data.total}</div>`;

  html += `<div class="report-section"><h3>التوزيع حسب الفئة</h3>`;
  html += Object.entries(data.counts)
    .map(([cat, n]) => `<div class="count-row"><span class="label">${escapeHTML(categoryLabel(cat))}</span><span class="value">${n}</span></div>`)
    .join("");
  html += `</div>`;

  html += `<div class="report-section"><h3>التوزيع حسب الملف المصدر</h3>`;
  html += Object.entries(data.by_source)
    .map(([src, n]) => `<div class="count-row" dir="auto"><span class="label">${escapeHTML(src)}</span><span class="value">${n}</span></div>`)
    .join("");
  html += `</div>`;

  html += `<div class="report-section"><h3>الأسئلة المفتوحة</h3>`;
  html += renderGroupedList(data.open_questions, "لا توجد أسئلة مفتوحة مصنّفة بعد.");
  html += `</div>`;

  html += `<div class="report-section"><h3>القرارات</h3>`;
  html += renderGroupedList(data.decisions, "لا توجد قرارات مصنّفة بعد.");
  html += `</div>`;

  return html;
}

function renderGroupedList(grouped, emptyMessage) {
  const sources = Object.keys(grouped);
  if (sources.length === 0) return `<p class="hint">${emptyMessage}</p>`;
  return sources
    .map(
      (src) => `
      <div class="report-source-group" dir="auto">
        <h4>${escapeHTML(src)}</h4>
        <ul>${grouped[src].map((s) => `<li>${escapeHTML(s)}</li>`).join("")}</ul>
      </div>`
    )
    .join("");
}

function escapeHTML(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}
