from fastapi import APIRouter

from src.core.categories import CATEGORIES

router = APIRouter()


@router.get("/categories")
async def get_categories() -> dict[str, list[str]]:
    """Get all available categories with their subcategories."""
    return CATEGORIES
