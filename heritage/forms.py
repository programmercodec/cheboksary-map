from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.safestring import mark_safe

from .models import Place

SOURCE_KINDS = [("book", "книга"), ("archive", "архив"),
                ("link", "ссылка"), ("memory", "личные воспоминания")]

PERSON_CATEGORIES = [(c, c) for c in (
    "участник ВОВ", "труженик тыла", "ветеран труда", "деятель культуры",
    "учёный", "спортсмен", "человек с интересной судьбой")]

LICENSE_LABEL = ("Я имею право передать этот материал и согласен(на) на его "
                 "публикацию под свободной лицензией CC BY-SA")


class RegisterForm(UserCreationForm):
    consent = forms.BooleanField(label=mark_safe(
        'Я согласен(на) на обработку персональных данных согласно '
        '<a href="/privacy/" target="_blank">политике конфиденциальности</a>'))

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
    consent = forms.BooleanField(label=LICENSE_LABEL)

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
    consent = forms.BooleanField(label=LICENSE_LABEL)


class PersonSuggestForm(forms.Form):
    full_name = forms.CharField(label="ФИО", max_length=250)
    birth_year = forms.IntegerField(
        label="Год рождения", required=False, min_value=1000, max_value=2100)
    death_year = forms.IntegerField(
        label="Год смерти", required=False, min_value=1000, max_value=2100)
    category = forms.ChoiceField(label="Категория", choices=PERSON_CATEGORIES)
    biography = forms.CharField(
        label="Биография: где жил, работал, воевал, чем известен",
        widget=forms.Textarea)
    author_relation = forms.CharField(
        label="Кем он(а) вам приходится (или «краевед», «исследователь»)",
        max_length=100)
    source_kind = forms.ChoiceField(label="Тип источника", choices=SOURCE_KINDS)
    source_title = forms.CharField(
        label="Источник (документ, книга, архив или «рассказ бабушки»)",
        max_length=300)
    source_url = forms.URLField(
        label="Ссылка на источник (например, «Подвиг народа»)", required=False)
    deceased = forms.BooleanField(
        label="Этого человека нет в живых. Данные живых людей на сайте "
              "публикуются только с письменным согласием через модератора")
    consent = forms.BooleanField(label=LICENSE_LABEL)

    def clean(self):
        data = super().clean()
        b, d = data.get("birth_year"), data.get("death_year")
        if b and d and d < b:
            raise forms.ValidationError("Год смерти раньше года рождения.")
        return data