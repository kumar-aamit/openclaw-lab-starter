// Example chips fill the form and run it; the response route gets the browser-measured total.
(function () {
  const form = document.querySelector(".review-form");
  if (!form) return;
  const exampleField = form.querySelector('input[name="example"]');

  form.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const inputs = JSON.parse(chip.dataset.inputs || "{}");
      form.querySelectorAll("[data-file-note]").forEach((n) => (n.textContent = ""));
      for (const [name, value] of Object.entries(inputs)) {
        const el = form.elements.namedItem(name);
        if (!el) continue;
        if (el.type === "file") {
          const note = form.querySelector(`[data-file-note="${name}"]`);
          if (note) note.textContent = `Using example file ${value}`;
        } else if (el.type === "checkbox") {
          el.checked = ["on", "true", "yes"].includes(String(value).toLowerCase());
        } else {
          el.value = value;
        }
      }
      exampleField.value = chip.dataset.example;
      htmx.trigger(form, "submit");
    });
  });

  form.addEventListener("input", () => {
    exampleField.value = "";
    form.querySelectorAll("[data-file-note]").forEach((n) => (n.textContent = ""));
  });

  let started = 0;
  document.body.addEventListener("htmx:beforeRequest", () => (started = performance.now()));
  document.body.addEventListener("htmx:afterSwap", (e) => {
    const result = e.detail.target.querySelector(".result");
    if (!result || !started) return;
    const total = (performance.now() - started) / 1000;
    const server = Number(result.dataset.serverMs || 0) / 1000;
    const totalEl = result.querySelector(".route-total");
    if (totalEl) totalEl.textContent = `${total.toFixed(2)} s`;
    const hop = result.querySelector('[data-hop="device"]');
    if (hop) hop.textContent = `${Math.max(total - server, 0).toFixed(2)} s`;
  });
})();
