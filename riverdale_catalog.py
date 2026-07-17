"""Riverdale project structure used by the focused product-search application."""

PROJECT_NAME = "Riverdale"

SPACES = [
    {"id": "dom-archie", "name": "Dom Archie", "rooms": ["izba Archie", "obývačka", "kuchyňa", "jedáleň", "vstupná zóna", "schodisko"]},
    {"id": "dom-betty", "name": "Dom Betty", "rooms": ["spálňa / izba", "obývačka", "kuchyňa", "jedáleň", "vstupná zóna", "schodisko"]},
    {"id": "vila-cheryl", "name": "Vila Cheryl", "rooms": ["salón", "jedáleň", "vstupná hala", "schodisko", "odpočinková zóna"]},
    {"id": "garzonka", "name": "Garzónka", "rooms": ["obývacia a spacia zóna", "kuchynská zóna", "vstup"]},
    {"id": "izba-veronika", "name": "Izba Veronika", "rooms": ["hlavná izba", "kúpeľňová alebo servisná zóna"]},
    {"id": "bufet", "name": "Bufet", "rooms": ["predajná zóna", "sedenie", "obsluha"]},
    {"id": "kaplnka", "name": "Kaplnka", "rooms": ["hlavný priestor", "oltárna zóna"]},
    {"id": "izba-polly", "name": "Izba Polly", "rooms": ["hlavná izba"]},
    {"id": "izba-cheryl", "name": "Izba Cheryl", "rooms": ["hlavná izba"]},
    {"id": "skola", "name": "Škola", "rooms": ["trieda", "hudobňa", "redakcia", "riaditeľňa", "kancelária starostky", "chodby", "vstup školy", "vstup Polly"]},
    {"id": "bar-veronika", "name": "Bar Veronika", "rooms": ["barový pult", "sedenie", "vstupná zóna"]},
    {"id": "fefe-beef", "name": "Fefe Beef", "rooms": ["hlavná reštaurácia", "barový alebo výdajný pult", "boxové sedenie", "vstup"]},
    {"id": "bunker", "name": "Bunker", "rooms": ["hlavná miestnosť", "vstupná zóna"]},
]

CATEGORIES = [
    {"id": "nabytok", "name": "Nábytok", "types": ["posteľ", "nočný stolík", "skriňa", "komoda", "sekretár", "knižnica", "polica", "regál", "stôl", "jedálenský stôl", "konferenčný stolík", "pracovný stôl", "písací stôl", "toaletný stolík", "barový pult", "stolička", "jedálenská stolička", "kreslo", "pohovka", "lavica", "taburetka", "barová stolička", "školská lavica", "učiteľský stôl", "vešiak", "botník", "paraván", "zrkadlo stojace", "servírovací vozík", "vitrína", "TV skrinka", "kuchynský ostrov", "kuchynská zostava", "umývadlová skrinka"]},
    {"id": "velke-dekoracie", "name": "Veľké dekorácie", "types": ["koberec", "záves", "záclona", "veľký obraz", "nástenná dekorácia", "veľké zrkadlo", "paraván", "stojaca lampa", "veľká rastlina", "socha", "dekoratívny panel", "nástenné hodiny", "vývesný štít", "tabuľa", "nástenná mapa"]},
    {"id": "male-dekoracie", "name": "Malé dekorácie", "types": ["váza", "svietnik", "rámik na fotografiu", "malý obraz", "stolové hodiny", "miska", "podnos", "dekoratívna škatuľa", "figúrka", "kvetináč", "umelá rastlina", "vankúš", "deka", "kniha ako dekorácia", "fľaša", "sviečka", "popolník", "stolová dekorácia"]},
    {"id": "osvetlenie", "name": "Osvetlenie", "types": ["stropné svietidlo", "luster", "nástenné svietidlo", "stojaca lampa", "stolová lampa", "nočná lampa", "pracovná lampa", "dekoratívne svetlo"]},
    {"id": "textil", "name": "Textil", "types": ["posteľná bielizeň", "paplón", "vankúš", "deka", "prehoz", "obrus", "prestieranie", "uterák", "záves", "záclona", "poťah", "koberec"]},
    {"id": "jedalensky-inventar", "name": "Jedálenský inventár", "types": ["tanier", "miska", "šálka", "podšálka", "pohár", "karafa", "džbán", "príbor", "servírovacia misa", "podnos", "kanvica", "cukornička", "mliečnik", "obrúsok", "stojan na obrúsky", "soľnička", "korenička"]},
    {"id": "kuchynsky-inventar", "name": "Kuchynský inventár", "types": ["hrniec", "panvica", "pekáč", "plech", "vareška", "naberačka", "nôž", "doska na krájanie", "cedidlo", "sitko", "odmerka", "misa", "dóza", "kuchynská váha", "kanvica", "kávovar", "mixér", "toastovač", "odkvapkávač"]},
    {"id": "spotrebice-a-technika", "name": "Spotrebiče a technika", "types": ["chladnička", "sporák", "rúra", "mikrovlnná rúra", "umývačka", "práčka", "televízor", "rádio", "gramofón", "telefón", "počítač", "tlačiareň", "reproduktor", "ventilátor", "hodiny", "školská technika"]},
    {"id": "rekvizity", "name": "Rekvizity", "types": ["hracia rekvizita", "ručná rekvizita", "papierová rekvizita", "kniha", "noviny", "listina", "fotografia", "osobný predmet", "školská pomôcka", "kancelárska pomôcka", "gastro rekvizita", "obal alebo etiketa", "fiktívny produkt", "kontinuitná rekvizita"]},
    {"id": "rastliny", "name": "Rastliny a zeleň", "types": ["izbová rastlina", "rezaná kvetina", "kytica", "umelá rastlina", "stromček", "bylinka", "kvetináč", "váza s kvetmi"]},
    {"id": "steny-a-grafika", "name": "Steny, grafika a označenia", "types": ["tapeta", "maľba", "obklad", "nápis", "logo", "smerová tabuľa", "menovka", "plagát", "výveska", "nástenná fotografia", "školská tabuľa", "menu", "cenovka"]},
    {"id": "stavebne-a-fixne-prvky", "name": "Stavebné a fixné prvky", "types": ["dvere", "okno", "zábradlie", "schodisko", "kuchynská linka", "barový pult", "vstavaná skriňa", "radiátor", "krb", "sanita", "umývadlo", "toaleta", "sprcha", "vaňa", "podlahová krytina"]},
]

SPACE_BY_ID = {space["id"]: space for space in SPACES}
CATEGORY_BY_ID = {category["id"]: category for category in CATEGORIES}

DEFAULT_CONTEXT = {
    "space_id": "dom-betty",
    "space_name": "Dom Betty",
    "room": "spálňa / izba",
    "main_category": "nabytok",
    "item_type": "posteľ",
}


def validate_context(values):
    """Return a normalized context using only project-defined values."""
    result = DEFAULT_CONTEXT.copy()
    space = SPACE_BY_ID.get(values.get("space_id"))
    if space:
        result["space_id"] = space["id"]
        result["space_name"] = space["name"]
        if values.get("room") in space["rooms"]:
            result["room"] = values["room"]
        else:
            result["room"] = space["rooms"][0]
    category = CATEGORY_BY_ID.get(values.get("main_category"))
    if category:
        result["main_category"] = category["id"]
        result["item_type"] = values.get("item_type") if values.get("item_type") in category["types"] else category["types"][0]
    return result
