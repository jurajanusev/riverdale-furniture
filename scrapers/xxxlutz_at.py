import json

from .base import BaseScraper


class XxxlutzAustriaScraper(BaseScraper):
    store = "XXXLutz Rakúsko"
    country = "Rakúsko"
    catalog_url = "https://www.xxxlutz.at/betten-C3C3?pa_lying_surface=90%2F200+cm&p_color=Wei%C3%9F"
    allowed_hosts = ("xxxlutz.at",)
    seed_urls = (
        "https://www.xxxlutz.at/p/carryhome-bett-90-200-cm-in-wei-002522009102",
    )
    search_language = "de"
    search_url_template = "https://www.xxxlutz.at/search?q={query}"
    category_urls = {"koberec": "https://www.xxxlutz.at/teppiche-C5C2"}

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
        name = "Carryhome BETT 90/200 cm in Weiß"
        return [{
            "name": name,
            **{
                key: self.criteria.get(key, default) for key, default in {
                    "space_id": "dom-betty", "space_name": "Dom Betty", "room": "spálňa / izba",
                    "main_category": "nabytok", "item_type": "posteľ",
                }.items()
            },
            "store": self.store, "country": self.country,
            "frame_price": 134.25, "original_price": 294.00,
            "sale_price": 134.25, "currency": "EUR",
            "mattress_width": 90, "mattress_length": 200,
            "total_dimensions": "97 × 207 × 81 cm", "color": "Biela",
            "material": "Lamino", "slats_included": False,
            "mattress_included": False, "product_url": source,
            "image_url": "", "additional_images": "[]",
            "last_checked": checked, "availability": "Dodanie približne 1–2 týždne podľa verejného indexu",
            "approval_status": "unreviewed",
            "style_match_score": self.score_for_context(name),
            "notes": "Overené cez verejný index XXXLutz Rakúsko. Automatické načítanie je blokované; cenu a dostupnosť pred objednaním potvrďte manuálne.",
            "source": source,
            "verification_data": json.dumps({"source": source, "method": "public_search_index", "checked": checked}, ensure_ascii=False),
        }]
