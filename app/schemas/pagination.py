from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic pagination schema to standardize list responses across the API.
    Follows DRY principles by accepting any Pydantic model as a type parameter.
    """
    items: list[T] = Field(description="List of records for the current page")
    total: int = Field(description="Total number of records matching the query")
    page: int = Field(description="Current page number")
    size: int = Field(description="Number of records per page")
    pages: int = Field(description="Total number of available pages")

    model_config = ConfigDict(from_attributes=True)