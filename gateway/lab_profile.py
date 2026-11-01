"""Profilo finanziario del solo laboratorio sintetico: niente PDF, testo o identificativi."""
from datetime import date
from decimal import Decimal,InvalidOperation
from typing import Literal
from pydantic import model_validator
from .models import Contract,Profile
from .policy import CATEGORIES,UNITS


class FinancialFact(Contract):
    value: str
    unit: Literal['EUR','month','percent_per_year','year','fraction','category']
    period: date
    status: Literal['validated','ambiguous','unvalidated']


class FullFinancialView(Contract):
    financial_profile: dict[str,FinancialFact | None]

    @model_validator(mode='after')
    def closed_profile(self):
        if set(self.financial_profile)!=set(Profile.model_fields):raise ValueError('Campi finanziari inattesi o mancanti')
        for key,fact in self.financial_profile.items():
            if fact is None:continue
            if key in CATEGORIES:
                if fact.unit!='category' or fact.value not in CATEGORIES[key]:raise ValueError('Categoria finanziaria non ammessa')
            else:
                if fact.unit!=UNITS[key]:raise ValueError('Unità finanziaria non ammessa')
                if fact.value=='ambiguous' and fact.status!='validated':continue
                try:
                    if not Decimal(fact.value).is_finite():raise ValueError('Valore non finito')
                except InvalidOperation:raise ValueError('Il laboratorio non ammette testo libero') from None
        return self

    @property
    def rate_type(self):return self.financial_profile['rate_type'].value
    @property
    def tax_year(self):return int(self.financial_profile['tax_year'].value)
    @property
    def purpose(self):return self.financial_profile['purpose'].value


def full_view(profile):
    data={name:({'value':str(f.value),'unit':f.unit,'period':f.period.isoformat(),'status':f.status} if f else None) for name,f in profile}
    return FullFinancialView(financial_profile=data).model_dump(mode='json')


def inspectable_view(data):
    """Convalida del profilo chiuso prima di escluderne i valori dal filtro di minimizzazione."""
    return FullFinancialView.model_validate(data).model_dump(mode='json')
