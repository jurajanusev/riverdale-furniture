from .base import BaseScraper


class IkeaAustriaScraper(BaseScraper):
    store = "IKEA Rakúsko"
    country = "Rakúsko"
    catalog_url = "https://www.ikea.com/at/de/cat/betten-bm003/f/betten-90x200-f-typed-reference-measurement--90x200-bed-frames/"
    allowed_hosts = ("ikea.com/at/de",)
    seed_urls = (
        "https://www.ikea.com/at/de/p/gullaberg-bettgestell-weiss-70608066/",
        "https://www.ikea.com/at/de/p/vihals-bettgestell-weiss-40602424/",
        "https://www.ikea.com/at/de/p/tarva-bettgestell-weiss-las-00586204/",
    )
    search_language = "de"
    search_url_template = "https://www.ikea.com/at/de/search/?q={query}"
    category_urls = {
        "koberec": "https://www.ikea.com/at/de/cat/teppiche-10653/",
        "komoda": "https://www.ikea.com/at/de/cat/kommoden-10451/",
    }

    def product_path_matches(self, url):
        excluded = ("/slaekt-", "/vitval-", "/tuffing-", "/kura-", "/smastad-", "/klippuggla-")
        return "/p/" in url and not any(value in url.lower() for value in excluded)
