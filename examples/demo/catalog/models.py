"""Demo models with a classic one-to-many relation prone to N+1 access."""

from __future__ import annotations

from django.db import models


class Author(models.Model):
    """A book author."""

    name = models.CharField(max_length=200)

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    """A book, related to exactly one author.

    Iterating books and touching ``book.author`` without ``select_related``
    triggers one extra query per book — the N+1 pattern the optimizer flags.
    """

    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")

    def __str__(self) -> str:
        return self.title
