const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

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
  if (message?.type !== 'riverdale-start-collection') return false;
  const originTabId = sender.tab?.id;
  if (!originTabId) return false;
  runCollection(message, originTabId)
    .then(() => sendResponse({ok: true}))
    .catch(error => sendResponse({ok: false, error: error.message}));
  return true;
});
