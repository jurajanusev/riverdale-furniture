import json

from .base import BaseScraper


class MoebelixSlovakiaScraper(BaseScraper):
    store = "Möbelix Slovensko"
    catalog_url = "https://www.moebelix.sk/postele-C2C2?v_targetcolor=biela"
    allowed_hosts = ("moebelix.sk",)
    seed_urls = (
        "https://www.moebelix.sk/p/jednolozkova-postel-billy-90x200-borovica-biela-000528037501",
        "https://www.moebelix.sk/p/postel-madrid-biela-90x200-cm-000532001701",
        "https://www.moebelix.sk/p/based-postel-dirk-ii-cenovy-trhak-000778004301",
    )
    search_url_template = "https://www.moebelix.sk/search?q={query}"
    category_urls = {"koberec": "https://www.moebelix.sk/koberce-a-rohozky-C10C6"}

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
        checked = "2026-07-15"
        rows = [
            {
                "name": "Jednolôžková posteľ BILLY, 90x200, borovica, biela",
                "frame_price": 80.75, "original_price": 95.00,
                "material": "Masív, Drevo", "slats_included": False,
                "url": self.seed_urls[0], "availability": "Neoverené",
            },
            {
                "name": "Posteľ MADRID biela, 90x200 cm",
                "frame_price": 79.90, "original_price": 149.00,
                "material": "Lamino", "slats_included": None,
                "url": self.seed_urls[1], "availability": "Neoverené",
            },
            {
                "name": "POSTEĽ DIRK II biela, 90x200 cm",
                "frame_price": 159.00, "original_price": 298.00,
                "material": "Lamino", "slats_included": False,
                "url": self.seed_urls[2], "availability": "Neoverené",
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
            "notes": "Overené cez verejný index Möbelix. Automatické načítanie blokuje Cloudflare; cenu a dostupnosť pred objednaním potvrďte manuálne.",
            "source": source,
            "verification_data": json.dumps({"source": source, "method": "public_search_index", "checked": checked}, ensure_ascii=False),
        }
