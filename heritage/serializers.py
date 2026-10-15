from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Place, Event, Person, Source, Status


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ("kind", "title", "url", "details")


class EventShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ("id", "title_ru", "title_cv", "start_year", "end_year",
                  "date_precision", "credibility")


class PersonShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ("id", "full_name", "birth_year", "death_year", "category")


class PlaceListSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Place
        geo_field = "geom"
        fields = ("id", "name_ru", "name_cv", "category",
                  "year_from", "year_to", "credibility")


class PlaceDetailSerializer(GeoFeatureModelSerializer):
    sources = SourceSerializer(many=True, read_only=True)
    events = serializers.SerializerMethodField()
    people = serializers.SerializerMethodField()

    class Meta:
        model = Place
        geo_field = "geom"
        fields = ("id", "name_ru", "name_cv", "old_names", "category", "address",
                  "year_from", "year_to", "description_ru", "description_cv",
                  "credibility", "sources", "events", "people")

    def get_events(self, obj):
        qs = obj.events.filter(status=Status.PUBLISHED)
        return EventShortSerializer(qs, many=True).data

    def get_people(self, obj):
        qs = obj.people.filter(status=Status.PUBLISHED, is_deceased=True)
        return PersonShortSerializer(qs, many=True).data