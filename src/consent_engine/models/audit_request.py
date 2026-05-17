from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class CMPProvider(StrEnum):
    ONETRUST = "onetrust"


class ConsentState(StrEnum):
    OPTED_IN = "opted_in"
    OPTED_OUT = "opted_out"
    GPC_OPTED_OUT = "gpc_opted_out"


class AuditRequest(BaseModel):
    url: str
    cmp_provider: Literal[CMPProvider.ONETRUST] = CMPProvider.ONETRUST
    consent_state: ConsentState = ConsentState.OPTED_OUT
    gtm_container_json: str | None = None
    onetrust_receipt_jwt: str | None = None
    har_file_path: str | None = None
