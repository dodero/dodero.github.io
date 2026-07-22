(function () {
  const grid = document.querySelector("#materials");
  const query = document.querySelector("#query");
  const tagFilter = document.querySelector("#tag-filter");
  const summary = document.querySelector("#summary");
  const cards = [...document.querySelectorAll(".card")];

  if (!grid || !query || !tagFilter || !summary) return;

  const tags = [...new Set(cards.flatMap((card) => (card.dataset.tags || "").split(",").filter(Boolean)))].sort();
  tags.forEach((tag) => {
    const option = document.createElement("option");
    option.value = tag;
    option.textContent = `#${tag}`;
    tagFilter.append(option);
  });

  function render() {
    const needle = query.value.trim().toLocaleLowerCase().replace(/^#+/, "");
    const tag = tagFilter.value;
    let visible = 0;
    cards.forEach((card) => {
      const matchesText = !needle || (card.dataset.search || "").toLocaleLowerCase().includes(needle);
      const matchesTag = !tag || (card.dataset.tags || "").split(",").includes(tag);
      const shown = matchesText && matchesTag;
      card.hidden = !shown;
      if (shown) visible += 1;
    });
    summary.textContent = `${visible} material${visible === 1 ? "" : "es"}`;
  }

  query.addEventListener("input", render);
  tagFilter.addEventListener("change", render);
}());
