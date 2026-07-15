from .base import BaseScraper


class JyskAustriaScraper(BaseScraper):
    store = "JYSK Rakúsko"
    country = "Rakúsko"
    catalog_url = "https://jysk.at/schlafzimmer/betten"
    allowed_hosts = ("jysk.at",)
    search_language = "de"
    search_url_template = "https://jysk.at/search?query={query}"
    category_urls = {
        "koberec": "https://jysk.at/wohnaccessoires/teppiche",
        "komoda": "https://jysk.at/aufbewahrung/kommoden",
    }

    def product_path_matches(self, url):
        low = url.lower()
        if self.criteria.get("item_type", "posteľ") == "posteľ":
            return "bettgestell" in low or "bettrahmen" in low
        final_slug = url.rstrip("/").rsplit("/", 1)[-1].lower()
        return any(token in final_slug for token in self.item_type_tokens())
