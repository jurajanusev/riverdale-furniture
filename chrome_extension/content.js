const normalize = value => String(value || '')
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function priceFrom(value) {
  const matches = String(value || '').replace(/\u00a0/g, ' ').match(/\d[\d .]*(?:,\d{1,2})?\s*€/g);
  if (!matches?.length) return null;
  let raw = matches[0].replace('€', '').replace(/\s/g, '');
  if (raw.includes(',')) raw = raw.replace(/\./g, '').replace(',', '.');
  else if (/^\d{1,3}(?:\.\d{3})+$/.test(raw)) raw = raw.replace(/\./g, '');
  const number = Number(raw);
  return Number.isFinite(number) ? number : null;
}

function absoluteUrl(value) {
  try { return new URL(value, location.href).href.split('#')[0]; } catch { return ''; }
}

function isProductUrl(value) {
  const url = absoluteUrl(value);
  if (!url) return false;
  return location.hostname.includes('sconto.sk') ? url.includes('/produkt/') : url.includes('/p/');
}

function productMatches(product, searchTerm, itemType) {
  const haystack = normalize(`${product.name} ${product.product_url}`);
  const preferred = normalize(searchTerm).split(/[^a-z0-9]+/).filter(token => token.length >= 4);
  const fallback = normalize(itemType).split(/[^a-z0-9]+/).filter(token => token.length >= 5);
  const tokens = preferred.length ? preferred : fallback;
  return !tokens.length || tokens.some(token => haystack.includes(token));
}

function jsonLdProducts() {
  const products = [];
  const walk = value => {
    if (Array.isArray(value)) return value.forEach(walk);
    if (!value || typeof value !== 'object') return;
    const kinds = Array.isArray(value['@type']) ? value['@type'] : [value['@type']];
    if (kinds.includes('Product')) {
      const offers = Array.isArray(value.offers) ? value.offers[0] : (value.offers || {});
      const image = Array.isArray(value.image) ? value.image[0] : value.image;
      products.push({
        name: String(value.name || '').trim(),
        product_url: absoluteUrl(value.url || offers.url || ''),
        image_url: absoluteUrl(typeof image === 'object' ? (image.url || image.contentUrl) : image),
        frame_price: Number(offers.price || offers.lowPrice) || null,
        currency: offers.priceCurrency || 'EUR',
        availability: String(offers.availability || '').includes('InStock') ? 'Dostupné' : 'Neoverené'
      });
    }
    Object.values(value).forEach(walk);
  };
  document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
    try { walk(JSON.parse(script.textContent)); } catch { }
  });
  return products;
}

function cardProducts() {
  const products = [];
  document.querySelectorAll('a[href]').forEach(anchor => {
    if (!isProductUrl(anchor.href)) return;
    const card = anchor.closest('article, li, [data-testid*="product"], [class*="product-card"], [class*="productTile"], [class*="product-tile"]') || anchor.parentElement;
    if (!card) return;
    const text = card.innerText || anchor.innerText || '';
    if (text.length > 5000) return;
    const image = card.querySelector('img');
    const heading = card.querySelector('h1, h2, h3, h4, [class*="title"], [class*="name"]');
    const name = String(
      heading?.textContent || anchor.getAttribute('title') || image?.getAttribute('alt') || anchor.textContent || ''
    ).replace(/\s+/g, ' ').trim();
    if (name.length < 3) return;
    products.push({
      name,
      product_url: absoluteUrl(anchor.href),
      image_url: absoluteUrl(image?.currentSrc || image?.src || image?.dataset?.src || ''),
      frame_price: priceFrom(text),
      currency: 'EUR',
      availability: /sklad|dostup|lieferbar|verfügbar/i.test(text) ? 'Dostupné' : 'Neoverené'
    });
  });
  return products;
}

function extractProducts(searchTerm, itemType) {
  const unique = new Map();
  for (const product of [...jsonLdProducts(), ...cardProducts()]) {
    if (!product.name || !isProductUrl(product.product_url)) continue;
    if (!productMatches(product, searchTerm, itemType)) continue;
    unique.set(product.product_url, {
      ...product,
      sale_price: product.frame_price,
      original_price: null,
      total_dimensions: 'Neoverené',
      color: 'Neoverené',
      material: 'Neoverené',
      notes: 'Automaticky zozbierané doplnkom Riverdale Collector. Pred objednaním skontrolujte cenu a dostupnosť.',
      source: product.product_url
    });
    if (unique.size >= 30) break;
  }
  return [...unique.values()];
}

function storeForPage() {
  const host = location.hostname;
  if (host.includes('ikea.com')) return location.pathname.startsWith('/at/de/') ? ['IKEA Rakúsko', 'Rakúsko'] : ['IKEA Slovensko', 'Slovensko'];
  if (host === 'jysk.at') return ['JYSK Rakúsko', 'Rakúsko'];
  if (host === 'jysk.sk') return ['JYSK Slovensko', 'Slovensko'];
  if (host.includes('moebelix.at')) return ['Möbelix Rakúsko', 'Rakúsko'];
  if (host.includes('moebelix.sk')) return ['Möbelix Slovensko', 'Slovensko'];
  if (host.includes('xxxlutz.at')) return ['XXXLutz Rakúsko', 'Rakúsko'];
  if (host.includes('xxxlutz.sk')) return ['XXXLutz Slovensko', 'Slovensko'];
  if (host.includes('moemax.at')) return ['Mömax Rakúsko', 'Rakúsko'];
  if (host.includes('sconto.sk')) return ['Sconto Slovensko', 'Slovensko'];
  if (host.includes('bonami.sk')) return ['Bonami Slovensko', 'Slovensko'];
  if (host.includes('asko-nabytok.sk')) return ['ASKO Slovensko', 'Slovensko'];
  if (host === 'favi.sk' || host.endsWith('.favi.sk')) return ['FAVI Slovensko', 'Slovensko'];
  return [host.replace(/^www\./, ''), 'Iný zdroj'];
}

function isLikelyProductPage() {
  const path = location.pathname;
  if (/\/(p|produkt)\//.test(path) || path.includes('/produkty/p/')) return true;
  if (location.hostname.includes('asko-nabytok.sk') && /\/\d+(?:\.\d+)?-[^/]+\/?$/.test(path)) return true;
  const explicitPrice = document.querySelector('meta[property="product:price:amount"], meta[itemprop="price"], [itemprop="price"][content]');
  if (document.querySelector('h1') && explicitPrice) return true;
  if (document.querySelector('h1') && priceFrom(document.body?.innerText || '')) return true;
  return location.hostname.startsWith('jysk.') && jsonLdProducts().some(product => product.name);
}

function currentProduct() {
  const store = storeForPage();
  if (!store) return null;
  const structured = jsonLdProducts().find(product => product.name) || {};
  const heading = document.querySelector('h1');
  const title = document.querySelector('meta[property="og:title"]');
  const image = document.querySelector('meta[property="og:image"]');
  const canonical = document.querySelector('link[rel="canonical"]');
  const priceMeta = document.querySelector('meta[property="product:price:amount"], meta[itemprop="price"], [itemprop="price"][content]');
  const name = String(structured.name || heading?.textContent || title?.content || '').replace(/\s+/g, ' ').trim();
  if (!name) return null;
  const metaPrice = Number(String(priceMeta?.content || '').replace(',', '.'));
  const framePrice = Number(structured.frame_price) || (Number.isFinite(metaPrice) && metaPrice > 0 ? metaPrice : priceFrom(document.body?.innerText || ''));
  return {
    ...structured,
    name,
    store: store[0],
    country: store[1],
    product_url: absoluteUrl(canonical?.href || location.href),
    image_url: structured.image_url || absoluteUrl(image?.content || document.querySelector('main img')?.currentSrc || ''),
    frame_price: framePrice,
    sale_price: framePrice,
    currency: structured.currency || 'EUR',
    total_dimensions: 'Neoverené',
    color: 'Neoverené',
    material: 'Neoverené',
    notes: 'Pridané z otvorenej produktovej stránky cez Riverdale Collector. Pred objednaním skontrolujte cenu a dostupnosť.',
    source: absoluteUrl(canonical?.href || location.href)
  };
}

function option(value, label, selected = false) {
  const element = document.createElement('option');
  element.value = value;
  element.textContent = label;
  element.selected = selected;
  return element;
}

async function openRiverdaleProductDialog() {
  const product = currentProduct();
  if (!product) {
    progressToast('Na tejto stránke sa nepodarilo rozpoznať produkt.', 'error');
    return;
  }
  progressToast('Načítavam priestory Riverdale…');
  const catalog = await chrome.runtime.sendMessage({type: 'riverdale-get-catalog'});
  if (!catalog?.ok) {
    progressToast(catalog?.error || 'Najprv otvor alebo obnov Riverdale.', 'error');
    return;
  }
  document.querySelector('#riverdale-product-dialog')?.remove();
  const overlay = document.createElement('div');
  overlay.id = 'riverdale-product-dialog';
  overlay.innerHTML = `
    <form>
      <button type="button" data-close aria-label="Zavrieť">×</button>
      <p class="rd-eyebrow">Riverdale Collector</p>
      <h2>Pridať produkt do Riverdale</h2>
      <div class="rd-preview"><img alt=""><div><strong></strong><span></span></div></div>
      <label>Projekt / set<select name="space_id"></select></label>
      <label>Miestnosť<select name="room"></select></label>
      <label>Kategória<select name="main_category"></select></label>
      <label>Typ produktu<select name="item_type"></select></label>
      <label class="rd-check"><input name="approved" type="checkbox"> Rovno schváliť do výberu miestnosti</label>
      <p data-error></p>
      <button class="rd-submit" type="submit">Pridať do Riverdale</button>
    </form>`;
  const style = document.createElement('style');
  style.textContent = `
    #riverdale-product-dialog{position:fixed;inset:0;z-index:2147483647;background:rgba(18,25,21,.68);display:grid;place-items:center;font-family:system-ui,sans-serif}
    #riverdale-product-dialog form{width:min(520px,calc(100vw - 30px));max-height:calc(100vh - 30px);overflow:auto;background:#fffdf8;color:#27332d;padding:28px;box-shadow:0 24px 80px rgba(0,0,0,.35);position:relative}
    #riverdale-product-dialog [data-close]{position:absolute;right:15px;top:10px;border:0;background:none;font-size:28px;cursor:pointer}
    #riverdale-product-dialog h2{font:28px Georgia,serif;margin:0 0 18px}.rd-eyebrow{color:#a8782f;text-transform:uppercase;letter-spacing:.15em;font-size:11px;font-weight:700}
    #riverdale-product-dialog label{display:block;margin:12px 0;font-size:12px;font-weight:700;text-transform:uppercase;color:#68736c}
    #riverdale-product-dialog select{display:block;width:100%;margin-top:6px;padding:10px;border:1px solid #cbc9c1;background:white;color:#27332d}
    #riverdale-product-dialog .rd-check{display:flex;gap:9px;align-items:center;text-transform:none}.rd-check input{width:auto}
    #riverdale-product-dialog .rd-submit{width:100%;border:0;padding:12px;background:#c49a55;color:#1d261f;font-weight:800;cursor:pointer}
    .rd-preview{display:flex;gap:14px;align-items:center;background:#f5f1e9;padding:12px}.rd-preview img{width:74px;height:74px;object-fit:cover;background:#ddd}.rd-preview strong,.rd-preview span{display:block}.rd-preview span{margin-top:5px;color:#68736c}
    #riverdale-product-dialog [data-error]{color:#9c4a42;font-size:13px}`;
  overlay.append(style);
  document.body.append(overlay);

  const form = overlay.querySelector('form');
  const spaceSelect = form.elements.space_id;
  const roomSelect = form.elements.room;
  const categorySelect = form.elements.main_category;
  const typeSelect = form.elements.item_type;
  const previewImage = form.querySelector('.rd-preview img');
  previewImage.src = product.image_url || '';
  previewImage.hidden = !product.image_url;
  form.querySelector('.rd-preview strong').textContent = product.name;
  form.querySelector('.rd-preview span').textContent = `${product.store}${product.frame_price ? ` · ${product.frame_price.toFixed(2)} €` : ''}`;
  const {lastAssignment = {}} = await chrome.storage.local.get('lastAssignment');
  catalog.spaces.forEach(space => spaceSelect.append(option(space.id, space.name, space.id === lastAssignment.space_id)));
  catalog.categories.forEach(category => categorySelect.append(option(category.id, category.name, category.id === lastAssignment.main_category)));
  const updateRooms = () => {
    const space = catalog.spaces.find(value => value.id === spaceSelect.value);
    roomSelect.replaceChildren(...space.rooms.map(room => option(room, room, room === lastAssignment.room)));
  };
  const updateTypes = () => {
    const category = catalog.categories.find(value => value.id === categorySelect.value);
    typeSelect.replaceChildren(...category.types.map(type => option(type, type, type === lastAssignment.item_type)));
  };
  spaceSelect.addEventListener('change', () => { lastAssignment.room = ''; updateRooms(); });
  categorySelect.addEventListener('change', () => { lastAssignment.item_type = ''; updateTypes(); });
  updateRooms(); updateTypes();
  form.querySelector('[data-close]').addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', event => { if (event.target === overlay) overlay.remove(); });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const submit = form.querySelector('.rd-submit');
    submit.disabled = true;
    submit.textContent = 'Ukladám…';
    const assignment = {
      space_id: spaceSelect.value, room: roomSelect.value,
      main_category: categorySelect.value, item_type: typeSelect.value
    };
    const result = await chrome.runtime.sendMessage({
      type: 'riverdale-add-product',
      payload: {product, assignment, approved: form.elements.approved.checked}
    });
    if (!result?.ok) {
      form.querySelector('[data-error]').textContent = result?.error || 'Produkt sa nepodarilo uložiť.';
      submit.disabled = false; submit.textContent = 'Pridať do Riverdale';
      return;
    }
    await chrome.storage.local.set({lastAssignment: assignment});
    form.innerHTML = `<p class="rd-eyebrow">Riverdale Collector</p><h2>Produkt bol pridaný</h2><p>${result.destination}</p><button class="rd-submit" type="button">Otvoriť v Riverdale</button>`;
    form.querySelector('.rd-submit').addEventListener('click', () => window.open(new URL(result.selection_url, result.cloudUrl).href, '_blank'));
  });
}

function addManualProductButton() {
  if (!storeForPage() || !isLikelyProductPage() || document.querySelector('#riverdale-add-product')) return;
  const button = document.createElement('button');
  button.id = 'riverdale-add-product';
  button.type = 'button';
  button.textContent = '+ Pridať do Riverdale';
  Object.assign(button.style, {
    position: 'fixed', left: '20px', bottom: '20px', zIndex: '2147483646',
    border: '1px solid #fff', borderRadius: '4px', padding: '13px 17px',
    background: '#304b3d', color: '#fff', font: '700 14px system-ui,sans-serif',
    boxShadow: '0 10px 30px rgba(0,0,0,.28)', cursor: 'pointer'
  });
  button.addEventListener('click', () => openRiverdaleProductDialog().catch(error => progressToast(error.message, 'error')));
  document.body.append(button);
}

function challengeVisible() {
  const text = normalize(`${document.title} ${(document.body?.innerText || '').slice(0, 12000)}`);
  return [
    'captcha', 'verify you are human', 'are you a human', 'overte ze nie ste robot',
    'access denied', 'just a moment', 'pardon our interruption', 'press and hold',
    'security check', 'sicherheitsprufung', 'roboter', 'cf-chl'
  ]
    .some(term => text.includes(term));
}

function progressToast(message, kind = 'info') {
  let toast = document.querySelector('#riverdale-extension-progress');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'riverdale-extension-progress';
    Object.assign(toast.style, {
      position: 'fixed', right: '20px', bottom: '20px', zIndex: '2147483647',
      maxWidth: '440px', padding: '16px 18px', borderRadius: '4px',
      color: '#fff', font: '600 14px/1.45 system-ui, sans-serif',
      boxShadow: '0 12px 40px rgba(0,0,0,.3)'
    });
    document.body.append(toast);
  }
  const colors = {info: '#304b3d', warning: '#8a6715', success: '#397242', error: '#9c4a42'};
  toast.style.background = colors[kind] || colors.info;
  toast.textContent = message;
}

if (location.hostname === 'riverdale-furniture.onrender.com') {
  document.documentElement.dataset.riverdaleCollector = 'ready';
  const collectorButton = document.querySelector('[data-extension-collect]');
  if (collectorButton) {
    chrome.runtime.sendMessage({
      type: 'riverdale-configure',
      cloudUrl: collectorButton.dataset.cloudUrl,
      token: collectorButton.dataset.collectorToken
    });
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-extension-collect]');
    if (!button) return;
    event.preventDefault();
    const form = document.querySelector('.search-form');
    if (!form) return;
    button.disabled = true;
    progressToast('Pripravujem automatický zber blokovaných obchodov…');
    chrome.runtime.sendMessage({
      type: 'riverdale-start-collection',
      cloudUrl: button.dataset.cloudUrl,
      token: button.dataset.collectorToken,
      formValues: Object.fromEntries(new FormData(form).entries())
    }).catch(error => progressToast(error.message || 'Doplnok sa nepodarilo spustiť.', 'error'))
      .finally(() => { button.disabled = false; });
  });
} else {
  addManualProductButton();
  setTimeout(addManualProductButton, 2500);
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'riverdale-open-product-dialog') {
    if (!storeForPage() || !isLikelyProductPage()) {
      sendResponse({ok: false, error: 'Otvorte konkrétnu produktovú stránku podporovaného obchodu.'});
      return false;
    }
    addManualProductButton();
    openRiverdaleProductDialog()
      .then(() => sendResponse({ok: true}))
      .catch(error => sendResponse({ok: false, error: error.message}));
    return true;
  }
  if (message?.type === 'riverdale-progress') {
    progressToast(message.message, message.kind);
    sendResponse({ok: true});
    return false;
  }
  if (message?.type === 'riverdale-collect-page') {
    sendResponse({
      challenge: challengeVisible(),
      products: challengeVisible() ? [] : extractProducts(message.searchTerm, message.itemType)
    });
    return false;
  }
  return false;
});
