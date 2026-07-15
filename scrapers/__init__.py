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
            return [], f"{scraper.store}: nepodarilo sa načítať ({exc})"

    products, messages = [], []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for found, message in executor.map(run, SCRAPERS):
            products.extend(found)
            messages.append(message)
    return products, messages
