// A small square of the colour before every inline code that is a hex colour, such as
// `#E8590C`, as code editors show them. The swatches on the plot colours page already show
// their colour, so they are skipped.
document.addEventListener("DOMContentLoaded", () => {
  const hex = /^#[0-9A-Fa-f]{6}$/;
  for (const code of document.querySelectorAll("code")) {
    const text = code.textContent.trim();
    if (!hex.test(text) || code.closest(".pytes-swatch, pre")) continue;
    const chip = document.createElement("span");
    chip.className = "pytes-colour-chip";
    chip.style.backgroundColor = text;
    chip.setAttribute("aria-hidden", "true");
    code.prepend(chip);
  }
});
