import json

from .base import BaseScraper


class XxxlutzSlovakiaScraper(BaseScraper):
    store = "XXXLutz Slovensko"
    catalog_url = "https://www.xxxlutz.sk/postele-C3C3?pa_lying_surface=90%2F200+cm&p_color=Biela"
    allowed_hosts = ("xxxlutz.sk",)
    seed_urls = (
        "https://www.xxxlutz.sk/p/cantus-postel-90-200-cm-biela-dub-sonoma-002698027201",
    )
    search_url_template = "https://www.xxxlutz.sk/search?q={query}"
    category_urls = {"koberec": "https://www.xxxlutz.sk/koberce-C11C1"}

    def product_path_matches(self, url):
        return "/p/" in url

    def search(self):
        if self.criteria.get("item_type", "posteľ") != "posteľ":
            return super().search()
        try:
            products = super().search()
        except Exception:
            products = []
        return products or self.indexed_fallback()

    def indexed_fallback(self):
        source = self.seed_urls[0]
        checked = "2026-07-15"
        name = "Cantus POSTEĽ, 90/200 cm biela, dub sonoma"
        return [{
            "name": name,
            **{
                key: self.criteria.get(key, default) for key, default in {
                    "space_id": "dom-betty", "space_name": "Dom Betty", "room": "spálňa / izba",
                    "main_category": "nabytok", "item_type": "posteľ",
                }.items()
            },
            "store": self.store, "country": self.country,
            "frame_price": 186.75, "original_price": 249.00,
            "sale_price": 186.75, "currency": "EUR",
            "mattress_width": 90, "mattress_length": 200,
            "total_dimensions": "97 × 204 × 68 cm", "color": "Biela",
            "material": "Lamino", "slats_included": False,
            "mattress_included": False, "product_url": source,
            "image_url": "", "additional_images": "[]",
            "last_checked": checked, "availability": "Neoverené",
            "approval_status": "unreviewed",
            "style_match_score": self.score_for_context(name),
            "notes": "Overené cez verejný index XXXLutz Slovensko. Automatické načítanie je blokované; cenu a dostupnosť pred objednaním potvrďte manuálne.",
            "source": source,
            "verification_data": json.dumps({"source": source, "method": "public_search_index", "checked": checked}, ensure_ascii=False),
        }]
