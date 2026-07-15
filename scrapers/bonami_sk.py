from .base import BaseScraper


class BonamiSlovakiaScraper(BaseScraper):
    store = "Bonami Slovensko"
    catalog_url = "https://www.bonami.sk/c/postele/biela/90x200-3"
    allowed_hosts = ("bonami.sk",)
    category_slugs = {
        "posteľ": "postele",
        "nočný stolík": "nocne-stoliky",
        "skriňa": "skrine",
        "komoda": "komody",
        "knižnica": "kniznice-a-police",
        "polica": "police",
        "jedálenský stôl": "jedalenske-stoly",
        "konferenčný stolík": "konferencne-stoliky",
        "pracovný stôl": "pracovne-stoly",
        "písací stôl": "pisacie-stoly",
        "jedálenská stolička": "jedalenske-stolicky",
        "stolička": "stolicky",
        "kreslo": "kresla",
        "pohovka": "pohovky",
        "lavica": "lavice",
        "taburetka": "taburetky",
        "koberec": "koberce",
        "záves": "zavesy",
        "záclona": "zaclony",
        "zrkadlo stojace": "zrkadla",
        "veľké zrkadlo": "zrkadla",
        "stojaca lampa": "stojacie-lampy",
        "stolová lampa": "stolove-lampy",
        "luster": "lustre",
        "váza": "vazy",
        "vankúš": "dekoracne-vankuse",
        "deka": "deky",
    }

    def catalog_url_for_search(self):
        slug = self.category_slugs.get(self.criteria.get("item_type", "posteľ"))
        return f"https://www.bonami.sk/c/{slug}" if slug else ""

    def product_path_matches(self, url):
        return "/p/" in url
