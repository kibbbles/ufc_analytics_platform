"""schemas/shared.py — Reusable building blocks shared across schema modules."""

from pydantic import BaseModel, ConfigDict


class PaginationMeta(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    page: int
    page_size: int
    total: int
    total_pages: int
