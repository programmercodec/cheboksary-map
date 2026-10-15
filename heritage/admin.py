from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from .models import Source, Place, Event, Person, Suggestion, Status

ALLOWED_FIELDS = {"name_ru", "name_cv", "old_names", "address",
                  "description_ru", "description_cv", "year_from", "year_to"}

def _set_status(queryset, status):
    for obj in queryset:          # через save(), чтобы попало в историю правок
        obj.status = status
        obj.save()

@admin.action(description="Опубликовать выбранные")
def publish(modeladmin, request, queryset):
    _set_status(queryset, Status.PUBLISHED)

@admin.action(description="Отклонить выбранные")
def reject(modeladmin, request, queryset):
    _set_status(queryset, Status.REJECTED)

@admin.action(description="Принять правку (применить к объекту)")
def accept_suggestion(modeladmin, request, queryset):
    for s in queryset.filter(status=Status.PENDING):
        for field, value in s.changes.items():
            if field in ALLOWED_FIELDS:
                setattr(s.place, field, value)
        s.place.save()
        s.status = Status.PUBLISHED
        s.save()

@admin.register(Place)
class PlaceAdmin(SimpleHistoryAdmin, GISModelAdmin):
    list_display = ("name_ru", "category", "credibility", "status")
    list_filter = ("status", "category", "credibility")
    search_fields = ("name_ru", "name_cv", "address")
    filter_horizontal = ("sources",)
    actions = [publish, reject]
    gis_widget_kwargs = {"attrs": {"default_lon": 47.25, "default_lat": 56.13, "default_zoom": 13}}

@admin.register(Event)
class EventAdmin(SimpleHistoryAdmin):
    list_display = ("title_ru", "start_year", "end_year", "status")
    list_filter = ("status", "kind")
    filter_horizontal = ("places", "sources")
    actions = [publish, reject]

@admin.register(Person)
class PersonAdmin(SimpleHistoryAdmin):
    list_display = ("full_name", "birth_year", "death_year", "is_deceased", "status")
    list_filter = ("status", "is_deceased", "category")
    search_fields = ("full_name",)
    filter_horizontal = ("places", "events", "sources")
    actions = [publish, reject]

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("place", "author", "status", "created")
    list_filter = ("status",)
    actions = [accept_suggestion]

admin.site.register(Source)