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
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
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
