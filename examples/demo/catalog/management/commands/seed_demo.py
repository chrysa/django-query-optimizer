"""Populate the demo database with authors and books.

Run once after migrating::

    python manage.py seed_demo
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from catalog.models import Author, Book

AUTHORS = ["Ursula K. Le Guin", "Terry Pratchett", "N. K. Jemisin", "Iain M. Banks"]
BOOKS_PER_AUTHOR = 5


class Command(BaseCommand):
    """Seed the catalog with a handful of authors and books."""

    help = "Populate the demo database with sample authors and books."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create authors and books, skipping work if data already exists."""
        if Book.objects.exists():
            self.stdout.write("Demo data already present — nothing to do.")
            return

        for author_name in AUTHORS:
            author = Author.objects.create(name=author_name)
            Book.objects.bulk_create(
                Book(title=f"{author_name} — Volume {n}", author=author)
                for n in range(1, BOOKS_PER_AUTHOR + 1)
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {Author.objects.count()} authors and {Book.objects.count()} books."
            )
        )
