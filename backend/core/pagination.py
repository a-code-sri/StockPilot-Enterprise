from dataclasses import dataclass

from fastapi import Query, Response

DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


@dataclass(frozen=True)
class Page:
    limit: int
    offset: int


def page_params(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> Page:
    return Page(limit=limit, offset=offset)


def set_total(response: Response, total: int) -> None:
    """List endpoints keep returning a JSON array; the total count goes in a header."""
    response.headers["X-Total-Count"] = str(total)
