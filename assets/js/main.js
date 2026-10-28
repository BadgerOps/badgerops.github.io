(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('[data-theme-toggle]');
  const menuButton = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-menu]');
  const dialog = document.querySelector('[data-search-dialog]');
  const input = document.querySelector('[data-search-input]');
  const results = document.querySelector('[data-search-results]');
  let searchIndex;

  themeButton?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('badgerops-theme', next);
  });

  menuButton?.addEventListener('click', () => {
    const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!isOpen));
    menu?.classList.toggle('is-open', !isOpen);
  });

  const openSearch = async () => {
    dialog?.showModal();
    document.body.classList.add('dialog-open');
    requestAnimationFrame(() => input?.focus());
    if (!searchIndex) {
      try {
        const response = await fetch(root.dataset.searchIndex);
        searchIndex = await response.json();
      } catch {
        results.innerHTML = '<p class="search-help">The search index could not be loaded. Try the topic index instead.</p>';
      }
    }
  };

  const closeSearch = () => {
    dialog?.close();
    document.body.classList.remove('dialog-open');
  };

  document.querySelectorAll('[data-search-open]').forEach((button) => button.addEventListener('click', openSearch));
  document.querySelector('[data-search-close]')?.addEventListener('click', closeSearch);
  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) closeSearch();
  });
  dialog?.addEventListener('close', () => document.body.classList.remove('dialog-open'));

  document.addEventListener('keydown', (event) => {
    const typing = ['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName);
    if (event.key === '/' && !typing) {
      event.preventDefault();
      openSearch();
    }
  });

  input?.addEventListener('input', () => {
    const query = input.value.trim().toLowerCase();
    if (!query) {
      results.innerHTML = '<p class="search-help">Search titles, topics, summaries, and article text.</p>';
      return;
    }
    if (!searchIndex) return;
    const terms = query.split(/\s+/);
    const matches = searchIndex
      .map((item) => {
        const title = item.title.toLowerCase();
        const topics = (item.topics || []).join(' ').toLowerCase();
        const haystack = `${title} ${topics} ${item.description} ${item.content}`.toLowerCase();
        const score = terms.reduce((total, term) => total + (title.includes(term) ? 5 : 0) + (topics.includes(term) ? 3 : 0) + (haystack.includes(term) ? 1 : 0), 0);
        return { item, score, matches: terms.every((term) => haystack.includes(term)) };
      })
      .filter((result) => result.matches)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8);

    results.innerHTML = matches.length
      ? matches.map(({ item }) => `
          <a class="search-result" href="${item.url}">
            <span>${item.date}${item.topics?.length ? ` · ${item.topics.slice(0, 2).join(' / ')}` : ''}</span>
            <strong>${escapeHtml(item.title)}</strong>
            <p>${escapeHtml(item.description)}</p>
          </a>`).join('')
      : '<p class="search-help">No matching field notes. Try a broader term.</p>';
  });

  function escapeHtml(value = '') {
    const element = document.createElement('div');
    element.textContent = value;
    return element.innerHTML;
  }

  document.querySelectorAll('[data-copy-url]').forEach((button) => {
    button.addEventListener('click', async () => {
      await navigator.clipboard.writeText(location.href);
      const original = button.textContent;
      button.textContent = 'Copied';
      setTimeout(() => { button.textContent = original; }, 1500);
    });
  });

  document.querySelectorAll('.post-content pre').forEach((pre) => {
    const button = document.createElement('button');
    button.className = 'copy-code';
    button.type = 'button';
    button.textContent = 'Copy';
    button.addEventListener('click', async () => {
      await navigator.clipboard.writeText(pre.innerText);
      button.textContent = 'Copied';
      setTimeout(() => { button.textContent = 'Copy'; }, 1200);
    });
    pre.append(button);
  });
})();
