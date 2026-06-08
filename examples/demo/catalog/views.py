"""Demo views: one N+1-prone listing and its optimized counterpart."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.urls import reverse

from catalog.models import Book


def index(request: HttpRequest) -> HttpResponse:
    """Landing page linking to the two book listings and the admin dashboard."""
    naive = reverse("books-naive")
    optimized = reverse("books-optimized")
    html = (
        "<h1>django-query-optimizer demo</h1>"
        "<p>Hit each listing, then open the dashboard to compare query counts.</p>"
        "<ul>"
        f'<li><a href="{naive}">/books/naive/</a> — N+1 (one query per author)</li>'
        f'<li><a href="{optimized}">/books/optimized/</a> — fixed with select_related</li>'
        '<li><a href="/admin/django_query_optimizer/querylog/">Query Optimizer dashboard</a></li>'
        "</ul>"
    )
    return HttpResponse(html)


def naive_book_list(request: HttpRequest) -> HttpResponse:
    """List books and their authors WITHOUT select_related.

    Each ``book.author.name`` access issues a separate SQL query, so this view
    runs 1 + N queries. The optimizer records it and flags the N+1 pattern in
    the dashboard.
    """
    books = Book.objects.all()
    rows = "".join(f"<li>{book.title} — {book.author.name}</li>" for book in books)
    return HttpResponse(f"<h1>Books (naive)</h1><ul>{rows}</ul>")


def optimized_book_list(request: HttpRequest) -> HttpResponse:
    """List books and their authors WITH select_related — a single query."""
    books = Book.objects.select_related("author").all()
    rows = "".join(f"<li>{book.title} — {book.author.name}</li>" for book in books)
    return HttpResponse(f"<h1>Books (optimized)</h1><ul>{rows}</ul>")
