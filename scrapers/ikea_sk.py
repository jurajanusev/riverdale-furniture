from .base import BaseScraper


class IkeaSlovakiaScraper(BaseScraper):
    store = "IKEA Slovensko"
    catalog_url = "https://www.ikea.com/sk/sk/cat/postele-bm003/f/postele-90x200-f-typed-reference-measurement--90x200-bed-frames/"
    allowed_hosts = ("ikea.com/sk/sk",)
    seed_urls = ("https://www.ikea.com/sk/sk/p/gullaberg-ram-postele-biela-70608066/",)
    search_url_template = "https://www.ikea.com/sk/sk/search/?q={query}"
    category_urls = {
        "koberec": "https://www.ikea.com/sk/sk/cat/koberce-10653/",
        "komoda": "https://www.ikea.com/sk/sk/cat/komody-10451/",
    }

    def product_path_matches(self, url):
        # Tieto rady sú moderné/minimalistické alebo výsuvné a nespĺňajú brief Betty.
        excluded_slugs = ("/slaekt-", "/vitval-", "/klippuggla-")
        return "/p/" in url and not any(slug in url.lower() for slug in excluded_slugs)
