import json
import hashlib
import re
import time
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup


BROWSER_PROFILE_ROOT = Path(__file__).resolve().parent.parent / "data" / "browser_profiles"
BROWSER_CACHE_ROOT = Path(__file__).resolve().parent.parent / "data" / "browser_cache"
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"


def browser_profile_dir(store):
    value = unicodedata.normalize("NFKD", store).encode("ascii", "ignore").decode().lower()
    return BROWSER_PROFILE_ROOT / re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def browser_cache_path(store, url):
    store_dir = browser_profile_dir(store).name
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return BROWSER_CACHE_ROOT / store_dir / f"{key}.html"


def write_browser_cache(store, url, html):
    path = browser_cache_path(store, url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


class BaseScraper:
    store = ""
    country = "Slovensko"
    catalog_url = ""
    allowed_hosts = ()
    seed_urls = ()
    delay_seconds = 1.2
    max_product_pages = 18
    category_urls = {}
    search_url_template = ""
    search_language = "sk"
    german_terms = {
        "posteľ": "Bett", "nočný stolík": "Nachttisch", "skriňa": "Schrank",
        "komoda": "Kommode", "sekretár": "Sekretär", "knižnica": "Bücherregal",
        "polica": "Wandregal", "regál": "Regal", "stôl": "Tisch",
        "jedálenský stôl": "Esstisch", "konferenčný stolík": "Couchtisch",
        "pracovný stôl": "Schreibtisch", "písací stôl": "Schreibtisch",
        "toaletný stolík": "Schminktisch", "barový pult": "Bartheke",
        "stolička": "Stuhl", "jedálenská stolička": "Esszimmerstuhl",
        "kreslo": "Sessel", "pohovka": "Sofa", "lavica": "Sitzbank",
        "taburetka": "Hocker", "barová stolička": "Barhocker", "vešiak": "Garderobe",
        "botník": "Schuhschrank", "paraván": "Paravent", "zrkadlo stojace": "Standspiegel",
        "servírovací vozík": "Servierwagen", "vitrína": "Vitrine", "TV skrinka": "TV Lowboard",
        "koberec": "Teppich", "záves": "Vorhang", "záclona": "Gardine",
        "veľký obraz": "Wandbild", "malý obraz": "Bild", "nástenná dekorácia": "Wanddekoration",
        "veľké zrkadlo": "Wandspiegel", "stojaca lampa": "Stehlampe", "stolová lampa": "Tischlampe",
        "nočná lampa": "Nachttischlampe", "luster": "Kronleuchter",
        "stropné svietidlo": "Deckenleuchte", "nástenné svietidlo": "Wandleuchte",
        "váza": "Vase", "svietnik": "Kerzenhalter", "rámik na fotografiu": "Bilderrahmen",
        "miska": "Schale", "podnos": "Tablett", "kvetináč": "Blumentopf",
        "vankúš": "Kissen", "deka": "Decke", "obrus": "Tischdecke",
        "posteľná bielizeň": "Bettwäsche", "hodiny": "Uhr", "nástenné hodiny": "Wanduhr",
        "izbová rastlina": "Zimmerpflanze", "umelá rastlina": "Kunstpflanze",
    }

    def __init__(self, session=None, criteria=None):
        self.session = session or requests.Session()
        self.criteria = criteria or {}
        self.session.headers.update({
            "User-Agent": BROWSER_USER_AGENT,
            "Accept-Language": "sk-SK,sk;q=0.9,en;q=0.7",
        })
        self.load_manual_session()

    def load_manual_session(self):
        state_path = browser_profile_dir(self.store) / "riverdale-state.json"
        if not state_path.exists():
            return
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            for cookie in state.get("cookies", []):
                self.session.cookies.set(
                    cookie["name"], cookie["value"],
                    domain=cookie.get("domain"), path=cookie.get("path", "/"),
                )
        except (OSError, ValueError, KeyError, TypeError):
            return

    def catalog_url_for_search(self):
        item_type = self.criteria.get("item_type", "posteľ")
        if item_type in self.category_urls:
            return self.category_urls[item_type]
        if item_type == "posteľ":
            return self.catalog_url
        if self.search_url_template:
            term = self.german_terms.get(item_type, item_type) if self.search_language == "de" else item_type
            return self.search_url_template.format(query=quote_plus(term))
        return ""

    def item_type_tokens(self):
        term = self.criteria.get("item_type", "")
        if self.search_language == "de":
            term = self.german_terms.get(term, term)
        normalized = unicodedata.normalize("NFKD", term).encode("ascii", "ignore").decode().lower()
        return [token for token in re.findall(r"[a-z0-9]+", normalized) if len(token) >= 4]

    def fetch(self, url):
        cached = browser_cache_path(self.store, url)
        if cached.exists() and time.time() - cached.stat().st_mtime < 6 * 60 * 60:
            return cached.read_text(encoding="utf-8")
        response = self.session.get(url, timeout=18)
        if response.status_code == 403:
            return self.fetch_with_browser(url)
        response.raise_for_status()
        time.sleep(self.delay_seconds)
        return response.text

    def fetch_with_browser(self, url):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Obchod vyžaduje prehliadač. Nainštalujte Playwright a Chromium "
                "podľa README."
            ) from exc

        profile = browser_profile_dir(self.store)
        profile.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                str(profile), headless=True, locale="sk-SK", user_agent=BROWSER_USER_AGENT,
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_timeout(1_500)
                html = page.content()
                challenge = (page.title() + " " + html[:5000]).lower()
                blocked_terms = (
                    "captcha", "verify you are human", "overte, že nie ste robot",
                    "access denied", "len chvíľu", "request could not be satisfied",
                )
                if any(term in challenge for term in blocked_terms):
                    raise RuntimeError("Stránka vyžaduje CAPTCHA alebo manuálne overenie.")
                time.sleep(self.delay_seconds)
                return html
            finally:
                context.close()

    def search(self):
        catalog_url = self.catalog_url_for_search()
        if not catalog_url:
            return []
        urls = list(self.seed_urls) if self.criteria.get("item_type", "posteľ") == "posteľ" else []
        try:
            soup = BeautifulSoup(self.fetch(catalog_url), "html.parser")
            discovered = self.product_urls_from_jsonld(soup)
            urls.extend(url for url in discovered if url not in urls)
            for link in soup.select("a[href]"):
                url = urljoin(catalog_url, link.get("href", "")).split("#")[0]
                if self.is_product_url(url) and url not in urls:
                    urls.append(url)
                if len(urls) >= self.max_product_pages:
                    break
        except requests.RequestException:
            if not urls:
                raise
        products = []
        for url in urls:
            try:
                product = self.parse_product(url, self.fetch(url))
                if product and self.qualifies(product):
                    products.append(product)
            except (requests.RequestException, ValueError, json.JSONDecodeError):
                continue
        return products

    def product_urls_from_jsonld(self, soup):
        urls = []

        def walk(value):
            if isinstance(value, dict):
                kind = value.get("@type")
                if kind == "Product" or (isinstance(kind, list) and "Product" in kind):
                    url = str(value.get("url") or "").replace(".sk//", ".sk/")
                    if url and self.is_product_url(url) and url not in urls:
                        urls.append(url)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                walk(json.loads(script.string or script.get_text()))
            except (json.JSONDecodeError, TypeError):
                continue
        terms = [self.criteria.get("item_type", ""), self.criteria.get("color", "")]
        urls.sort(key=lambda url: sum(term.lower() not in url.lower() for term in terms if term))
        return urls[:self.max_product_pages]

    def is_product_url(self, url):
        return any(host in url for host in self.allowed_hosts) and self.product_path_matches(url)

    def product_path_matches(self, url):
        return "/p/" in url or "/produkt/" in url

    def parse_product(self, url, html):
        soup = BeautifulSoup(html, "html.parser")
        data = self.find_product_jsonld(soup)
        if not data:
            data = self.find_product_metadata(soup, html, url)
        if not data:
            return None
        offer = data.get("offers") or {}
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        image = data.get("image") or ""
        raw_images = image if isinstance(image, list) else [image] if image else []
        images = []
        for item in raw_images:
            if isinstance(item, dict):
                item = item.get("contentUrl") or item.get("url") or ""
            if isinstance(item, str) and item:
                images.append(urljoin(url, item))
        text = soup.get_text(" ", strip=True)
        name = str(data.get("name") or "").strip()
        if not name:
            heading = soup.select_one("h1")
            meta_title = soup.select_one('meta[property="og:title"]')
            name = (heading.get_text(" ", strip=True) if heading else "") or (meta_title.get("content", "").strip() if meta_title else "")
        if not images:
            meta_image = soup.select_one('meta[property="og:image"]')
            if meta_image and meta_image.get("content"):
                images.append(meta_image["content"])
        description = str(data.get("description") or "")
        combined = f"{name} {description} {text[:15000]}"
        style_text = f"{name} {description}"
        width, length = self.extract_mattress_size(style_text)
        price = self.parse_price(offer.get("price") or offer.get("lowPrice"))
        return {
            "name": name,
            "space_id": self.criteria.get("space_id", "dom-betty"),
            "space_name": self.criteria.get("space_name", "Dom Betty"),
            "room": self.criteria.get("room", "spálňa / izba"),
            "main_category": self.criteria.get("main_category", "nabytok"),
            "item_type": self.criteria.get("item_type", "posteľ"),
            "store": self.store,
            "country": self.country,
            "frame_price": price,
            "original_price": None,
            "sale_price": price,
            "currency": offer.get("priceCurrency") or "EUR",
            "mattress_width": width,
            "mattress_length": length,
            "total_dimensions": self.extract_total_dimensions(combined),
            "color": self.extract_color(style_text),
            "material": self.extract_material(style_text),
            "slats_included": self.extract_inclusion(style_text, "rošt"),
            "mattress_included": self.extract_inclusion(style_text, "matrac"),
            "product_url": url,
            "image_url": images[0] if images else "",
            "additional_images": json.dumps(images[1:8], ensure_ascii=False),
            "last_checked": date.today().isoformat(),
            "availability": self.availability(offer),
            "notes": "Pred objednaním skontrolujte variant, konečnú cenu a príslušenstvo.",
            "approval_status": "unreviewed",
            "style_match_score": self.score_for_context(style_text),
            "source": url,
            "verification_data": json.dumps({"source": url, "checked": date.today().isoformat()}, ensure_ascii=False),
        }

    @staticmethod
    def find_product_metadata(soup, html, url):
        """Use explicit public metadata when a shop omits Product JSON-LD."""
        title = soup.select_one('meta[property="og:title"]')
        image = soup.select_one('meta[property="og:image"]')
        description = soup.select_one('meta[property="og:description"], meta[name="description"]')
        if not title or not title.get("content"):
            return None
        price_meta = soup.select_one(
            'meta[property="product:price:amount"], meta[itemprop="price"], [itemprop="price"][content]'
        )
        price = price_meta.get("content") if price_meta else None
        if price is None:
            price_match = re.search(r'"currency"\s*:\s*"EUR"\s*,\s*"price"\s*:\s*(\d+(?:\.\d+)?)', html, re.I)
            if not price_match:
                price_match = re.search(r'"price"\s*:\s*(\d+(?:\.\d+)?)\s*,\s*"price_without_VAT"', html, re.I)
            price = price_match.group(1) if price_match else None
        if price is None:
            return None
        return {
            "@type": "Product",
            "name": title.get("content", "").strip(),
            "description": description.get("content", "").strip() if description else "",
            "image": urljoin(url, image.get("content", "")) if image else "",
            "offers": {"price": price, "priceCurrency": "EUR"},
        }

    @staticmethod
    def find_product_jsonld(soup):
        def walk(value):
            if isinstance(value, dict):
                kind = value.get("@type")
                if kind == "Product" or (isinstance(kind, list) and "Product" in kind):
                    return value
                for child in value.values():
                    found = walk(child)
                    if found:
                        return found
            elif isinstance(value, list):
                for child in value:
                    found = walk(child)
                    if found:
                        return found
            return None
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                found = walk(json.loads(script.string or script.get_text()))
                if found:
                    return found
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    @staticmethod
    def parse_price(value):
        if value is None:
            return None
        match = re.search(r"\d+(?:[\s.,]\d{1,2})?", str(value).replace("\xa0", ""))
        return float(match.group(0).replace(" ", "").replace(",", ".")) if match else None

    @staticmethod
    def extract_mattress_size(text):
        match = re.search(r"(?<!\d)(80|90|100)\s*[x×/]\s*(190|200|210)(?!\d)", text, re.I)
        return (int(match.group(1)), int(match.group(2))) if match else (None, None)

    @staticmethod
    def extract_total_dimensions(text):
        match = re.search(r"(?:š(?:írka)?\.?\s*)?(\d{2,3})\s*(?:cm)?\s*[x×]\s*(?:d(?:ĺžka)?\.?\s*)?(\d{2,3})\s*(?:cm)?(?:\s*[x×]\s*(?:v(?:ýška)?\.?\s*)?(\d{2,3})\s*cm)?", text, re.I)
        if not match:
            return "Neoverené"
        return " × ".join(v for v in match.groups() if v) + " cm"

    @staticmethod
    def extract_color(text):
        lowered = text.lower()
        colors = {
            "Ivory": ("ivory", "slonovin", "elfenbein"),
            "Biela": ("biela", "biely", "white", "weiß", "weiss"),
            "Čierna": ("čierna", "čierny", "black", "schwarz"),
            "Hnedá": ("hnedá", "hnedý", "brown", "braun"),
            "Béžová": ("béžová", "béžový", "beige"),
            "Sivá": ("sivá", "sivý", "šedá", "šedý", "grey", "gray", "grau"),
            "Zelená": ("zelená", "zelený", "green", "grün"),
            "Modrá": ("modrá", "modrý", "blue", "blau"),
            "Červená": ("červená", "červený", "red", "rot"),
            "Ružová": ("ružová", "ružový", "pink", "rosa"),
            "Zlatá": ("zlatá", "zlatý", "gold"),
        }
        for label, terms in colors.items():
            if any(term in lowered for term in terms):
                return label
        return "Neoverené"

    @staticmethod
    def extract_material(text):
        hits = []
        for label, terms in {"Masív": ("masív", "solid wood", "massivholz"), "MDF": ("mdf",), "Lamino": ("lamino", "drevotriesk", "particleboard", "holzwerkstoff", "spanplatte"), "Drevo": ("drevo", "wood", "holz"), "Kov": ("kov", "metal", "stahl", "oceľ"), "Sklo": ("sklo", "glass", "glas"), "Textil": ("textil", "fabric", "stoff"), "Keramika": ("keramik", "ceramic"), "Plast": ("plast", "plastic", "kunststoff")}.items():
            if any(term in text.lower() for term in terms):
                hits.append(label)
        return ", ".join(hits) if hits else "Neoverené"

    @staticmethod
    def extract_inclusion(text, noun):
        low = text.lower()
        german_noun = "lattenrost" if noun == "rošt" else "matratze"
        shared_without = (
            "bez roštu a matraca" in low
            or "bez roštu aj matraca" in low
            or bool(re.search(r"rošt\w*(?:\s+postele)?\s*,\s*matrac\w*.*nie sú súčasť", low))
            or bool(re.search(r"rošt\w*\s+a\s+matrac\w*.*nie sú súčasť", low))
        )
        if (shared_without
                or re.search(rf"bez\s+(?:lamelového\s+)?{noun}", low)
                or re.search(rf"{noun}\w*\s+(?:nie je|nie sú)\s+súčasť", low)
                or re.search(rf"{noun}\w*.*(?:predáva|predávajú)\s+(?:sa\s+)?samostatne", low)
                or re.search(rf"ohne\s+(?:\w+\s+)?{german_noun}", low)
                or re.search(rf"{german_noun}\w*.*separat\s+erhältlich", low)):
            return False
        if (re.search(rf"{noun}\w*\s+(?:je|sú)\s+(?:v cene|súčasť)", low)
                or f"s {noun}" in low
                or re.search(rf"inkl(?:usive|\.)?\s+(?:\w+\s+)?{german_noun}", low)
                or re.search(rf"mit\s+{german_noun}", low)):
            return True
        return None

    @staticmethod
    def availability(offer):
        value = str(offer.get("availability") or "").lower()
        if "instock" in value:
            return "Dostupné"
        if "outofstock" in value:
            return "Nedostupné"
        return "Neoverené"

    def score_for_context(self, text):
        """Priestor je iba cieľové zaradenie; štýl výsledky nehodnotí ani nefiltruje."""
        return 0

    def qualifies(self, product):
        item_type = self.criteria.get("item_type", "posteľ")
        min_price = self.criteria.get("min_price")
        max_price = self.criteria.get("max_price")
        desired_color = self.criteria.get("color", "").strip().lower()
        desired_material = self.criteria.get("material", "").strip().lower()
        if product.get("frame_price") is None:
            return False
        if min_price not in (None, "") and product["frame_price"] < float(min_price):
            return False
        if max_price not in (None, "") and product["frame_price"] > float(max_price):
            return False
        if desired_color and desired_color not in str(product.get("color") or "").lower():
            return False
        if desired_material and desired_material not in str(product.get("material") or "").lower():
            return False
        if self.criteria.get("in_stock") and product.get("availability") != "Dostupné":
            return False
        dimensions = self.product_dimensions(product)
        dimension_filters = (
            ("min_width", 0, lambda actual, limit: actual >= limit),
            ("max_width", 0, lambda actual, limit: actual <= limit),
            ("max_depth", 1, lambda actual, limit: actual <= limit),
            ("max_height", 2, lambda actual, limit: actual <= limit),
        )
        for key, position, comparison in dimension_filters:
            limit = self.criteria.get(key)
            if limit not in (None, ""):
                if len(dimensions) <= position or not comparison(dimensions[position], float(limit)):
                    return False
        if item_type != "posteľ":
            return True
        name = product["name"].lower()
        excluded = ("poschod", "domček", "rozklad", "výsuv", "na kolies", "kovov", "metal", "detsk", "zábran", "ochrann", "etagenbett", "hochbett", "hausbett", "ausziehbett", "kinderbett")
        bed_width = self.criteria.get("bed_width")
        bed_length = self.criteria.get("bed_length")
        slats = self.criteria.get("slats_included")
        mattress = self.criteria.get("mattress_included")
        return (
            (bed_width in (None, "") or product.get("mattress_width") == int(bed_width))
            and (bed_length in (None, "") or product.get("mattress_length") == int(bed_length))
            and (slats in (None, "", "any") or product.get("slats_included") is (slats == "yes"))
            and (mattress in (None, "", "any") or product.get("mattress_included") is (mattress == "yes"))
            and not any(word in name for word in excluded)
        )

    @staticmethod
    def product_dimensions(product):
        values = re.findall(r"\d+(?:[.,]\d+)?", str(product.get("total_dimensions") or ""))
        return tuple(float(value.replace(",", ".")) for value in values[:3])
