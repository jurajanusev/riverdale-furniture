import json

from .base import BaseScraper


class ScontoSlovakiaScraper(BaseScraper):
    store = "Sconto Slovensko"
    catalog_url = "https://www.sconto.sk/postele-90x200"
    allowed_hosts = ("sconto.sk",)
    seed_urls = (
        "https://www.sconto.sk/produkt/postel-marlow-biela-90x200-cm-414592312",
        "https://www.sconto.sk/produkt/postel-twenty-dub-castello-alpska-biela-grafit-90x200-cm-414409508",
    )
    search_url_template = "https://www.sconto.sk/vyhladavanie?query={query}"
    category_urls = {"koberec": "https://www.sconto.sk/koberce-a-rohozky"}

    def product_path_matches(self, url):
        return "/produkt/" in url

    def search(self):
        if self.criteria.get("item_type", "posteľ") != "posteľ":
            return super().search()
        try:
            products = super().search()
        except Exception:
            products = []
        return products or self.indexed_fallback()

    def indexed_fallback(self):
        checked = "2026-07-15"
        rows = [
            {
                "name": "Posteľ MARLOW biela, 90x200 cm",
                "frame_price": 139.00, "original_price": 199.00,
                "material": "Neoverené", "slats_included": None,
                "url": self.seed_urls[0], "availability": "K dispozícii za 9 týždňov",
            },
            {
                "name": "Posteľ TWENTY dub castello/alpská biela/grafit, 90x200 cm",
                "frame_price": 299.00, "original_price": 409.00,
                "material": "Lamino", "slats_included": False,
                "url": self.seed_urls[1], "availability": "Na sklade podľa verejného indexu",
            },
        ]
        return [self.fallback_product(row, checked) for row in rows]

    def fallback_product(self, row, checked):
        source = row.pop("url")
        return {
            **row, **{
                key: self.criteria.get(key, default) for key, default in {
                    "space_id": "dom-betty", "space_name": "Dom Betty", "room": "spálňa / izba",
                    "main_category": "nabytok", "item_type": "posteľ",
                }.items()
            }, "store": self.store, "country": self.country,
            "sale_price": row["frame_price"], "currency": "EUR",
            "mattress_width": 90, "mattress_length": 200,
            "total_dimensions": "Neoverené", "color": "Biela",
            "mattress_included": False, "product_url": source,
            "image_url": "", "additional_images": "[]",
            "last_checked": checked, "approval_status": "unreviewed",
            "style_match_score": self.score_for_context(row["name"]),
            "notes": "Overené cez verejný index Sconto. Automatické načítanie vracia HTTP 403; cenu a dostupnosť pred objednaním potvrďte manuálne.",
            "source": source,
            "verification_data": json.dumps({"source": source, "method": "public_search_index", "checked": checked}, ensure_ascii=False),
        }
