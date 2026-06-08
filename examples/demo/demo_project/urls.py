"""URL configuration for the demo project."""

from __future__ import annotations

from django.contrib import admin
from django.urls import path

from catalog import views

urlpatterns = [
    path("", views.index, name="index"),
    # Triggers an N+1 query pattern — one query per book to fetch its author.
    path("books/naive/", views.naive_book_list, name="books-naive"),
    # Same data, fixed with select_related — a single query.
    path("books/optimized/", views.optimized_book_list, name="books-optimized"),
    path("admin/", admin.site.urls),
]
