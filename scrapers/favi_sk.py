from .base import BaseScraper


class FaviSlovakiaScraper(BaseScraper):
    store = "FAVI Slovensko"
    catalog_url = "https://favi.sk/produkty/kategorie/postele/90-x-200-cm/biela"
    allowed_hosts = ("favi.sk",)
    max_product_pages = 30
    category_slugs = {
        "posteľ": "postele",
        "nočný stolík": "nocne-stoliky",
        "skriňa": "skrine",
        "komoda": "komody",
        "knižnica": "kniznice",
        "polica": "police",
        "regál": "regaly",
        "stôl": "stoly-a-stoliky",
        "jedálenský stôl": "jedalenske-stoly",
        "konferenčný stolík": "konferencne-stoliky",
        "pracovný stôl": "pracovne-stoly",
        "písací stôl": "pisacie-stoly",
        "toaletný stolík": "toaletne-stoliky",
        "stolička": "stolicky",
        "jedálenská stolička": "jedalenske-stolicky",
        "kreslo": "kresla",
        "pohovka": "pohovky",
        "lavica": "lavice",
        "taburetka": "taburetky",
        "barová stolička": "barove-stolicky",
        "vešiak": "vesiaky",
        "botník": "botniky",
        "paraván": "paravany",
        "zrkadlo stojace": "stojace-zrkadla",
        "veľké zrkadlo": "zrkadla",
        "servírovací vozík": "servirovacie-voziky",
        "vitrína": "vitriny",
        "TV skrinka": "tv-stoliky",
        "koberec": "koberce",
        "záves": "zavesy",
        "záclona": "zaclony",
        "obraz": "obrazy",
        "veľký obraz": "obrazy",
        "malý obraz": "obrazy",
        "nástenná dekorácia": "nastenne-dekoracie",
        "stojaca lampa": "stojacie-lampy",
        "stolová lampa": "stolove-lampy",
        "nočná lampa": "nocne-lampy",
        "luster": "lustre",
        "stropné svietidlo": "stropne-svietidla",
        "nástenné svietidlo": "nastenne-svietidla",
        "váza": "vazy",
        "svietnik": "svietniky",
        "rámik na fotografiu": "ramiky-na-fotografie",
        "miska": "misky",
        "podnos": "podnosy",
        "kvetináč": "kvetinace",
        "vankúš": "vankuse",
        "deka": "deky",
        "obrus": "obrusy",
        "posteľná bielizeň": "postelna-bielizen",
        "hodiny": "hodiny",
        "nástenné hodiny": "nastenne-hodiny",
        "izbová rastlina": "izbove-rastliny",
        "umelá rastlina": "umele-rastliny",
    }

    def catalog_url_for_search(self):
        item_type = self.criteria.get("item_type", "posteľ")
        if item_type == "posteľ":
            return self.catalog_url
        slug = self.category_slugs.get(item_type)
        if not slug:
            return ""
        url = f"https://favi.sk/produkty/kategorie/{slug}"
        if self.criteria.get("color", "").strip().lower() in {"biela", "biely", "white"}:
            url += "/biela"
        return url

    def product_path_matches(self, url):
        return "/produkty/p/" in url

    def parse_product(self, url, html):
        product = super().parse_product(url, html)
        if product:
            product["notes"] = (
                "Zdrojom je produktový detail na FAVI.sk, ktorý môže smerovať "
                "do partnerského obchodu. Pred objednaním overte konečnú cenu, "
                "predajcu a príslušenstvo."
            )
        return product
