const search = document.querySelector('#search');
if (search) {
  const entries = [...document.querySelectorAll('.entry')];
  search.addEventListener('input', () => {
    const terms = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const entry of entries) {
      entry.hidden = !terms.every(term => entry.dataset.search.toLocaleLowerCase().includes(term));
      if (!entry.hidden) visible++;
    }
    document.querySelector('#no-results').hidden = visible > 0;
  });
}
