"""Contratti del primo confine A2A; nessun dato finanziario esatto."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from .models import Contract


class DurationBand(Contract):
    lower_exclusive: int = Field(ge=0, le=95)
    upper_inclusive: int = Field(ge=5, le=100)

    @model_validator(mode='after')
    def check_band(self):
        if self.lower_exclusive % 5 or self.upper_inclusive != self.lower_exclusive + 5:
            raise ValueError('Fascia non conforme alla policy')
        return self


class MarketView(Contract):
    mortgage_type: Literal['residential', 'other', 'not_specified']
    rate_type: Literal['fixed', 'variable', 'mixed']
    remaining_years_band: DurationBand


class MarketTask(Contract):
    correlation_id: UUID
    scenario: Literal['S-01'] = 'S-01'
    purpose: Literal['market_rate_context'] = 'market_rate_context'
    policy_version: Literal['0.1.0', '0.2.0', '0.3.0'] = '0.3.0'
    deadline: datetime
    view: MarketView

    @model_validator(mode='after')
    def timezone_required(self):
        if self.deadline.tzinfo is None:
            raise ValueError('Scadenza senza fuso orario')
        return self


class RateEvidence(Contract):
    source_id: Literal['simulated-rates-v1'] = 'simulated-rates-v1'
    simulated: Literal[True] = True
    annual_rate_percent: str = Field(pattern=r'^\d{1,2}\.\d{2}$')
    reference_date: Literal['2025-12-31'] = '2025-12-31'
    unit: Literal['percent_per_year'] = 'percent_per_year'


class MarketResult(Contract):
    correlation_id: UUID
    status: Literal['completed', 'failed', 'unverified']
    error_code: Literal['timeout', 'execution_failed', 'missing_provenance'] | None = None
    evidence: RateEvidence | None = None
    summary: str = Field(max_length=2000)
    limits: list[str] = Field(max_length=10)
    model: str
    measurements: dict[str, int | float | str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def provenance_required(self):
        if self.status == 'completed' and self.evidence is None:
            raise ValueError('Provenienza obbligatoria')
        if self.status=='unverified' and (self.evidence is not None or self.error_code!='missing_provenance'):
            raise ValueError('Risultato non verificato incoerente')
        return self


class TaxView(Contract):
    tax_year: int = Field(ge=1900, le=2100)
    expense_category: Literal['mortgage_interest'] = 'mortgage_interest'
    purpose: Literal['primary_home_purchase', 'primary_home_construction', 'renovation', 'other']


class TaxTask(Contract):
    correlation_id: UUID
    scenario: Literal['S-02'] = 'S-02'
    purpose: Literal['tax_context'] = 'tax_context'
    policy_version: Literal['0.2.0', '0.3.0'] = '0.3.0'
    deadline: datetime
    view: TaxView

    @model_validator(mode='after')
    def timezone_required(self):
        if self.deadline.tzinfo is None:
            raise ValueError('Scadenza senza fuso orario')
        return self


class TaxEvidence(Contract):
    source_id: Literal['simulated-tax-v1'] = 'simulated-tax-v1'
    simulated: Literal[True] = True
    tax_year: int = Field(ge=1900, le=2100)
    purpose: Literal['primary_home_purchase', 'primary_home_construction', 'renovation', 'other']
    reference: Literal['DEMO-TAX-001'] = 'DEMO-TAX-001'
    conditions: list[str] = Field(min_length=1, max_length=10)


class TaxResult(MarketResult):
    evidence: TaxEvidence | None = None
