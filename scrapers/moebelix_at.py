from .base import BaseScraper


class MoebelixAustriaScraper(BaseScraper):
    store = "Möbelix Rakúsko"
    country = "Rakúsko"
    catalog_url = "https://www.moebelix.at/betten-C3C1"
    allowed_hosts = ("moebelix.at",)
    search_language = "de"
    search_url_template = "https://www.moebelix.at/search?q={query}"
    category_urls = {"koberec": "https://www.moebelix.at/teppiche-C37C1"}

    def product_path_matches(self, url):
        return "/p/" in url
