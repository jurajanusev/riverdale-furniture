"""Use one user-verified browser session to cache protected public product pages."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

import requests

from bs4 import BeautifulSoup
from playwright.sync_api import Error, sync_playwright

from scrapers import SCRAPERS
from scrapers.base import BROWSER_USER_AGENT, browser_profile_dir, write_browser_cache


CHALLENGE_TERMS = (
    "captcha", "verify you are human", "just a moment", "overte, že nie ste robot",
    "access denied", "len chví", "request could not be satisfied", "cf-chl",
)


def is_challenge(page):
    content = (page.title() + " " + page.content()[:20_000]).lower()
    return any(term in content for term in CHALLENGE_TERMS)


def wait_for_verified_html(page, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if not is_challenge(page):
                page.wait_for_timeout(2_000)
                if not is_challenge(page):
                    return page.content()
            page.wait_for_timeout(1_000)
        except Error:
            return None
    return None


def save_status(profile, **status):
    (profile / "riverdale-status.json").write_text(
        json.dumps(status, ensure_ascii=False), encoding="utf-8",
    )


def chrome_executable():
    candidates = (
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    )
    return next((path for path in candidates if path.is_file()), None)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_debugging(port, timeout_seconds=20):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1):
                return True
        except OSError:
            time.sleep(.25)
    return False


def sync_to_cloud(products):
    cloud_url = os.environ.get("RIVERDALE_CLOUD_URL", "").strip().rstrip("/")
    token = os.environ.get("RIVERDALE_SYNC_TOKEN", "").strip()
    if not cloud_url or not token:
        return 0, "Synchronizácia nie je nakonfigurovaná."
    try:
        response = requests.post(
            f"{cloud_url}/api/collector/products",
            headers={"Authorization": f"Bearer {token}"},
            json={"products": products}, timeout=45,
        )
        response.raise_for_status()
        result = response.json()
        return int(result.get("imported", 0)), ""
    except (requests.RequestException, ValueError, TypeError) as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            try:
                detail = exc.response.json().get("error", "")
            except ValueError:
                detail = exc.response.text[:200]
        return 0, detail or str(exc)


def main():
    if len(sys.argv) not in {4, 5}:
        raise SystemExit("Použitie: verify_store.py OBCHOD URL TYP_POLOŽKY [KONTEXT_JSON]")
    store, url, item_type = sys.argv[1:4]
    try:
        context = json.loads(sys.argv[4]) if len(sys.argv) == 5 else {"item_type": item_type}
    except (ValueError, TypeError):
        context = {"item_type": item_type}
    context["item_type"] = item_type
    scraper_class = next((cls for cls in SCRAPERS if cls.store == store), None)
    if not scraper_class:
        raise SystemExit("Neznámy obchod")
    scraper = scraper_class(criteria=context)
    profile = browser_profile_dir(store)
    profile.mkdir(parents=True, exist_ok=True)
    state_path = profile / "riverdale-state.json"
    save_status(profile, state="opening", store=store, cached=0)

    chrome = chrome_executable()
    if not chrome:
        save_status(profile, state="error", store=store, cached=0, error="Google Chrome nebol nájdený")
        return
    port = free_port()
    chrome_profile = profile / "google-chrome"
    chrome_process = subprocess.Popen(
        [str(chrome), f"--remote-debugging-port={port}", f"--user-data-dir={chrome_profile}",
         "--no-first-run", "--no-default-browser-check", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if not wait_for_debugging(port):
        save_status(profile, state="error", store=store, cached=0, error="Google Chrome sa nespustil")
        chrome_process.terminate()
        return

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        context = browser.contexts[0]
        pages = context.pages
        page = next((candidate for candidate in reversed(pages) if candidate.url.startswith("http")), pages[-1])
        try:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            except Error:
                pass
            save_status(profile, state="waiting_for_captcha", store=store, cached=0)
            catalog_html = wait_for_verified_html(page, 600)
            if not catalog_html:
                save_status(profile, state="cancelled", store=store, cached=0)
                return

            context.storage_state(path=str(state_path))
            write_browser_cache(store, url, catalog_html)
            soup = BeautifulSoup(catalog_html, "html.parser")
            product_urls = scraper.product_urls_from_jsonld(soup)
            for link in soup.select("a[href]"):
                product_url = urljoin(url, link.get("href", "")).split("#")[0]
                if scraper.is_product_url(product_url) and product_url not in product_urls:
                    product_urls.append(product_url)
                if len(product_urls) >= scraper.max_product_pages:
                    break

            cached = 0
            save_status(profile, state="caching_products", store=store, cached=0, total=len(product_urls))
            for product_url in product_urls[:scraper.max_product_pages]:
                try:
                    page.goto(product_url, wait_until="domcontentloaded", timeout=60_000)
                except Error:
                    continue
                product_html = wait_for_verified_html(page, 120)
                if not product_html:
                    continue
                write_browser_cache(store, product_url, product_html)
                cached += 1
                context.storage_state(path=str(state_path))
                save_status(profile, state="caching_products", store=store, cached=cached, total=len(product_urls))
            products = scraper.search()
            synced, sync_error = sync_to_cloud(products)
            status = {
                "state": "complete", "store": store, "cached": cached,
                "total": len(product_urls), "found": len(products), "synced": synced,
            }
            if sync_error:
                status["sync_error"] = sync_error
            save_status(profile, **status)
            page.wait_for_timeout(1_500)
        finally:
            try:
                browser.close()
            except Error:
                pass
            if chrome_process.poll() is None:
                chrome_process.terminate()


if __name__ == "__main__":
    main()
