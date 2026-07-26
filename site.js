(function () {
  const grid = document.querySelector("#materials");
  const query = document.querySelector("#query");
  const tagFilter = document.querySelector("#tag-filter");
  const languageOptions = [...document.querySelectorAll(".language-option")];
  const summary = document.querySelector("#summary");
  const cards = [...document.querySelectorAll(".card")];
  const noResults = document.querySelector("#no-results");
  const clearFilters = document.querySelector("#clear-filters");

  if (!grid || !query || !tagFilter || !summary) return;

  let language = new URLSearchParams(window.location.search).get("lang") || "";
  if (!languageOptions.some((option) => option.dataset.language === language)) language = "";

  const tags = [...new Set(cards.flatMap((card) => (card.dataset.tags || "").split(",").filter(Boolean)))].sort(
    (a, b) => a.localeCompare(b, "es")
  );
  tags.forEach((tag) => {
    const option = document.createElement("option");
    option.value = tag;
    option.textContent = `#${tag}`;
    tagFilter.append(option);
  });

  function setLanguage(nextLanguage) {
    language = nextLanguage;
    languageOptions.forEach((option) => {
      const active = option.dataset.language === language;
      option.classList.toggle("is-active", active);
      option.setAttribute("aria-pressed", String(active));
    });
    const url = new URL(window.location);
    if (language) url.searchParams.set("lang", language);
    else url.searchParams.delete("lang");
    window.history.replaceState({}, "", url);
    render();
  }

  function localizeCard(card) {
    const variants = [...card.querySelectorAll(".variant")];
    variants.forEach((variant) => {
      variant.hidden = Boolean(language) && variant.dataset.language !== language;
    });
    const selected = variants.find((variant) => variant.dataset.language === language)
      || variants.find((variant) => variant.dataset.language === "es")
      || variants[0];
    const title = card.querySelector(".card-title");
    const description = card.querySelector(".card-description");
    if (selected && title) {
      title.href = selected.dataset.html;
      title.childNodes[0].nodeValue = selected.dataset.title;
      title.lang = selected.dataset.language || "";
      if (description) {
        description.textContent = selected.dataset.description;
        description.lang = selected.dataset.language || "";
      }
    }
  }

  function render() {
    const needle = query.value.trim().toLocaleLowerCase().replace(/^#+/, "");
    const tag = tagFilter.value;
    let visible = 0;
    cards.forEach((card) => {
      const languages = (card.dataset.languages || "").split(",").filter(Boolean);
      const matchesText = !needle || (card.dataset.search || "").toLocaleLowerCase().includes(needle);
      const matchesTag = !tag || (card.dataset.tags || "").split(",").includes(tag);
      const matchesLanguage = !language || languages.includes(language);
      const shown = matchesText && matchesTag && matchesLanguage;
      card.hidden = !shown;
      if (shown) {
        localizeCard(card);
        visible += 1;
      }
    });
    summary.textContent = `${visible} material${visible === 1 ? "" : "es"}`;
    if (noResults) noResults.hidden = visible !== 0;
  }

  query.addEventListener("input", render);
  tagFilter.addEventListener("change", render);
  languageOptions.forEach((option) => option.addEventListener("click", () => setLanguage(option.dataset.language)));
  clearFilters?.addEventListener("click", () => {
    query.value = "";
    tagFilter.value = "";
    setLanguage("");
    query.focus();
  });

  setLanguage(language);
}());
