// Start page: copy the prompt, check a described idea, and reload when a new build goes live.
(function () {
  const page = document.querySelector(".start");
  if (!page) return;
  const box = document.getElementById("prompt");
  const note = page.querySelector(".copy-note");
  const typed = box.tagName === "TEXTAREA";

  function select(el) {
    if (el.select) {
      el.focus();
      el.select();
      return;
    }
    const range = document.createRange();
    range.selectNodeContents(el);
    getSelection().removeAllRanges();
    getSelection().addRange(range);
  }

  page.querySelector(".copy").addEventListener("click", async () => {
    const text = (typed ? box.value : box.textContent).trim();
    if (!text) {
      note.textContent = "Describe your app first.";
      box.focus();
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      note.textContent = "Copied. Paste it into your harness chat.";
    } catch {
      select(box);
      note.textContent = "Selected. Press Cmd+C or Ctrl+C, then paste it into your harness chat.";
    }
  });

  if (typed) {
    const hints = {
      who: /\b(for|by)\s+\w+|\b(analysts?|associates?|technicians?|nurses?|engineers?|officers?|managers?|agents?|clerks?|staff|leads?|investigators?|operators?|lawyers?)\b/i,
      input: /\b(paste|pastes|upload|uploads|enter|enters|attach|attaches|types?|picks?|selects?|submits?)\b/i,
      output: /\b(gets?|returns?|shows?|says|lists?|flags?|scores?|verdict|recommends?|suggests?|drafts?|explains?)\b/i,
    };
    const blocks = {
      score: /\b(score|risk|rating|0 to 100)\b/i,
      table: /\b(table|compare|list of|ranked)\b/i,
      checklist: /\b(steps|checklist|to do|actions|next)\b/i,
    };
    const unsupported = /\b(chart|graph|chat|conversation|image|photo|picture|video|stream)\w*/i;
    const warn = document.getElementById("unsupported");
    box.addEventListener("input", () => {
      const text = box.value;
      for (const [key, re] of Object.entries(hints)) {
        page.querySelector(`[data-hint="${key}"]`).classList.toggle("hint-ok", re.test(text));
      }
      for (const [kind, re] of Object.entries(blocks)) {
        page.querySelector(`.preview-block[data-kind="${kind}"]`).hidden = !re.test(text);
      }
      const word = (text.match(unsupported) || [])[0];
      warn.hidden = !word;
      if (word) warn.textContent = `"${word}" isn't in this version. The harness will offer the closest thing, such as a table instead of a chart.`;
    });
  }

  const commit = page.dataset.commit;
  const timer = setInterval(async () => {
    try {
      const r = await fetch("/api/version", { cache: "no-store" });
      if (!r.ok || (await r.json()).commit === commit) return;
    } catch {
      return;
    }
    if (typed && box.value.trim()) {
      clearInterval(timer);
      note.textContent = "A new build is live. Copy your prompt, then reload this page.";
      return;
    }
    location.reload();
  }, 5000);
})();
