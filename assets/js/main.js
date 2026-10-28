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
        renderHelp('The search index could not be loaded. Try the topic index instead.');
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
      renderHelp('Search titles, topics, summaries, and article text.');
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

    if (!matches.length) {
      renderHelp('No matching field notes. Try a broader term.');
      return;
    }

    const fragment = document.createDocumentFragment();
    matches.forEach(({ item }) => {
      const link = document.createElement('a');
      const metadata = document.createElement('span');
      const title = document.createElement('strong');
      const description = document.createElement('p');

      link.className = 'search-result';
      link.href = item.url;
      metadata.textContent = `${item.date}${item.topics?.length ? ` · ${item.topics.slice(0, 2).join(' / ')}` : ''}`;
      title.textContent = item.title;
      description.textContent = item.description;
      link.append(metadata, title, description);
      fragment.append(link);
    });
    results.replaceChildren(fragment);
  });

  function renderHelp(message) {
    const help = document.createElement('p');
    help.className = 'search-help';
    help.textContent = message;
    results.replaceChildren(help);
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
