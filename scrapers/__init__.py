import os
from concurrent.futures import ThreadPoolExecutor

from .ikea_sk import IkeaSlovakiaScraper
from .ikea_at import IkeaAustriaScraper
from .jysk_sk import JyskSlovakiaScraper
from .jysk_at import JyskAustriaScraper
from .moebelix_sk import MoebelixSlovakiaScraper
from .moebelix_at import MoebelixAustriaScraper
from .sconto_sk import ScontoSlovakiaScraper
from .xxxlutz_sk import XxxlutzSlovakiaScraper
from .xxxlutz_at import XxxlutzAustriaScraper
from .moemax_at import MoemaxAustriaScraper
from .bonami_sk import BonamiSlovakiaScraper
from .asko_sk import AskoSlovakiaScraper
from .favi_sk import FaviSlovakiaScraper


SCRAPERS = [
    IkeaSlovakiaScraper, IkeaAustriaScraper,
    JyskSlovakiaScraper, JyskAustriaScraper,
    MoebelixSlovakiaScraper, MoebelixAustriaScraper,
    XxxlutzSlovakiaScraper, XxxlutzAustriaScraper,
    MoemaxAustriaScraper, ScontoSlovakiaScraper,
    BonamiSlovakiaScraper, AskoSlovakiaScraper,
    FaviSlovakiaScraper,
]


def scraper_error_message(exc):
    """Return a short, user-facing explanation instead of a Playwright traceback."""
    message = " ".join(str(exc).split())
    lowered = message.lower()
    if "executable doesn't exist" in lowered or "playwright install" in lowered:
        return "cloudový prehliadač nie je pripravený"
    if "captcha" in lowered or "manual verification" in lowered:
        return "stránka vyžaduje CAPTCHA alebo manuálne overenie"
    if not message:
        return "neznáma chyba"
    return message[:217] + "..." if len(message) > 220 else message


def search_all(criteria=None):
    def run(scraper_class):
        scraper = scraper_class(criteria=criteria)
        try:
            found = scraper.search()
            if not scraper.catalog_url_for_search():
                message = f"{scraper.store}: kategória zatiaľ nie je podporovaná"
            else:
                message = f"{scraper.store}: {len(found)} vhodných produktov"
            return found, message
        except Exception as exc:
            return [], f"{scraper.store}: nepodarilo sa načítať ({scraper_error_message(exc)})"

    products, messages = [], []
    try:
        worker_count = max(1, min(5, int(os.environ.get("RIVERDALE_SCRAPER_WORKERS", "3"))))
    except ValueError:
        worker_count = 3
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for found, message in executor.map(run, SCRAPERS):
            products.extend(found)
            messages.append(message)
    return products, messages
