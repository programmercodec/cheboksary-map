import json
import re
import urllib.parse
import urllib.request

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError

from heritage.models import Credibility, Place, Source, Status

ENDPOINT = "https://query.wikidata.org/sparql"
CENTER = (47.2489, 56.1322)  # долгота, широта центра Чебоксар

CATEGORY_HINTS = [
    ("church", r"церков|храм|собор|часовн|монастыр|мечет"),
    ("museum", r"музей"),
    ("monument", r"памятник|скульптур|монумент|мемориал|обелиск"),
    ("park", r"парк|сквер|сад"),
    ("square", r"площад"),
]

QUERY = """
SELECT ?item ?itemLabel ?cv ?desc ?coord ?inception ?classLabel WHERE {{
  SERVICE wikibase:around {{
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "{radius}" .
  }}
  {heritage}
  OPTIONAL {{ ?item wdt:P571 ?inception }}
  OPTIONAL {{ ?item wdt:P31 ?class }}
  OPTIONAL {{ ?item rdfs:label ?cv FILTER(LANG(?cv) = "cv") }}
  OPTIONAL {{ ?item schema:description ?desc FILTER(LANG(?desc) = "ru") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ru,en". }}
}}
"""


def guess_category(class_label):
    text = (class_label or "").lower()
    for key, pattern in CATEGORY_HINTS:
        if re.search(pattern, text):
            return key
    return "building"


class Command(BaseCommand):
    help = "Импорт объектов из Wikidata вокруг Чебоксар (статус «на проверке»)"

    def add_arguments(self, parser):
        parser.add_argument("--radius", type=float, default=8, help="радиус, км")
        parser.add_argument("--all", action="store_true",
                            help="все объекты с координатами, а не только охраняемые")

    def handle(self, *args, **opts):
        heritage = "" if opts["all"] else "?item wdt:P1435 ?heritage ."
        query = QUERY.format(lon=CENTER[0], lat=CENTER[1],
                             radius=opts["radius"], heritage=heritage)
        url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
        req = urllib.request.Request(url, headers={
            "User-Agent": "cheboksary-map/0.1 (local history project)"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                rows = json.load(resp)["results"]["bindings"]
        except Exception as e:
            raise CommandError(f"Не удалось получить данные Wikidata: {e}")

        items = {}
        for r in rows:
            uri = r["item"]["value"]
            it = items.setdefault(uri, {"classes": set()})
            it["name"] = r["itemLabel"]["value"]
            it["coord"] = r["coord"]["value"]
            it["cv"] = r.get("cv", {}).get("value", "")
            it["desc"] = r.get("desc", {}).get("value", "")
            it["inception"] = r.get("inception", {}).get("value", "")
            if "classLabel" in r:
                it["classes"].add(r["classLabel"]["value"])

        created = skipped = 0
        for uri, it in items.items():
            m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", it["coord"])
            if not m or re.match(r"^Q\d+$", it["name"]):  # нет метки на русском/английском
                skipped += 1
                continue
            if Source.objects.filter(url=uri).exists():
                skipped += 1
                continue
            year = None
            ym = re.match(r"^(-?\d{4})", it["inception"])
            if ym:
                year = int(ym.group(1))
            place = Place.objects.create(
                name_ru=it["name"][:200], name_cv=it["cv"][:200],
                category=guess_category(" ".join(it["classes"])),
                geom=Point(float(m.group(1)), float(m.group(2)), srid=4326),
                year_from=year, description_ru=it["desc"],
                credibility=Credibility.REQUIRES_CHECK, status=Status.PENDING)
            place.sources.add(Source.objects.create(
                kind="link", title="Wikidata", url=uri))
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Создано: {created}, пропущено: {skipped}. "
            "Все объекты в статусе «на проверке»."))