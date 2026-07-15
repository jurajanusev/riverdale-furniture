const modal = document.querySelector('#product-modal');
document.querySelectorAll('[data-open-modal]').forEach(button => button.addEventListener('click', () => modal.showModal()));
modal?.addEventListener('click', event => { if (event.target === modal) modal.close(); });
const spacesModal = document.querySelector('#spaces-modal');
document.querySelectorAll('[data-open-spaces]').forEach(button => button.addEventListener('click', () => spacesModal.showModal()));
spacesModal?.addEventListener('click', event => { if (event.target === spacesModal) spacesModal.close(); });

const fillSelect = (select, values, preferred) => {
  select.replaceChildren(...values.map(value => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    return option;
  }));
  if (values.includes(preferred)) select.value = preferred;
};

document.querySelectorAll('.context-form').forEach(form => {
  const space = form.querySelector('[data-space-select]');
  const room = form.querySelector('[data-room-select]');
  const category = form.querySelector('[data-category-select]');
  const itemType = form.querySelector('[data-item-type-select]');
  const dimensionCategories = new Set(['nabytok', 'velke-dekoracie', 'textil', 'osvetlenie', 'stavebne-a-fixne-prvky']);
  const updateCriteria = () => {
    form.querySelectorAll('[data-bed-filter]').forEach(field => { field.hidden = itemType.value !== 'posteľ'; });
    form.querySelectorAll('[data-dimension-filter]').forEach(field => { field.hidden = !dimensionCategories.has(category.value); });
  };
  const updateRooms = () => {
    const values = JSON.parse(space.options[space.selectedIndex].dataset.rooms || '[]');
    fillSelect(room, values, room.dataset.current || room.value);
    room.dataset.current = room.value;
  };
  const updateTypes = () => {
    const values = JSON.parse(category.options[category.selectedIndex].dataset.types || '[]');
    fillSelect(itemType, values, itemType.dataset.current || itemType.value);
    itemType.dataset.current = itemType.value;
  };
  space.addEventListener('change', () => { room.dataset.current = ''; updateRooms(); });
  category.addEventListener('change', () => { itemType.dataset.current = ''; updateTypes(); updateCriteria(); });
  itemType.addEventListener('change', updateCriteria);
  updateRooms();
  updateTypes();
  updateCriteria();
});

const searchForm = document.querySelector('.search-form');
const copySearchCriteria = target => {
  if (!searchForm) return;
  for (const field of searchForm.elements) {
    if (!field.name || field.type === 'submit') continue;
    let copy = target.elements.namedItem(field.name);
    if (!copy) {
      copy = document.createElement('input');
      copy.type = 'hidden';
      copy.name = field.name;
      target.append(copy);
    }
    copy.value = field.value;
  }
};

document.querySelectorAll('.captcha-store-form').forEach(form => {
  form.addEventListener('submit', () => copySearchCriteria(form));
});

document.querySelectorAll('[data-local-verify-store]').forEach(link => {
  link.addEventListener('click', () => {
    const params = new URLSearchParams(new FormData(searchForm));
    link.href = `http://127.0.0.1:5000/local-verify-store/${link.dataset.localVerifyStore}?${params}`;
  });
});

document.querySelectorAll('.product-card').forEach(card => {
  const save = async status => {
    const previousStatus = [...card.classList].find(c => c.startsWith('status-'))?.replace('status-', '');
    const response = await fetch(`/api/products/${card.dataset.id}`, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({approval_status: status, notes: card.querySelector('.notes').value})
    });
    if (!response.ok) { alert('Zmenu sa nepodarilo uložiť.'); return; }
    const result = await response.json();
    card.className = `product-card status-${status}`;
    card.querySelector('.status-badge').textContent = result.label;
    const feedback = card.querySelector('.selection-feedback');
    feedback?.classList.toggle('is-visible', status === 'approved');
    if (result.selection_url) feedback?.querySelector('a')?.setAttribute('href', result.selection_url);
    const selectionCount = document.querySelector('[data-selection-count]');
    if (selectionCount && previousStatus !== status) {
      const delta = status === 'approved' ? 1 : previousStatus === 'approved' ? -1 : 0;
      selectionCount.textContent = Math.max(0, Number(selectionCount.textContent) + delta);
    }
  };
  card.querySelectorAll('[data-status]').forEach(button => button.addEventListener('click', () => save(button.dataset.status)));
  card.querySelector('.notes').addEventListener('change', () => {
    const current = [...card.classList].find(c => c.startsWith('status-')).replace('status-', '');
    save(current);
  });
  card.querySelector('[data-delete-product]').addEventListener('click', async () => {
    const name = card.querySelector('h3').textContent.trim();
    const wasApproved = card.classList.contains('status-approved');
    if (!confirm(`Naozaj chcete natrvalo vymazať produkt „${name}“?`)) return;
    const response = await fetch(`/api/products/${card.dataset.id}`, {method: 'DELETE'});
    if (!response.ok) { alert('Produkt sa nepodarilo vymazať.'); return; }
    const group = card.closest('[data-selection-group]');
    card.remove();
    const counter = document.querySelector('.section-heading h2 span');
    if (counter) counter.textContent = Math.max(0, Number(counter.textContent) - 1);
    const selectionCount = document.querySelector('[data-selection-count]');
    if (selectionCount && wasApproved) selectionCount.textContent = Math.max(0, Number(selectionCount.textContent) - 1);
  });
});

document.querySelectorAll('[data-remove-selection]').forEach(button => {
  button.addEventListener('click', async () => {
    const card = button.closest('[data-selection-card]');
    button.disabled = true;
    const response = await fetch(`/api/products/${card.dataset.id}`, {
      method: 'PATCH', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({approval_status: 'unreviewed'})
    });
    if (!response.ok) {
      button.disabled = false;
      alert('Produkt sa nepodarilo odobrať z výberu.');
      return;
    }
    const group = card.closest('[data-selection-group]');
    card.remove();
    const count = document.querySelector('[data-selection-total-count]');
    const price = document.querySelector('[data-selection-total-price]');
    if (count) count.textContent = Math.max(0, Number(count.textContent) - 1);
    if (price) {
      const current = Number(price.textContent.replace('€', '').trim().replace(',', '.')) || 0;
      const next = Math.max(0, current - (Number(card.dataset.price) || 0));
      price.textContent = `${next.toFixed(2).replace('.', ',')} €`;
    }
    const remaining = group?.querySelectorAll('[data-selection-card]').length || 0;
    if (remaining === 0) group?.remove();
    else {
      const badge = group.querySelector('.selection-group-heading > span');
      if (badge) badge.textContent = remaining;
    }
    if (!document.querySelector('[data-selection-card]')) window.location.reload();
  });
});

document.querySelectorAll('[data-copy-share]').forEach(button => {
  button.addEventListener('click', async () => {
    const input = button.parentElement.querySelector('input');
    try {
      await navigator.clipboard.writeText(input.value);
    } catch {
      input.select();
      document.execCommand('copy');
    }
    button.textContent = 'Skopírované';
    setTimeout(() => { button.textContent = 'Kopírovať'; }, 1800);
  });
});
