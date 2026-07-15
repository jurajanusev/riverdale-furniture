from .base import BaseScraper


class MoemaxAustriaScraper(BaseScraper):
    store = "Mömax Rakúsko"
    country = "Rakúsko"
    catalog_url = "https://www.moemax.at/alle-einzelbetten-C30C5C13?p_color=Wei%C3%9F"
    allowed_hosts = ("moemax.at",)
    search_language = "de"
    search_url_template = "https://www.moemax.at/search?q={query}"
    category_urls = {"koberec": "https://www.moemax.at/alle-teppiche-C32C1"}

    def product_path_matches(self, url):
        return "/p/" in url
