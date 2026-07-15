import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from itsdangerous import URLSafeTimedSerializer
from app import create_app
from scrapers import SCRAPERS, scraper_error_message
from scrapers.base import BaseScraper


class RiverdaleAppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.tmp.name) / "test.db"
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_cloud_admin_password_protects_management(self):
        with patch.dict(os.environ, {"RIVERDALE_ADMIN_PASSWORD": "river-secret"}):
            protected_app = create_app({"TESTING": True, "SECRET_KEY": "test"})
            client = protected_app.test_client()
            response = client.get("/")
            self.assertEqual(response.status_code, 302)
            self.assertIn("/login", response.headers["Location"])
            self.assertEqual(client.get("/healthz").status_code, 200)
            self.assertIn("Nesprávne heslo", client.post(
                "/login", data={"password": "wrong"}, follow_redirects=True,
            ).get_data(as_text=True))
            response = client.post(
                "/login", data={"password": "river-secret", "next": "/"},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Riverdale", response.get_data(as_text=True))

    def add_product(self):
        return self.client.post("/products", data={
            "name": "Overená vidiecka posteľ", "store": "JYSK Slovensko", "price": "199,90",
            "dimensions": "100 × 210 × 91 cm", "material": "MDF, masív", "color": "Biela",
            "product_url": "https://jysk.sk/example-product", "image_url": "https://example.com/bed.jpg",
            "slats_included": "no", "mattress_included": "no", "availability": "Dostupné", "notes": "Overené ručne",
        }, follow_redirects=True)

    def test_empty_index_and_manual_add(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Zatiaľ tu nie sú žiadne výsledky".encode(), response.data)
        self.assertIn("Priestory a miestnosti".encode(), response.data)
        self.assertIn("Dom Archie".encode(), response.data)
        self.assertIn("Ručne overiť blokovaný obchod".encode(), response.data)
        self.assertIn("Max. hĺbka".encode(), response.data)
        response = self.add_product()
        self.assertEqual(response.status_code, 200)
        self.assertIn("RIV-ITEM-0001", response.get_data(as_text=True))
        self.assertIn("199,90", response.get_data(as_text=True))

    def test_status_update_filters_and_exports(self):
        self.add_product()
        product = database.list_products()[0]
        response = self.client.patch(f"/api/products/{product.id}", json={"approval_status": "approved", "notes": "OK"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(database.get_product(product.id).approval_status, "approved")
        self.assertEqual(self.client.get("/?approval_status=approved").status_code, 200)
        xlsx = self.client.get("/export/xlsx")
        self.assertEqual(xlsx.status_code, 200)
        self.assertTrue(xlsx.data.startswith(b"PK"))
        csv_response = self.client.get("/export/csv")
        self.assertIn("RIV-ITEM-0001", csv_response.data.decode("utf-8-sig"))
        canva = self.client.get("/export/canva")
        self.assertIn("product_id", canva.data.decode("utf-8-sig"))

    def test_approved_products_from_multiple_categories_share_room_selection(self):
        self.add_product()
        self.client.post("/products", data={
            "space_id": "dom-betty", "room": "spálňa / izba",
            "main_category": "velke-dekoracie", "item_type": "koberec",
            "name": "Koberec Riverdale", "store": "FAVI Slovensko", "price": "89,50",
            "product_url": "https://favi.sk/example-carpet",
        })
        products = database.list_products()
        bed = next(product for product in products if product.item_type == "posteľ")
        carpet = next(product for product in products if product.item_type == "koberec")
        bed_response = self.client.patch(
            f"/api/products/{bed.id}", json={"approval_status": "approved"}
        )
        self.assertIn("/selection?", bed_response.get_json()["selection_url"])
        self.client.patch(f"/api/products/{carpet.id}", json={"approval_status": "approved"})

        selection = self.client.get("/selection", query_string={
            "space_id": "dom-betty", "room": "spálňa / izba",
        })
        text = selection.get_data(as_text=True)
        self.assertEqual(selection.status_code, 200)
        self.assertIn("Overená vidiecka posteľ", text)
        self.assertIn("Koberec Riverdale", text)
        self.assertIn("Výber miestnosti", text)
        self.assertIn("289,40 €", text)

        self.client.patch(f"/api/products/{carpet.id}", json={"approval_status": "unreviewed"})
        updated = self.client.get("/selection", query_string={
            "space_id": "dom-betty", "room": "spálňa / izba",
        }).get_data(as_text=True)
        self.assertNotIn("Koberec Riverdale", updated)
        self.assertIn("Overená vidiecka posteľ", updated)

    def test_architect_can_select_products_through_revocable_share_link(self):
        self.add_product()
        product = database.list_products()[0]
        self.client.patch(f"/api/products/{product.id}", json={"approval_status": "approved"})
        created = self.client.post("/shares", data={
            "space_id": "dom-betty", "room": "spálňa / izba",
            "main_category": "nabytok", "item_type": "posteľ",
            "architect_name": "Ateliér Novák",
        }, follow_redirects=True)
        self.assertEqual(created.status_code, 200)
        self.assertIn("Ateliér Novák", created.get_data(as_text=True))
        share = database.list_share_links("dom-betty", "spálňa / izba")[0]

        review = self.client.get(f"/architect/{share['token']}")
        self.assertEqual(review.status_code, 200)
        self.assertIn("Overená vidiecka posteľ", review.get_data(as_text=True))
        choice = self.client.post(
            f"/architect/{share['token']}/choice/{product.id}", json={"selected": True},
        )
        self.assertEqual(choice.status_code, 200)
        self.assertTrue(choice.get_json()["selected"])
        selection = self.client.get("/selection", query_string={
            "space_id": "dom-betty", "room": "spálňa / izba",
        }).get_data(as_text=True)
        self.assertIn("Páči sa architektovi", selection)

        removed = self.client.post(
            f"/architect/{share['token']}/choice/{product.id}", json={"selected": False},
        )
        self.assertFalse(removed.get_json()["selected"])
        self.client.post(f"/shares/{share['token']}/revoke")
        self.assertEqual(self.client.get(f"/architect/{share['token']}").status_code, 410)

    def test_architect_cannot_select_product_outside_shared_room(self):
        self.add_product()
        product = database.list_products()[0]
        self.client.patch(f"/api/products/{product.id}", json={"approval_status": "approved"})
        self.client.post("/shares", data={
            "space_id": "dom-betty", "room": "obývačka",
            "main_category": "nabytok", "item_type": "posteľ",
        })
        share = database.list_share_links("dom-betty", "obývačka")[0]
        response = self.client.post(
            f"/architect/{share['token']}/choice/{product.id}", json={"selected": True},
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_product(self):
        self.add_product()
        product = database.list_products()[0]
        response = self.client.delete(f"/api/products/{product.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(database.get_product(product.id))
        missing = self.client.delete(f"/api/products/{product.id}")
        self.assertEqual(missing.status_code, 404)

    def test_validation_rejects_store_and_price(self):
        response = self.client.post("/products", data={"name": "X", "store": "Iný obchod", "price": "10", "product_url": "https://example.com/x"}, follow_redirects=True)
        self.assertIn("nie je povolený", response.get_data(as_text=True))
        response = self.client.post("/products", data={"name": "X", "store": "IKEA Slovensko", "price": "-1", "product_url": "https://example.com/x"}, follow_redirects=True)
        self.assertIn("nemôže byť záporná", response.get_data(as_text=True))

    def test_scraper_parses_json_ld_without_inventing(self):
        html = '''<html><script type="application/ld+json">{"@type":"Product","name":"COUNTRY posteľ biela 90x200","image":["https://example.com/a.jpg"],"description":"Masívne drevo, tradičné čelo. Bez roštu a matraca.","offers":{"price":"249.00","priceCurrency":"EUR","availability":"https://schema.org/InStock"}}</script></html>'''
        scraper = BaseScraper()
        scraper.store = "JYSK Slovensko"
        product = scraper.parse_product("https://example.com/product", html)
        self.assertEqual(product["frame_price"], 249.0)
        self.assertFalse(product["slats_included"])
        self.assertFalse(product["mattress_included"])
        self.assertTrue(scraper.qualifies(product))

    def test_scraper_normalizes_image_object_and_shared_exclusions(self):
        html = '''<html><head><meta property="og:title" content="Vidiecka posteľ biela 90x200"></head><body><h1>Vidiecka posteľ biela 90x200</h1><script type="application/ld+json">{"@type":"Product","name":"Vidiecka posteľ biela 90x200","image":{"@type":"ImageObject","contentUrl":"https://example.com/bed.jpg"},"description":"Tradičné drevené čelo. Rošt postele, matrac a obliečky nie sú súčasťou balenia.","offers":{"price":"199","priceCurrency":"EUR"}}</script></body></html>'''
        scraper = BaseScraper()
        scraper.store = "IKEA Slovensko"
        product = scraper.parse_product("https://example.com/product", html)
        self.assertEqual(product["image_url"], "https://example.com/bed.jpg")
        self.assertFalse(product["slats_included"])
        self.assertFalse(product["mattress_included"])
        self.assertTrue(scraper.qualifies(product))

    def test_generic_scraper_uses_context_without_bed_requirements(self):
        html = '''<html><script type="application/ld+json">{"@type":"Product","name":"Americký drevený jedálenský stôl","description":"Klasický vintage štýl","offers":{"price":"399","priceCurrency":"EUR"}}</script></html>'''
        scraper = BaseScraper(criteria={
            "space_id": "dom-archie", "space_name": "Dom Archie", "room": "jedáleň",
            "main_category": "nabytok", "item_type": "jedálenský stôl", "max_price": 450,
            "color": "", "material": "",
        })
        product = scraper.parse_product("https://example.com/table", html)
        self.assertTrue(scraper.qualifies(product))
        self.assertEqual(product["space_name"], "Dom Archie")
        self.assertEqual(product["item_type"], "jedálenský stôl")
        self.assertEqual(product["style_match_score"], 0)

    def test_space_never_changes_product_style_score(self):
        text = "vidiecky elegantný industriálny nábytok"
        scores = {
            BaseScraper(criteria={"space_id": space_id}).score_for_context(text)
            for space_id in ("dom-betty", "dom-archie", "vila-cheryl", "bunker")
        }
        self.assertEqual(scores, {0})

    def test_scraper_uses_explicit_open_graph_price_metadata(self):
        html = '''<html><head><meta property="og:title" content="Koberec Creation 160x230 cm"><meta property="og:image" content="/images/carpet.webp"></head><body><script>data={"currency":"EUR","price":109,"price_without_VAT":90.83}</script></body></html>'''
        scraper = BaseScraper(criteria={"item_type": "koberec", "max_price": 200})
        product = scraper.parse_product("https://example.com/123-koberec", html)
        self.assertEqual(product["frame_price"], 109.0)
        self.assertEqual(product["image_url"], "https://example.com/images/carpet.webp")
        self.assertTrue(scraper.qualifies(product))

    def test_common_shop_filters_are_applied_to_verified_product_data(self):
        product = {
            "name": "Drevená komoda", "frame_price": 199.0, "color": "Hnedá",
            "material": "Drevo", "availability": "Dostupné",
            "total_dimensions": "120 × 45 × 80 cm",
        }
        matching = BaseScraper(criteria={
            "item_type": "komoda", "min_price": 150, "max_price": 250,
            "color": "hnedá", "material": "drevo", "in_stock": True,
            "min_width": 100, "max_width": 130, "max_depth": 50, "max_height": 90,
        })
        self.assertTrue(matching.qualifies(product))
        too_narrow = BaseScraper(criteria={"item_type": "komoda", "min_width": 130})
        self.assertFalse(too_narrow.qualifies(product))

    def test_bed_shop_filters_are_configurable(self):
        product = {
            "name": "Drevená posteľ", "frame_price": 399.0, "color": "Hnedá",
            "material": "Drevo", "availability": "Dostupné", "total_dimensions": "100 × 210 × 90 cm",
            "mattress_width": 90, "mattress_length": 200,
            "slats_included": True, "mattress_included": False,
        }
        scraper = BaseScraper(criteria={
            "item_type": "posteľ", "bed_width": "90", "bed_length": "200",
            "slats_included": "yes", "mattress_included": "no",
        })
        self.assertTrue(scraper.qualifies(product))
        scraper.criteria["bed_width"] = "160"
        self.assertFalse(scraper.qualifies(product))

    def test_all_store_adapters_have_generic_carpet_catalog(self):
        criteria = {"item_type": "koberec", "main_category": "velke-dekoracie"}
        urls = {scraper_class.store: scraper_class(criteria=criteria).catalog_url_for_search() for scraper_class in SCRAPERS}
        self.assertTrue(all(urls.values()), urls)
        ikea_at = next(scraper for scraper in SCRAPERS if scraper.store == "IKEA Rakúsko")
        self.assertIn("Sessel", ikea_at(criteria={"item_type": "kreslo"}).catalog_url_for_search())

    def test_playwright_install_error_is_shortened_for_users(self):
        error = RuntimeError(
            "BrowserType.launch_persistent_context: Executable doesn't exist at /tmp/chrome "
            "Please run the following command to download new browsers: playwright install"
        )
        self.assertEqual(
            scraper_error_message(error),
            "cloudový prehliadač nie je pripravený",
        )

    def test_ikea_and_jysk_use_direct_chest_of_drawers_categories(self):
        from scrapers.ikea_sk import IkeaSlovakiaScraper
        from scrapers.ikea_at import IkeaAustriaScraper
        from scrapers.jysk_sk import JyskSlovakiaScraper
        from scrapers.jysk_at import JyskAustriaScraper

        urls = [scraper(criteria={"item_type": "komoda"}).catalog_url_for_search() for scraper in (
            IkeaSlovakiaScraper, IkeaAustriaScraper, JyskSlovakiaScraper, JyskAustriaScraper,
        )]
        self.assertTrue(all("search" not in url for url in urls), urls)
        self.assertIn("komody-10451", urls[0])
        self.assertIn("kommoden-10451", urls[1])
        self.assertTrue(urls[2].endswith("/ulozne-priestory/komody"))
        self.assertTrue(urls[3].endswith("/aufbewahrung/kommoden"))

    def test_jysk_generic_product_url_matching(self):
        from scrapers.jysk_sk import JyskSlovakiaScraper
        scraper = JyskSlovakiaScraper(criteria={"item_type": "koberec"})
        self.assertTrue(scraper.is_product_url("https://jysk.sk/domacnost/koberce/male-koberce/koberec-tysbast-60x90-rozne"))

    @patch("app.search_all")
    def test_search_imports_only_returned_products(self, search_all):
        search_all.return_value = ([], ["IKEA Slovensko: 0 vhodných produktov"])
        response = self.client.post("/search", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(database.list_products(), [])

    @patch("app.search_all")
    def test_search_passes_riverdale_context_and_generic_criteria(self, search_all):
        search_all.return_value = ([], ["FAVI Slovensko: 0 vhodných produktov"])
        response = self.client.post("/search", data={
            "space_id": "dom-archie", "room": "jedáleň", "main_category": "nabytok",
            "item_type": "jedálenský stôl", "search_max_price": "450",
            "search_min_price": "100", "search_color": "hnedá", "search_material": "drevo",
            "search_in_stock": "yes", "search_min_width": "120", "search_max_width": "200",
            "search_max_depth": "100", "search_max_height": "90",
        })
        self.assertEqual(response.status_code, 302)
        criteria = search_all.call_args.args[0]
        self.assertEqual(criteria["space_name"], "Dom Archie")
        self.assertEqual(criteria["room"], "jedáleň")
        self.assertEqual(criteria["item_type"], "jedálenský stôl")
        self.assertEqual(criteria["max_price"], 450.0)
        self.assertEqual(criteria["min_price"], 100.0)
        self.assertTrue(criteria["in_stock"])
        self.assertEqual(criteria["min_width"], 120.0)
        self.assertEqual(criteria["max_depth"], 100.0)

    @patch("app.subprocess.Popen")
    def test_manual_captcha_verification_starts_persistent_browser_helper(self, popen):
        response = self.client.post("/verify-store/moebelix-sk", data={
            "space_id": "dom-betty", "room": "spálňa / izba",
            "main_category": "nabytok", "item_type": "komoda",
            "search_max_price": "350", "search_color": "hnedá",
            "search_in_stock": "yes", "search_min_width": "80",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Otvorilo sa ručné overenie".encode(), response.data)
        popen.assert_called_once()
        self.assertIn("verify_store.py", popen.call_args.args[0][1])
        self.assertEqual(popen.call_args.args[0][-2], "komoda")
        helper_context = json.loads(popen.call_args.args[0][-1])
        self.assertEqual(helper_context["space_id"], "dom-betty")
        self.assertEqual(helper_context["item_type"], "komoda")
        self.assertEqual(helper_context["max_price"], 350.0)
        self.assertEqual(helper_context["color"], "hnedá")
        self.assertTrue(helper_context["in_stock"])
        self.assertEqual(helper_context["min_width"], 80.0)
        self.assertIn(b'name="search_max_price"', response.data)
        self.assertIn(b'value="350"', response.data)

    @patch("app.subprocess.Popen")
    def test_cloud_captcha_uses_local_collector_instead_of_server_browser(self, popen):
        with patch.dict(os.environ, {"RENDER": "true"}):
            page = self.client.get("/")
            response = self.client.post(
                "/verify-store/moebelix-sk",
                data={"space_id": "dom-betty", "room": "spálňa / izba", "item_type": "posteľ"},
                follow_redirects=True,
            )
        self.assertIn(b"http://127.0.0.1:5000/local-verify-all", page.data)
        self.assertIn("CAPTCHA sa musí overiť na vašom počítači".encode(), response.data)
        popen.assert_not_called()

    @patch("app.subprocess.Popen")
    def test_cloud_button_can_start_local_verification_without_switching_apps(self, popen):
        response = self.client.get(
            "/local-verify-all",
            query_string={
                "space_id": "dom-betty", "room": "spálňa / izba",
                "main_category": "nabytok", "item_type": "posteľ",
                "search_max_price": "500", "search_bed_width": "90",
                "collector_token": "short-lived-token",
                "collector_cloud_url": "https://riverdale-furniture.onrender.com",
            },
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"window.close()", response.data)
        popen.assert_called_once()
        self.assertIn("verify_all_stores.py", popen.call_args.args[0][1])
        helper_context = json.loads(popen.call_args.args[0][-1])
        self.assertEqual(helper_context["max_price"], 500.0)
        self.assertEqual(helper_context["bed_width"], "90")
        self.assertEqual(helper_context["collector_token"], "short-lived-token")

    def test_collector_import_requires_token_and_saves_valid_product(self):
        payload = {"products": [{
            "name": "Komoda z lokálneho zberača",
            "space_id": "dom-betty", "room": "spálňa / izba",
            "main_category": "nabytok", "item_type": "komoda",
            "store": "Möbelix Slovensko", "country": "Slovensko",
            "frame_price": 179.0, "sale_price": 179.0, "currency": "EUR",
            "product_url": "https://www.moebelix.sk/p/komoda-riverdale-000000000001",
            "image_url": "https://example.com/komoda.jpg", "availability": "Dostupné",
        }]}
        with patch.dict(os.environ, {"RIVERDALE_ADMIN_PASSWORD": "cloud-secret"}):
            self.assertEqual(self.client.post("/api/collector/products", json=payload).status_code, 401)
            response = self.client.post(
                "/api/collector/products", json=payload,
                headers={"Authorization": "Bearer cloud-secret"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["imported"], 1)
        products = database.list_products({"store": "Möbelix Slovensko"})
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].item_type, "komoda")
        self.assertEqual(products[0].approval_status, "unreviewed")

    def test_collector_import_rejects_forged_store_url(self):
        payload = {"products": [{
            "name": "Falošný produkt", "store": "Möbelix Slovensko",
            "product_url": "https://example.com/p/not-moebelix",
        }]}
        with patch.dict(os.environ, {"RIVERDALE_SYNC_TOKEN": "sync-secret"}):
            response = self.client.post(
                "/api/collector/products", json=payload,
                headers={"Authorization": "Bearer sync-secret"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["imported"], 0)

    def test_short_lived_cloud_token_imports_without_admin_password(self):
        token = URLSafeTimedSerializer("test", salt="riverdale-collector").dumps({"purpose": "collector"})
        response = self.client.post(
            "/api/collector/products",
            json={"products": [{
                "name": "Posteľ z CAPTCHA", "store": "Möbelix Slovensko",
                "product_url": "https://www.moebelix.sk/p/postel-riverdale-000000000001",
                "space_id": "dom-betty", "room": "spálňa / izba",
                "main_category": "nabytok", "item_type": "posteľ",
            }]},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["imported"], 1)

    @patch("verify_store.requests.post")
    def test_local_collector_sends_products_with_bearer_token(self, post):
        from verify_store import sync_to_cloud

        post.return_value.raise_for_status.return_value = None
        post.return_value.json.return_value = {"ok": True, "imported": 2}
        with patch.dict(os.environ, {
            "RIVERDALE_CLOUD_URL": "https://riverdale-furniture.onrender.com/",
            "RIVERDALE_SYNC_TOKEN": "collector-secret",
        }):
            synced, error = sync_to_cloud([{"name": "A"}, {"name": "B"}])
        self.assertEqual((synced, error), (2, ""))
        self.assertEqual(
            post.call_args.kwargs["headers"]["Authorization"],
            "Bearer collector-secret",
        )
        self.assertEqual(
            post.call_args.args[0],
            "https://riverdale-furniture.onrender.com/api/collector/products",
        )

    def test_verified_browser_cache_is_used_before_network(self):
        import scrapers.base as base_module

        with tempfile.TemporaryDirectory() as cache_dir, patch.object(base_module, "BROWSER_CACHE_ROOT", Path(cache_dir)):
            scraper = BaseScraper()
            scraper.store = "Möbelix Slovensko"
            url = "https://www.moebelix.sk/p/example"
            base_module.write_browser_cache(scraper.store, url, "<html>overený produkt</html>")
            with patch.object(scraper.session, "get") as get:
                self.assertIn("overený produkt", scraper.fetch(url))
                get.assert_not_called()

    def test_manual_generic_product_keeps_context_and_allows_higher_price(self):
        response = self.client.post("/products", data={
            "space_id": "dom-betty", "room": "jedáleň", "main_category": "nabytok",
            "item_type": "jedálenský stôl", "name": "Vidiecky jedálenský stôl",
            "store": "Bonami Slovensko", "price": "450", "dimensions": "180 × 90 × 76 cm",
            "product_url": "https://www.bonami.sk/p/example-table",
        })
        self.assertEqual(response.status_code, 302)
        product = database.list_products({"item_type": "jedálenský stôl"})[0]
        self.assertEqual(product.space_name, "Dom Betty")
        self.assertEqual(product.room, "jedáleň")
        self.assertEqual(product.frame_price, 450.0)

    def test_seed_url_is_used_when_catalog_is_blocked(self):
        from requests import HTTPError
        scraper = BaseScraper()
        scraper.store = "JYSK Slovensko"
        scraper.seed_urls = ("https://example.com/product",)
        scraper.catalog_url = "https://example.com/catalog"
        scraper.allowed_hosts = ("example.com",)
        html = '''<script type="application/ld+json">{"@type":"Product","name":"Country posteľ biela 90x200","description":"Tradičné drevené čelo. Bez roštu a matraca.","offers":{"price":"199","priceCurrency":"EUR"}}</script>'''

        def fake_fetch(url):
            if url.endswith("catalog"):
                raise HTTPError("blocked")
            return html

        scraper.fetch = fake_fetch
        products = scraper.search()
        self.assertEqual(len(products), 1)


if __name__ == "__main__":
    unittest.main()
