"""Contratti provvisori: input strutturato, nessuna estrazione documentale."""
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Scenario(str, Enum):
    MORTGAGE = "S-01"
    TAX = "S-02"


class Source(Contract):
    # Codice opaco, non percorso del file o testo originale.
    document_id: Annotated[str, Field(pattern=r"^doc-[a-zA-Z0-9-]{1,40}$")]
    page: Annotated[int, Field(strict=True, ge=1)]


class Fact(Contract):
    value: str | Decimal | int
    unit: str
    period: date
    source: Source
    status: Literal["validated", "ambiguous", "unvalidated"] = "unvalidated"


class Profile(Contract):
    mortgage_type: Fact | None = None
    rate_type: Fact | None = None
    remaining_principal: Fact | None = None
    remaining_months: Fact | None = None
    annual_rate: Fact | None = None
    payment_amount: Fact | None = None
    payment_frequency: Fact | None = None
    tax_year: Fact | None = None
    purpose: Fact | None = None
    annual_interest: Fact | None = None
    ownership_share: Fact | None = None


class SessionInput(Contract):
    scenarios: Annotated[list[Scenario], Field(min_length=1, max_length=2)]
    profile: Profile


class ViewRequest(Contract):
    scenario: Scenario
    recipient: Literal["markets", "tax"]
