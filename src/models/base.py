"""Base model utilities."""

from pydantic import BaseModel


class AppBaseModel(BaseModel):
    """Shared base for all domain models."""

    class Config:
        from_attributes = True
        populate_by_name = True
