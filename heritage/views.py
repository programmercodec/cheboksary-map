import json
import re
import urllib.parse
import urllib.request

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .forms import PlaceEditForm, PlaceSuggestForm, RegisterForm
from .models import Credibility, Place, PlacePhoto, Source, Status, Suggestion
from .serializers import PlaceDetailSerializer, PlaceListSerializer, pastvu_photo

PASTVU_API = "https://api.pastvu.com/api2"
FILE_RE = re.compile(r"^[A-Za-z0-9/_.\-]+\.(?:jpe?g|png|webp|gif)$")


def fetch_pastvu(lat, lon, distance):
    key = f"pastvu2:{lat:.4f}:{lon:.4f}:{distance}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    params = {"geo": [lat, lon], "distance": distance, "limit": 12}
    url = PASTVU_API + "?" + urllib.parse.urlencode(
        {"method": "photo.giveNearestPhotos", "params": json.dumps(params)})
    req = urllib.request.Request(url, headers={
        "User-Agent": "cheboksary-map/0.1 (local history project)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = json.load(resp)
    photos = []
    for p in raw.get("result", {}).get("photos", []):
        file, cid = p.get("file"), p.get("cid")
        if file and cid:
            photos.append(pastvu_photo(
                cid, file, p.get("title", ""), p.get("year"), p.get("year2")))
    cache.set(key, photos, 60 * 60 * 24)
    return photos


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class PlaceViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = None

    def get_queryset(self):
        qs = Place.objects.filter(status=Status.PUBLISHED)
        p = self.request.query_params
        if p.get("category"):
            qs = qs.filter(category=p["category"])
        if p.get("year", "").lstrip("-").isdigit():
            y = int(p["year"])
            qs = qs.filter(Q(year_from__isnull=True) | Q(year_from__lte=y)) \
                   .filter(Q(year_to__isnull=True) | Q(year_to__gte=y))
        return qs.prefetch_related("sources")

    def get_serializer_class(self):
        return PlaceListSerializer if self.action == "list" else PlaceDetailSerializer

    @action(detail=True, methods=["get"])
    def photos(self, request, pk=None):
        place = self.get_object()
        distance = _int_or_none(request.query_params.get("distance")) or 150
        distance = min(max(distance, 30), 500)
        try:
            photos = fetch_pastvu(place.geom.y, place.geom.x, distance)
        except Exception:
            return Response({"photos": [], "error": "PastVu сейчас недоступен"})
        return Response({"photos": photos})

    @action(detail=True, methods=["post"])
    def pin_photo(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"error": "Нужны права модератора"}, status=403)
        place = self.get_object()
        d = request.data
        cid = _int_or_none(d.get("cid"))
        file = str(d.get("file", ""))
        if cid is None or not FILE_RE.match(file) or ".." in file:
            return Response({"error": "Неверные данные фото"}, status=400)
        PlacePhoto.objects.update_or_create(
            place=place, pastvu_cid=cid,
            defaults={"file": file, "title": str(d.get("title", ""))[:300],
                      "year": _int_or_none(d.get("year")),
                      "year2": _int_or_none(d.get("year2")),
                      "pinned_by": request.user})
        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def unpin_photo(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"error": "Нужны права модератора"}, status=403)
        place = self.get_object()
        place.photos.filter(pastvu_cid=_int_or_none(request.data.get("cid"))).delete()
        return Response({"ok": True})


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("/")
    return render(request, "registration/register.html", {"form": form})


@login_required
def suggest_place(request):
    form = PlaceSuggestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        source = Source.objects.create(
            kind=d["source_kind"], title=d["source_title"], url=d["source_url"])
        place = Place.objects.create(
            name_ru=d["name_ru"], category=d["category"], address=d["address"],
            year_from=d["year_from"], description_ru=d["description_ru"],
            geom=Point(d["lon"], d["lat"], srid=4326),
            credibility=Credibility.REQUIRES_CHECK,
            status=Status.PENDING, author=request.user)
        place.sources.add(source)
        return redirect("thanks")
    return render(request, "suggest_place.html", {"form": form})


def _norm(value):
    if isinstance(value, str):
        return value.replace("\r\n", "\n").strip()
    return value


@login_required
def suggest_edit(request, pk):
    place = get_object_or_404(Place, pk=pk, status=Status.PUBLISHED)
    fields = ["name_ru", "address", "year_from", "year_to", "description_ru"]
    initial = {f: getattr(place, f) for f in fields}
    form = PlaceEditForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        changes = {f: _norm(d[f]) for f in fields if _norm(d[f]) != _norm(initial[f])}
        if not changes:
            form.add_error(None, "Вы ничего не изменили.")
        else:
            Suggestion.objects.create(
                place=place, author=request.user, changes=changes,
                comment=d["comment"], source_note=d["source_note"])
            return redirect("thanks")
    return render(request, "suggest_edit.html", {"form": form, "place": place})