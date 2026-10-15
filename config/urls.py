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
    path("places/<int:pk>/suggest/", views.suggest_edit, name="suggest_edit"),
    path("thanks/", TemplateView.as_view(template_name="thanks.html"), name="thanks"),
    path("", TemplateView.as_view(template_name="index.html")),
]