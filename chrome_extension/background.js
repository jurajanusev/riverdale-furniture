const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

const SHOP_TABS = [
  {key: 'ikea-sk', url: 'https://www.ikea.com/sk/sk/', matches: url => url.hostname.includes('ikea.com') && url.pathname.startsWith('/sk/sk/')},
  {key: 'ikea-at', url: 'https://www.ikea.com/at/de/', matches: url => url.hostname.includes('ikea.com') && url.pathname.startsWith('/at/de/')},
  {key: 'jysk-sk', url: 'https://jysk.sk/', matches: url => url.hostname === 'jysk.sk'},
  {key: 'jysk-at', url: 'https://jysk.at/', matches: url => url.hostname === 'jysk.at'},
  {key: 'moebelix-sk', url: 'https://www.moebelix.sk/', matches: url => url.hostname.endsWith('moebelix.sk')},
  {key: 'moebelix-at', url: 'https://www.moebelix.at/', matches: url => url.hostname.endsWith('moebelix.at')},
  {key: 'xxxlutz-sk', url: 'https://www.xxxlutz.sk/', matches: url => url.hostname.endsWith('xxxlutz.sk')},
  {key: 'xxxlutz-at', url: 'https://www.xxxlutz.at/', matches: url => url.hostname.endsWith('xxxlutz.at')},
  {key: 'moemax-at', url: 'https://www.moemax.at/', matches: url => url.hostname.endsWith('moemax.at')},
  {key: 'sconto-sk', url: 'https://www.sconto.sk/', matches: url => url.hostname.endsWith('sconto.sk')},
  {key: 'bonami-sk', url: 'https://www.bonami.sk/', matches: url => url.hostname.endsWith('bonami.sk')},
  {key: 'asko-sk', url: 'https://www.asko-nabytok.sk/', matches: url => url.hostname.endsWith('asko-nabytok.sk')},
  {key: 'favi-sk', url: 'https://favi.sk/', matches: url => url.hostname === 'favi.sk' || url.hostname.endsWith('.favi.sk')}
];

function parsedUrl(value) {
  try { return new URL(value); } catch { return null; }
}

async function groupShopTabs({openMissing = false} = {}) {
  const focused = await chrome.windows.getLastFocused();
  let tabs = await chrome.tabs.query({windowId: focused.id});
  const tabIds = [];
  for (const shop of SHOP_TABS) {
    let tab = tabs.find(candidate => {
      const url = parsedUrl(candidate.url);
      return url && shop.matches(url);
    });
    if (!tab && openMissing) {
      tab = await chrome.tabs.create({windowId: focused.id, url: shop.url, active: false});
      tabs.push(tab);
    }
    if (tab?.id) tabIds.push(tab.id);
  }
  if (!tabIds.length) return;
  const groups = await chrome.tabGroups.query({windowId: focused.id, title: 'Riverdale obchody'});
  const groupId = await chrome.tabs.group({tabIds, ...(groups[0] ? {groupId: groups[0].id} : {})});
  await chrome.tabGroups.update(groupId, {title: 'Riverdale obchody', color: 'green', collapsed: true});
}

chrome.runtime.onInstalled.addListener(() => {
  groupShopTabs({openMissing: true}).catch(() => {});
});

chrome.runtime.onStartup.addListener(() => {
  groupShopTabs().catch(() => {});
});

let activeRun = false;

async function notify(tabId, message, kind = 'info') {
  try {
    await chrome.tabs.sendMessage(tabId, {type: 'riverdale-progress', message, kind});
  } catch { }
}

async function searchPlan(cloudUrl, token, formValues) {
  const response = await fetch(`${cloudUrl}/api/extension/search-plan`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(formValues)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Cloud nepripravil vyhľadávanie.');
  return result;
}

async function waitForTab(tabId) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.status === 'complete') return;
    await wait(500);
  }
}

async function collectStore(tabId, store, originTabId) {
  const started = Date.now();
  let challengeWasShown = false;
  while (Date.now() - started < 10 * 60 * 1000) {
    let result = null;
    try {
      result = await chrome.tabs.sendMessage(tabId, {
        type: 'riverdale-collect-page',
        store: store.store,
        country: store.country,
        searchTerm: store.search_term,
        itemType: store.item_type
      });
    } catch { }

    if (result?.challenge) {
      if (!challengeWasShown) {
        challengeWasShown = true;
        await chrome.tabs.update(tabId, {active: true});
        await notify(originTabId, `${store.store}: vyrieš CAPTCHA v otvorenej karte. Potom budem pokračovať automaticky.`, 'warning');
      }
      await wait(2500);
      continue;
    }
    if (result?.products?.length) return result.products;
    if (Date.now() - started > 30 * 1000) return [];
    await wait(2500);
  }
  return [];
}

async function uploadProducts(cloudUrl, token, products) {
  let imported = 0;
  for (let offset = 0; offset < products.length; offset += 50) {
    const response = await fetch(`${cloudUrl}/api/collector/products`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({products: products.slice(offset, offset + 50)})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Produkty sa nepodarilo odoslať.');
    imported += Number(result.imported || 0);
  }
  return imported;
}

async function configuredRequest(path, options = {}) {
  const {riverdaleConfig} = await chrome.storage.local.get('riverdaleConfig');
  if (!riverdaleConfig?.cloudUrl || !riverdaleConfig?.token) {
    throw new Error('Najprv otvor alebo obnov cloudovú stránku Riverdale.');
  }
  const cloudUrl = riverdaleConfig.cloudUrl.replace(/\/+$/, '');
  let response;
  let result;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    response = await fetch(`${cloudUrl}${path}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${riverdaleConfig.token}`,
        ...(options.body ? {'Content-Type': 'application/json'} : {}),
        ...(options.headers || {})
      }
    });
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      result = await response.json();
      break;
    }
    if (attempt === 0 && [502, 503, 504].includes(response.status)) {
      await wait(1200);
      continue;
    }
    throw new Error('Cloud Riverdale je dočasne nedostupný. Počkajte chvíľu a skúste to znova.');
  }
  if (!result) throw new Error('Cloud Riverdale nevrátil platnú odpoveď. Skúste to znova.');
  if (!response.ok) throw new Error(result.error || 'Riverdale požiadavku odmietol.');
  return {...result, cloudUrl};
}

async function runCollection(message, originTabId) {
  if (activeRun) {
    await notify(originTabId, 'Zber blokovaných obchodov už prebieha.', 'warning');
    return;
  }
  activeRun = true;
  let totalImported = 0;
  try {
    const plan = await searchPlan(message.cloudUrl, message.token, message.formValues);
    await notify(originTabId, `Spúšťam ${plan.stores.length} blokovaných obchodov…`);
    for (let index = 0; index < plan.stores.length; index += 1) {
      const store = plan.stores[index];
      await notify(originTabId, `${index + 1}/${plan.stores.length}: otváram ${store.store}…`);
      const tab = await chrome.tabs.create({url: store.url, active: true});
      try {
        await waitForTab(tab.id);
        const extracted = await collectStore(tab.id, store, originTabId);
        const matching = extracted.filter(product => {
          const price = Number(product.frame_price);
          if (plan.criteria.min_price !== '' && (!price || price < Number(plan.criteria.min_price))) return false;
          if (plan.criteria.max_price !== '' && (!price || price > Number(plan.criteria.max_price))) return false;
          return true;
        });
        const products = matching.map(product => ({
          ...product,
          space_id: plan.criteria.space_id,
          space_name: plan.criteria.space_name,
          room: plan.criteria.room,
          main_category: plan.criteria.main_category,
          item_type: plan.criteria.item_type,
          store: store.store,
          country: store.country
        }));
        if (products.length) {
          const imported = await uploadProducts(message.cloudUrl, message.token, products);
          totalImported += imported;
          await notify(originTabId, `${store.store}: odoslaných ${imported} produktov.`);
        } else {
          await notify(originTabId, `${store.store}: na stránke neboli nájdené zodpovedajúce produkty.`, 'warning');
        }
      } finally {
        try { await chrome.tabs.remove(tab.id); } catch { }
      }
    }
    await notify(originTabId, `Hotovo. Do Riverdale bolo odoslaných ${totalImported} produktov. Obnovujem výsledky…`, 'success');
    await wait(1800);
    await chrome.tabs.reload(originTabId);
  } catch (error) {
    await notify(originTabId, error.message || 'Zber sa nepodarilo dokončiť.', 'error');
  } finally {
    activeRun = false;
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const respond = promise => {
    promise.then(result => sendResponse({ok: true, ...result}))
      .catch(error => sendResponse({ok: false, error: error.message}));
    return true;
  };
  if (message?.type === 'riverdale-configure') {
    return respond(chrome.storage.local.set({
      riverdaleConfig: {cloudUrl: message.cloudUrl, token: message.token, updatedAt: Date.now()}
    }).then(() => ({})));
  }
  if (message?.type === 'riverdale-get-catalog') {
    return respond(configuredRequest('/api/extension/catalog'));
  }
  if (message?.type === 'riverdale-add-product') {
    return respond(configuredRequest('/api/extension/product', {
      method: 'POST', body: JSON.stringify(message.payload)
    }));
  }
  if (message?.type === 'riverdale-start-collection') {
    const originTabId = sender.tab?.id;
    if (!originTabId) return false;
    return respond(
      chrome.storage.local.set({
        riverdaleConfig: {cloudUrl: message.cloudUrl, token: message.token, updatedAt: Date.now()}
      }).then(() => runCollection(message, originTabId)).then(() => ({}))
    );
  }
  return false;
});

chrome.action.onClicked.addListener(async tab => {
  if (!tab?.id) return;
  try {
    let response;
    try {
      response = await chrome.tabs.sendMessage(tab.id, {type: 'riverdale-open-product-dialog'});
    } catch { }
    if (!response?.ok) {
      await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']});
      response = await chrome.tabs.sendMessage(tab.id, {type: 'riverdale-open-product-dialog'});
    }
    if (!response?.ok) throw new Error(response?.error || 'Táto stránka nie je podporovaná produktová stránka.');
  } catch (error) {
    try {
      await chrome.scripting.executeScript({
        target: {tabId: tab.id},
        func: message => window.alert(`Riverdale Collector: ${message}`),
        args: [error.message || 'Produkt sa nepodarilo načítať.']
      });
    } catch { }
  }
});
