from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from heritage import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("heritage.urls")),
    path("accounts/register/", views.register, name="register"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("suggest/", views.suggest_place, name="suggest_place"),
    path("suggest/person/", views.suggest_person, name="suggest_person"),
    path("places/<int:pk>/suggest/", views.suggest_edit, name="suggest_edit"),
    path("people/", views.people_list, name="people"),
    path("people/<int:pk>/", views.person_detail, name="person"),
    path("events/", views.events_list, name="events"),
    path("events/<int:pk>/", views.event_detail, name="event"),
    path("search/", views.search, name="search"),
    path("rules/", TemplateView.as_view(template_name="rules.html"), name="rules"),
    path("privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"),
    path("thanks/", TemplateView.as_view(template_name="thanks.html"), name="thanks"),
    path("", TemplateView.as_view(template_name="index.html")),
]