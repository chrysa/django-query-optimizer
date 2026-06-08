"""Demo of the django-query-optimizer test API.

Two complementary styles:

* ``test_naive_listing_trips_health_gate`` uses the ``assert_query_health``
  pytest fixture (auto-registered by the plugin) to fail a test when the ORM
  health score drops — exactly what you'd add to CI to block an N+1 regression.

* ``test_select_related_is_healthier`` uses the public ``QueryCollector`` +
  ``QueryAnalyzer`` + ``QueryScorer`` API to compare the naive and optimized
  query plans directly.

Run from this directory::

    pytest
"""

from __future__ import annotations

import pytest

from django_query_optimizer import QueryAnalyzer, QueryCollector, QueryScorer
from catalog.models import Author, Book


@pytest.fixture()
def seeded() -> None:
    """Create a few authors with books for the listings to render."""
    for author_name in ("Author A", "Author B", "Author C"):
        author = Author.objects.create(name=author_name)
        Book.objects.bulk_create(Book(title=f"{author_name} {n}", author=author) for n in range(3))


@pytest.mark.django_db()
def test_naive_listing_trips_health_gate(seeded: None, assert_query_health: object) -> None:
    """The naive listing's N+1 drops the health score below a CI gate."""
    list((book.title, book.author.name) for book in Book.objects.all())
    with pytest.raises(AssertionError):
        assert_query_health(min_score=90)  # type: ignore[operator]


@pytest.mark.django_db()
def test_select_related_is_healthier(seeded: None) -> None:
    """select_related runs fewer queries and scores higher than the naive plan."""
    with QueryCollector() as naive:
        list((book.title, book.author.name) for book in Book.objects.all())
    naive_score = QueryScorer(QueryAnalyzer(naive.queries).analyze()).compute()

    with QueryCollector() as optimized:
        list((book.title, book.author.name) for book in Book.objects.select_related("author").all())
    optimized_score = QueryScorer(QueryAnalyzer(optimized.queries).analyze()).compute()

    assert optimized.count < naive.count
    assert optimized_score.value > naive_score.value
    assert optimized_score.grade == "A"
