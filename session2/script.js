/* =========================================================
   DECK ENGINE
   -----------------------------------------------------------
   Reads SLIDES (slides.js) and QUIZ (quiz.js), builds the full
   deck (content slides + one slide per quiz question + a
   results slide), and drives navigation, the progress bar,
   the presenter timer, swipe/keyboard input, and printing.
   No build step, no external libraries.
========================================================= */

(function () {
  "use strict";

  /* ---------- Build the full deck ---------- */
  const deckData = [];

  SLIDES.forEach((s) => {
    deckData.push({
      kind: "content",
      duration: s.duration,
      durationText: s.durationText || null,
      html: s.html,
    });
  });

  const firstQuizIndex = deckData.length;

  QUIZ.forEach((q, i) => {
    deckData.push({
      kind: "quiz",
      duration: null,
      durationText: "Quiz",
      quizIndex: i,
      quizData: q,
    });
  });

  const resultsIndex = deckData.length;
  deckData.push({
    kind: "results",
    duration: null,
    durationText: "النتيجة",
  });

  /* ---------- State ---------- */
  let currentIndex = 0;
  let quizState = {}; // { [questionIndex]: boolean(isCorrect) }
  let slideEls = [];

  /* ---------- DOM refs ---------- */
  const deckEl = document.getElementById("deck");
  const progressFill = document.getElementById("progressFill");
  const slideCounter = document.getElementById("slideCounter");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const printBtn = document.getElementById("printBtn");
  const timerWidget = document.getElementById("timerWidget");
  const timerDisplay = document.getElementById("timerDisplay");
  const timerToggle = document.getElementById("timerToggle");
  const timerReset = document.getElementById("timerReset");

  /* =========================================================
     Arabic minute labels (1 / 2 / 3-10 / 11+ have different forms)
  ========================================================= */
  function minutesLabel(n) {
    if (n === 1) return "دقيقة واحدة";
    if (n === 2) return "دقيقتان";
    if (n >= 3 && n <= 10) return n + " دقائق";
    return n + " دقيقة";
  }

  function getBadgeText(slide) {
    if (slide.durationText) return slide.durationText;
    if (typeof slide.duration === "number" && slide.duration > 0) {
      return "⏱ " + minutesLabel(slide.duration);
    }
    return null;
  }

  /* =========================================================
     Quiz slide / results slide markup
  ========================================================= */
  function buildQuizSlideHTML(q, i, total) {
    const options = q.options
      .map((opt, oi) => {
        const letter = String.fromCharCode(65 + oi);
        const isCorrect = oi === q.correctIndex ? "true" : "false";
        return (
          '<button type="button" class="quiz-option" data-oindex="' + oi + '" data-correct="' + isCorrect + '">' +
          '<span class="opt-letter">' + letter + "</span>" +
          '<span class="opt-text">' + opt + "</span>" +
          "</button>"
        );
      })
      .join("");

    return (
      '<div class="slide-inner quiz-question-wrap">' +
      '<span class="slide-eyebrow">Quiz</span>' +
      '<span class="quiz-progress">سؤال ' + (i + 1) + " من " + total + "</span>" +
      '<div class="quiz-q-text">' + q.question + "</div>" +
      '<div class="quiz-options" data-qindex="' + i + '" data-answered="false">' + options + "</div>" +
      '<div class="quiz-feedback" data-feedback></div>' +
      "</div>"
    );
  }

  function buildResultsHTML() {
    const total = QUIZ.length;
    const answered = Object.keys(quizState).length;
    const score = Object.values(quizState).filter(Boolean).length;

    let msg;
    if (answered < total) {
      msg = "أجب عن جميع الأسئلة لعرض نتيجتك النهائية.";
    } else if (score === total) {
      msg = "ممتاز! إجابات كاملة 🎉";
    } else if (score >= Math.ceil(total / 2)) {
      msg = "جيد! يُنصح بمراجعة النقاط التي أخطأت فيها.";
    } else {
      msg = "يُنصح بمراجعة محتوى الجلسة قبل المتابعة.";
    }

    return (
      '<div class="slide-inner quiz-results">' +
      '<span class="slide-eyebrow">Quiz Results</span>' +
      '<h1 class="slide-title">نتيجتك</h1>' +
      '<div class="quiz-score-circle"><span class="score-num">' + score + "/" + total + '</span><span class="score-den en">correct</span></div>' +
      '<p class="slide-desc">' + msg + "</p>" +
      '<button type="button" class="retry-btn ctrl-btn">🔄 إعادة المحاولة</button>' +
      "</div>"
    );
  }

  /* =========================================================
     Render all slides into the DOM once
  ========================================================= */
  function renderDeck() {
    deckEl.innerHTML = "";
    slideEls = deckData.map((slide, i) => {
      const section = document.createElement("section");
      section.className = "slide";
      section.dataset.index = String(i);

      const badgeText = getBadgeText(slide);
      const badgeHTML = badgeText
        ? '<div class="time-badge"><span class="dot"></span>' + badgeText + "</div>"
        : "";

      let bodyHTML;
      if (slide.kind === "quiz") {
        bodyHTML = buildQuizSlideHTML(slide.quizData, slide.quizIndex, QUIZ.length);
      } else if (slide.kind === "results") {
        bodyHTML = buildResultsHTML();
      } else {
        bodyHTML = slide.html;
      }

      section.innerHTML = badgeHTML + bodyHTML;
      deckEl.appendChild(section);
      return section;
    });
  }

  /* =========================================================
     Navigation
  ========================================================= */
  function updateChrome() {
    const total = deckData.length;
    progressFill.style.width = ((currentIndex + 1) / total) * 100 + "%";
    slideCounter.textContent = currentIndex + 1 + " / " + total;
    prevBtn.disabled = currentIndex === 0;
    nextBtn.disabled = currentIndex === total - 1;
  }

  function goTo(newIndex) {
    if (newIndex < 0 || newIndex >= deckData.length || newIndex === currentIndex) return;
    const direction = newIndex > currentIndex ? "next" : "prev";
    const oldEl = slideEls[currentIndex];
    const newEl = slideEls[newIndex];

    if (deckData[newIndex].kind === "results") {
      const badge = newEl.querySelector(".time-badge");
      newEl.innerHTML = (badge ? badge.outerHTML : "") + buildResultsHTML();
    }

    if (direction === "next") {
      newEl.style.setProperty("--enter-x", "40px");
      if (oldEl) oldEl.style.setProperty("--enter-x", "-40px");
    } else {
      newEl.style.setProperty("--enter-x", "-40px");
      if (oldEl) oldEl.style.setProperty("--enter-x", "40px");
    }

    if (oldEl) oldEl.classList.remove("active");

    requestAnimationFrame(() => {
      newEl.classList.add("active");
    });

    currentIndex = newIndex;
    updateChrome();
    setupTimerForSlide(deckData[currentIndex]);
  }

  function next() {
    goTo(currentIndex + 1);
  }
  function prev() {
    goTo(currentIndex - 1);
  }

  /* =========================================================
     Presenter timer
  ========================================================= */
  let timerInterval = null;
  let timerTotal = 0;
  let timerRemaining = 0;
  let timerRunning = false;

  function formatTime(sec) {
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    return m + ":" + s;
  }

  function setupTimerForSlide(slide) {
    clearInterval(timerInterval);
    timerRunning = false;
    timerWidget.classList.remove("warn", "danger");

    if (typeof slide.duration === "number" && slide.duration > 0) {
      timerWidget.classList.remove("disabled");
      timerTotal = slide.duration * 60;
      timerRemaining = timerTotal;
      timerToggle.disabled = false;
      timerToggle.textContent = "ابدأ العداد";
      timerDisplay.textContent = formatTime(timerRemaining);
    } else {
      timerWidget.classList.add("disabled");
      timerToggle.disabled = true;
      timerTotal = 0;
      timerRemaining = 0;
      timerDisplay.textContent = "--:--";
      timerToggle.textContent = "ابدأ العداد";
    }
  }

  function updateTimerDisplay() {
    timerDisplay.textContent = formatTime(timerRemaining);
    const ratio = timerTotal ? timerRemaining / timerTotal : 1;
    timerWidget.classList.remove("warn", "danger");
    if (timerRemaining <= 0) {
      timerWidget.classList.add("danger");
    } else if (ratio <= 0.15 || timerRemaining <= 20) {
      timerWidget.classList.add("danger");
    } else if (ratio <= 0.35) {
      timerWidget.classList.add("warn");
    }
  }

  function startTimer() {
    if (timerTotal === 0) return;
    timerRunning = true;
    timerToggle.textContent = "إيقاف مؤقت";
    timerInterval = setInterval(() => {
      timerRemaining--;
      if (timerRemaining <= 0) {
        timerRemaining = 0;
        updateTimerDisplay();
        clearInterval(timerInterval);
        timerRunning = false;
        timerToggle.textContent = "انتهى الوقت";
        return;
      }
      updateTimerDisplay();
    }, 1000);
  }

  function pauseTimer() {
    timerRunning = false;
    clearInterval(timerInterval);
    timerToggle.textContent = "استئناف";
  }

  function toggleTimer() {
    if (timerTotal === 0) return;
    if (timerRunning) pauseTimer();
    else startTimer();
  }

  function resetTimer() {
    clearInterval(timerInterval);
    timerRunning = false;
    timerRemaining = timerTotal;
    updateTimerDisplay();
    timerWidget.classList.remove("warn", "danger");
    timerToggle.textContent = "ابدأ العداد";
  }

  /* =========================================================
     Quiz interactivity (event delegation)
  ========================================================= */
  function handleQuizOptionClick(optBtn) {
    const wrap = optBtn.closest(".quiz-options");
    if (!wrap || wrap.dataset.answered === "true") return;
    wrap.dataset.answered = "true";

    const qIndex = Number(wrap.dataset.qindex);
    const isCorrect = optBtn.dataset.correct === "true";

    wrap.querySelectorAll(".quiz-option").forEach((btn) => {
      btn.disabled = true;
      if (btn.dataset.correct === "true") btn.classList.add("correct");
    });
    if (!isCorrect) optBtn.classList.add("incorrect");

    quizState[qIndex] = isCorrect;

    const slideEl = wrap.closest(".slide");
    const feedback = slideEl.querySelector("[data-feedback]");
    feedback.classList.add("show", isCorrect ? "ok" : "bad");
    feedback.textContent = isCorrect
      ? "✅ إجابة صحيحة!"
      : "❌ إجابة غير صحيحة — الإجابة الصحيحة موضّحة أعلاه.";
  }

  function handleQuizRetry() {
    quizState = {};
    document.querySelectorAll(".quiz-options").forEach((wrap) => {
      wrap.dataset.answered = "false";
      wrap.querySelectorAll(".quiz-option").forEach((btn) => {
        btn.disabled = false;
        btn.classList.remove("correct", "incorrect");
      });
      const slideEl = wrap.closest(".slide");
      const feedback = slideEl.querySelector("[data-feedback]");
      feedback.classList.remove("show", "ok", "bad");
      feedback.textContent = "";
    });
    goTo(firstQuizIndex);
  }

  deckEl.addEventListener("click", (e) => {
    const optBtn = e.target.closest(".quiz-option");
    if (optBtn) {
      handleQuizOptionClick(optBtn);
      return;
    }
    const retryBtn = e.target.closest(".retry-btn");
    if (retryBtn) {
      handleQuizRetry();
      return;
    }
    const jumpBtn = e.target.closest("[data-jump]");
    if (jumpBtn) {
      e.preventDefault();
      if (jumpBtn.dataset.jump === "quiz") goTo(firstQuizIndex);
    }
  });

  /* =========================================================
     Input: keyboard, buttons, swipe
  ========================================================= */
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      prev();
    } else if (e.key === " " || e.key === "Spacebar") {
      e.preventDefault();
      next();
    } else if (e.key === "Home") {
      e.preventDefault();
      goTo(0);
    } else if (e.key === "End") {
      e.preventDefault();
      goTo(deckData.length - 1);
    }
  });

  prevBtn.addEventListener("click", prev);
  nextBtn.addEventListener("click", next);
  printBtn.addEventListener("click", () => window.print());
  timerToggle.addEventListener("click", toggleTimer);
  timerReset.addEventListener("click", resetTimer);

  let touchStartX = 0;
  let touchStartY = 0;
  deckEl.addEventListener(
    "touchstart",
    (e) => {
      const t = e.changedTouches[0];
      touchStartX = t.clientX;
      touchStartY = t.clientY;
    },
    { passive: true }
  );
  deckEl.addEventListener(
    "touchend",
    (e) => {
      const t = e.changedTouches[0];
      const dx = t.clientX - touchStartX;
      const dy = t.clientY - touchStartY;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        if (dx < 0) next();
        else prev();
      }
    },
    { passive: true }
  );

  /* =========================================================
     Init
  ========================================================= */
  renderDeck();
  if (window.MiniHighlight) window.MiniHighlight.highlightAll(deckEl);
  slideEls[0].classList.add("active");
  updateChrome();
  setupTimerForSlide(deckData[0]);
  deckEl.focus();
})();
