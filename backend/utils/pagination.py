import math
from dataclasses import dataclass
from typing import List

import sqlalchemy
from fastapi.exceptions import HTTPException


@dataclass
class Pagination:
    query: sqlalchemy.orm.Query
    page: int
    per_page: int
    total: int
    items: List

    @property
    def pages(self):
        """The total number of pages"""
        if self.per_page == 0 or self.total is None:
            pages = 0
        else:
            pages = int(math.ceil(self.total / float(self.per_page)))
        return pages

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert (
            self.query is not None
        ), "a query object is required for this method to work"
        return self.query.paginate(self.page - 1, self.per_page, error_out)

    @property
    def prev_num(self):
        """Number of the previous page."""
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert (
            self.query is not None
        ), "a query object is required for this method to work"
        return self.query.paginate(self.page + 1, self.per_page, error_out)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        if not self.has_next:
            return None
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (
                    num > self.page - left_current - 1
                    and num < self.page + right_current
                )
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def all_results_on_page1(page, items, per_page):
    return page == 1 and len(items) < per_page


def paginate(
    query, page=None, per_page=None, error_out=True, max_per_page=None, count=True
):
    if page is None:
        page = 1

    if per_page is None:
        per_page = 100000

    if max_per_page is not None:
        per_page = min(per_page, max_per_page)

    if page < 1:
        if error_out:
            raise HTTPException(404, "page_token >= 1")
        else:
            page = 1

    if per_page < 0:
        if error_out:
            raise HTTPException(404, "page_size >= 1")
        else:
            per_page = 20

    items = query.limit(per_page).offset((page - 1) * per_page).all()

    if not items and page != 1 and error_out:
        raise HTTPException(404, "no items returned")

    if all_results_on_page1(page, items, per_page):
        total = len(items)
    elif not count:
        total = None
    else:
        total = query.order_by(None).count()

    return Pagination(query, page, per_page, total, items)
