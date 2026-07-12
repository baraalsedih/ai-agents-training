/* =========================================================
   MINI SYNTAX HIGHLIGHTER — no external library, no CDN.
   -----------------------------------------------------------
   Small regex-based tokenizer for the three languages used in
   this deck's code blocks: python, bash, json. Good enough for
   short teaching snippets — not a general-purpose highlighter.
   Runs once after the deck is rendered (see script.js).
========================================================= */

(function () {
  "use strict";

  const PY_KEYWORDS = /\b(def|class|return|import|from|as|if|elif|else|for|while|in|not|and|or|is|None|True|False|try|except|finally|raise|with|yield|lambda|pass|break|continue|async|await|global)\b/g;
  const BASH_KEYWORDS = /\b(source|export|cd|if|then|fi|do|done|for|while|echo|activate)\b/g;

  function escapeHTML(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /* Tokenize a single line by scanning left-to-right so string/comment
     spans are never re-matched by the keyword/number passes. */
  function highlightLine(line, lang) {
    const tokens = [];
    let i = 0;
    const n = line.length;

    const commentChar = lang === "python" || lang === "bash" ? "#" : null;

    while (i < n) {
      const ch = line[i];

      // comment: rest of line
      if (commentChar && ch === commentChar) {
        tokens.push({ text: line.slice(i), cls: "tok-com" });
        break;
      }
      if (lang === "json" && ch === "/" && line[i + 1] === "/") {
        tokens.push({ text: line.slice(i), cls: "tok-com" });
        break;
      }

      // string literal: ' " or f'/f"
      if (ch === '"' || ch === "'") {
        const quote = ch;
        let j = i + 1;
        while (j < n && line[j] !== quote) {
          if (line[j] === "\\") j++;
          j++;
        }
        j = Math.min(j + 1, n);
        tokens.push({ text: line.slice(i, j), cls: "tok-str" });
        i = j;
        continue;
      }
      if (ch === "f" && (line[i + 1] === '"' || line[i + 1] === "'")) {
        const quote = line[i + 1];
        let j = i + 2;
        while (j < n && line[j] !== quote) {
          if (line[j] === "\\") j++;
          j++;
        }
        j = Math.min(j + 1, n);
        tokens.push({ text: line.slice(i, j), cls: "tok-str" });
        i = j;
        continue;
      }

      // decorator @tool
      if (ch === "@" && /[A-Za-z_]/.test(line[i + 1] || "")) {
        let j = i + 1;
        while (j < n && /[A-Za-z0-9_.]/.test(line[j])) j++;
        tokens.push({ text: line.slice(i, j), cls: "tok-dec" });
        i = j;
        continue;
      }

      // number
      if (/[0-9]/.test(ch) && (i === 0 || !/[A-Za-z_]/.test(line[i - 1]))) {
        let j = i;
        while (j < n && /[0-9._]/.test(line[j])) j++;
        tokens.push({ text: line.slice(i, j), cls: "tok-num" });
        i = j;
        continue;
      }

      // identifier / keyword / function call / class name
      if (/[A-Za-z_]/.test(ch)) {
        let j = i;
        while (j < n && /[A-Za-z0-9_]/.test(line[j])) j++;
        const word = line.slice(i, j);
        const isKw =
          (lang === "python" && new RegExp("^(" + PY_KEYWORDS.source.slice(2, -2) + ")$").test(word)) ||
          (lang === "bash" && new RegExp("^(" + BASH_KEYWORDS.source.slice(2, -2) + ")$").test(word));
        const nextNonSpace = line.slice(j).match(/^\s*\(/);
        const prevWord = line.slice(0, i).trimEnd();
        const isClass = /\b(class)\s*$/.test(prevWord) || (/^[A-Z]/.test(word) && nextNonSpace === null && /[A-Z][a-z]/.test(word));
        if (isKw) {
          tokens.push({ text: word, cls: "tok-kw" });
        } else if (nextNonSpace && !isKw) {
          tokens.push({ text: word, cls: "tok-fn" });
        } else if (isClass) {
          tokens.push({ text: word, cls: "tok-cls" });
        } else {
          tokens.push({ text: word, cls: null });
        }
        i = j;
        continue;
      }

      // operators / arrows
      if ("=<>!+-*/%&|:.,()[]{}".includes(ch)) {
        let j = i + 1;
        if ("=<>-".includes(ch) && line[j] === ">") j++;
        else if (ch === "=" && line[j] === "=") j++;
        tokens.push({ text: line.slice(i, j), cls: "tok-op" });
        i = j;
        continue;
      }

      tokens.push({ text: ch, cls: null });
      i++;
    }

    return tokens
      .map((t) => (t.cls ? '<span class="' + t.cls + '">' + escapeHTML(t.text) + "</span>" : escapeHTML(t.text)))
      .join("");
  }

  function highlightBlock(codeEl) {
    const lang = (codeEl.className.match(/language-(\w+)/) || [, "text"])[1];
    const raw = codeEl.textContent.replace(/\n$/, "");
    const lines = raw.split("\n");
    codeEl.innerHTML = lines.map((l) => highlightLine(l, lang)).join("\n");
  }

  function highlightAll(root) {
    (root || document).querySelectorAll("code[class*='language-']").forEach(highlightBlock);
  }

  window.MiniHighlight = { highlightAll };
})();
