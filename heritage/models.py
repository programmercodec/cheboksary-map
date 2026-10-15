from django.contrib.gis.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords


class Credibility(models.TextChoices):
    CONFIRMED = "confirmed", "подтверждено"
    FROM_WORDS = "from_words", "со слов"
    REQUIRES_CHECK = "requires_check", "требует проверки"


class Status(models.TextChoices):
    PENDING = "pending", "на проверке"
    PUBLISHED = "published", "опубликовано"
    REJECTED = "rejected", "отклонено"


class DatePrecision(models.TextChoices):
    EXACT = "exact", "точная"
    YEAR = "year", "год"
    DECADE = "decade", "десятилетие"
    ABOUT = "about", "около"
    RANGE = "range", "диапазон"


class Source(models.Model):
    kind = models.CharField(
        "Тип", max_length=30,
        choices=[("book", "книга"), ("archive", "архив"),
                 ("link", "ссылка"), ("memory", "воспоминание")])
    title = models.CharField("Название", max_length=300)
    url = models.URLField("Ссылка", blank=True)
    details = models.TextField("Реквизиты", blank=True)

    def __str__(self):
        return self.title


class Place(models.Model):
    name_ru = models.CharField("Название", max_length=200)
    name_cv = models.CharField("Название (чув.)", max_length=200, blank=True)
    old_names = models.TextField("Прежние названия", blank=True)
    category = models.CharField(
        "Категория", max_length=30,
        choices=[("church", "храм"), ("museum", "музей"),
                 ("monument", "памятник"), ("park", "парк"),
                 ("square", "площадь"), ("building", "здание"),
                 ("lost", "исчезнувший объект"), ("other", "другое")])
    geom = models.PointField("Точка на карте", srid=4326)
    address = models.CharField("Адрес", max_length=300, blank=True)
    year_from = models.IntegerField("Год появления", null=True, blank=True)
    year_to = models.IntegerField("Год исчезновения", null=True, blank=True)
    date_precision = models.CharField(
        "Точность даты", max_length=10,
        choices=DatePrecision.choices, default=DatePrecision.YEAR)
    description_ru = models.TextField("Описание", blank=True)
    description_cv = models.TextField("Описание (чув.)", blank=True)
    credibility = models.CharField(
        "Достоверность", max_length=20,
        choices=Credibility.choices, default=Credibility.REQUIRES_CHECK)
    status = models.CharField(
        "Статус", max_length=10,
        choices=Status.choices, default=Status.PENDING)
    sources = models.ManyToManyField(Source, blank=True, verbose_name="Источники")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name="Автор")
    history = HistoricalRecords()  # версии и откат правок

    def __str__(self):
        return self.name_ru


class Event(models.Model):
    title_ru = models.CharField("Название", max_length=250)
    title_cv = models.CharField("Название (чув.)", max_length=250, blank=True)
    kind = models.CharField("Тип события", max_length=30, blank=True)
    start_year = models.IntegerField("Год начала", null=True, blank=True)
    end_year = models.IntegerField("Год окончания", null=True, blank=True)
    date_precision = models.CharField(
        "Точность даты", max_length=10,
        choices=DatePrecision.choices, default=DatePrecision.YEAR)
    description = models.TextField("Описание", blank=True)
    places = models.ManyToManyField(
        Place, blank=True, related_name="events", verbose_name="Места")
    sources = models.ManyToManyField(Source, blank=True, verbose_name="Источники")
    credibility = models.CharField(
        "Достоверность", max_length=20,
        choices=Credibility.choices, default=Credibility.REQUIRES_CHECK)
    status = models.CharField(
        "Статус", max_length=10,
        choices=Status.choices, default=Status.PENDING)
    history = HistoricalRecords()

    def __str__(self):
        return self.title_ru


class Person(models.Model):
    full_name = models.CharField("ФИО", max_length=250)
    birth_year = models.IntegerField("Год рождения", null=True, blank=True)
    death_year = models.IntegerField("Год смерти", null=True, blank=True)
    category = models.CharField("Категория", max_length=40, blank=True)
    biography = models.TextField("Биография", blank=True)
    is_deceased = models.BooleanField("Умер(ла)", default=True)
    consent_document = models.CharField(
        "Согласие (если жив)", max_length=300, blank=True)
    author_relation = models.CharField(
        "Кем приходится автору", max_length=100, blank=True)
    places = models.ManyToManyField(
        Place, blank=True, related_name="people", verbose_name="Места")
    events = models.ManyToManyField(
        Event, blank=True, related_name="people", verbose_name="События")
    sources = models.ManyToManyField(Source, blank=True, verbose_name="Источники")
    status = models.CharField(
        "Статус", max_length=10,
        choices=Status.choices, default=Status.PENDING)
    history = HistoricalRecords()

    def __str__(self):
        return self.full_name


class Suggestion(models.Model):
    """Предложение правки к существующему объекту (очередь модерации)."""
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="suggestions",
        verbose_name="Объект")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name="Автор")
    changes = models.JSONField(
        "Изменения", help_text='Например: {"description_ru": "новый текст"}')
    comment = models.TextField("Комментарий", blank=True)
    source_note = models.CharField("Источник", max_length=300)
    status = models.CharField(
        "Статус", max_length=10,
        choices=Status.choices, default=Status.PENDING)
    reject_reason = models.CharField("Причина отказа", max_length=300, blank=True)
    created = models.DateTimeField("Создано", auto_now_add=True)

    def __str__(self):
        return f"Правка к {self.place}"