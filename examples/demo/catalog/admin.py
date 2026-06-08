"""Register demo models in the admin so you can browse the seeded data."""

from __future__ import annotations

from django.contrib import admin

from catalog.models import Author, Book

admin.site.register(Author)
admin.site.register(Book)
