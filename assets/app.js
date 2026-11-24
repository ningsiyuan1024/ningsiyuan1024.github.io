const search = document.querySelector('#search');
if (search) {
  const category = document.querySelector('#category');
  const entries = [...document.querySelectorAll('.entry')];
  const filter = () => {
    const terms = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const entry of entries) {
      const matchesCategory = !category.value || entry.dataset.categories.split('|').includes(category.value);
      entry.hidden = !matchesCategory || !terms.every(term => entry.dataset.search.toLocaleLowerCase().includes(term));
      if (!entry.hidden) visible++;
    }
    document.querySelector('#no-results').hidden = visible > 0;
  };
  search.addEventListener('input', filter);
  category.addEventListener('change', filter);
}

for (const link of document.querySelectorAll('.entry-image')) {
  const image = link.querySelector('img');
  if (!image || !image.getAttribute('src')?.trim()) {
    link.remove();
    continue;
  }

  const finish = () => {
    if (image.naturalWidth <= 1 || image.naturalHeight <= 1) {
      link.remove();
    } else {
      link.classList.remove('cover-pending');
    }
  };

  link.classList.add('cover-pending');
  image.addEventListener('load', finish, { once: true });
  image.addEventListener('error', () => link.remove(), { once: true });
  if (image.complete) finish();
}
