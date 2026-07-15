from .base import BaseScraper


class JyskSlovakiaScraper(BaseScraper):
    store = "JYSK Slovensko"
    catalog_url = "https://jysk.sk/spalna/postele"
    allowed_hosts = ("jysk.sk",)
    seed_urls = ("https://jysk.sk/spalna/postele/ramy-postele-rosty-na-postele/postelove-ramy/postelovy-ram-markskel-90x200-biela",)
    search_url_template = "https://jysk.sk/search?query={query}"
    category_urls = {
        "koberec": "https://jysk.sk/domacnost/koberce",
        "komoda": "https://jysk.sk/ulozne-priestory/komody",
    }

    def product_path_matches(self, url):
        # Kategórie obsahujú /postele/, konkrétne slovenské produkty používajú
        # v slugu stabilné označenie postelovy-ram.
        if self.criteria.get("item_type", "posteľ") == "posteľ":
            return "/postelovy-ram" in url
        final_slug = url.rstrip("/").rsplit("/", 1)[-1].lower()
        return any(token in final_slug for token in self.item_type_tokens())
