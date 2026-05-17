from enum import StrEnum

from pydantic import BaseModel


class CookieCategory(StrEnum):
    ESSENTIAL = "essential"
    ANALYTICS = "analytics"
    FUNCTIONAL = "functional"
    TARGETING = "targeting"
    UNKNOWN = "unknown"


class LegalExposure(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Vendor(BaseModel):
    name: str
    domains: list[str]
    cookie_names: list[str] = []
    category: CookieCategory
    legal_exposure: LegalExposure = LegalExposure.UNKNOWN
    onetrust_category: str | None = None
    notes: str = ""
