from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Place

SOURCE_KINDS = [("book", "книга"), ("archive", "архив"),
                ("link", "ссылка"), ("memory", "личные воспоминания")]


class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")


class PlaceSuggestForm(forms.Form):
    name_ru = forms.CharField(label="Название", max_length=200)
    category = forms.ChoiceField(
        label="Категория", choices=Place._meta.get_field("category").choices)
    address = forms.CharField(label="Адрес", max_length=300, required=False)
    year_from = forms.IntegerField(
        label="Год появления (если известен)", required=False,
        min_value=1000, max_value=2100)
    description_ru = forms.CharField(
        label="Что известно о месте", widget=forms.Textarea)
    source_kind = forms.ChoiceField(label="Тип источника", choices=SOURCE_KINDS)
    source_title = forms.CharField(
        label="Источник (книга, архив, автор или «воспоминания бабушки»)",
        max_length=300)
    source_url = forms.URLField(label="Ссылка на источник", required=False)
    lat = forms.FloatField(
        widget=forms.HiddenInput,
        error_messages={"required": "Нажмите на карту, чтобы выбрать точку."})
    lon = forms.FloatField(
        widget=forms.HiddenInput,
        error_messages={"required": "Нажмите на карту, чтобы выбрать точку."})
    consent = forms.BooleanField(
        label="Я имею право передать этот материал и согласен(на) на его "
              "публикацию под свободной лицензией CC BY-SA")

    def clean(self):
        data = super().clean()
        lat, lon = data.get("lat"), data.get("lon")
        if lat is not None and lon is not None:
            if not (55.8 <= lat <= 56.5 and 46.8 <= lon <= 47.7):
                raise forms.ValidationError(
                    "Точка далеко от Чебоксар. Выберите место на карте города.")
        return data


class PlaceEditForm(forms.Form):
    name_ru = forms.CharField(label="Название", max_length=200)
    address = forms.CharField(label="Адрес", max_length=300, required=False)
    year_from = forms.IntegerField(label="Год появления", required=False)
    year_to = forms.IntegerField(label="Год исчезновения", required=False)
    description_ru = forms.CharField(label="Описание", widget=forms.Textarea)
    source_note = forms.CharField(
        label="Источник правки (книга, архив, ссылка, «воспоминания»)",
        max_length=300)
    comment = forms.CharField(
        label="Комментарий модератору", widget=forms.Textarea, required=False)
    consent = forms.BooleanField(
        label="Я имею право передать этот материал и согласен(на) на его "
              "публикацию под лицензией CC BY-SA")