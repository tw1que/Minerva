from __future__ import annotations


def normalize_pagination(
    page: int = 1,
    page_size: int = 25,
    max_size: int = 100,
) -> tuple[int, int, int]:
    safe_page = 1 if page < 1 else page
    safe_size = 25 if page_size < 1 else min(page_size, max_size)
    offset = (safe_page - 1) * safe_size
    return safe_page, safe_size, offset
