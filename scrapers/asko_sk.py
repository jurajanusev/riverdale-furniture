import re

from .base import BaseScraper


class AskoSlovakiaScraper(BaseScraper):
    store = "ASKO Slovensko"
    catalog_url = "https://www.asko-nabytok.sk/postele"
    allowed_hosts = ("asko-nabytok.sk",)
    seed_urls = (
        "https://www.asko-nabytok.sk/506180.1-postel-saturn-90x200-cm-biela",
        "https://www.asko-nabytok.sk/531548.0-postel-nadja-90x200-cm-biela",
        "https://www.asko-nabytok.sk/4596627.14-postel-so-zasuvkami-carlos-90x200-biela",
    )
    search_url_template = "https://www.asko-nabytok.sk/vyhladavanie?search_text={query}"
    category_urls = {"koberec": "https://www.asko-nabytok.sk/koberce"}

    def product_path_matches(self, url):
        if self.criteria.get("item_type", "posteľ") == "posteľ":
            return "postel-" in url.lower()
        final_slug = url.rstrip("/").rsplit("/", 1)[-1].lower()
        return bool(re.match(r"\d+(?:\.\d+)?-", final_slug))
