"""Policy deterministica e validazione semantica del solo ingresso JSON."""
from decimal import Decimal, InvalidOperation
from .models import Profile, Scenario

POLICY_VERSION = "0.1.0"
REQUIRED = {
    Scenario.MORTGAGE: ("mortgage_type", "rate_type", "remaining_principal", "remaining_months", "annual_rate", "payment_amount", "payment_frequency"),
    Scenario.TAX: ("tax_year", "purpose", "annual_interest", "ownership_share"),
}
CATEGORIES = {
    "mortgage_type": {"residential", "other"},
    "rate_type": {"fixed", "variable", "mixed"},
    "payment_frequency": {"monthly", "quarterly", "semiannual", "annual"},
    "purpose": {"primary_home_purchase", "primary_home_construction", "other"},
}
UNITS = {"remaining_principal": "EUR", "remaining_months": "month", "annual_rate": "percent_per_year", "payment_amount": "EUR", "tax_year": "year", "annual_interest": "EUR", "ownership_share": "fraction"}


def issues(profile: Profile, scenario: Scenario) -> list[dict]:
    problems = []
    for name in REQUIRED[scenario]:
        fact = getattr(profile, name)
        reason = None
        if fact is None:
            reason = "Campo obbligatorio mancante"
        elif fact.status != "validated":
            reason = "Campo non validato o ambiguo"
        elif name in CATEGORIES:
            if fact.unit != "category" or fact.value not in CATEGORIES[name]:
                reason = "Categoria o unità non ammessa"
        else:
            try:
                number = Decimal(str(fact.value))
                if not number.is_finite() or fact.unit != UNITS[name]:
                    reason = "Valore o unità non valido"
                elif name in {"remaining_months", "tax_year"} and number != number.to_integral_value():
                    reason = "È richiesto un intero"
                elif name == "tax_year" and not 1900 <= number <= 2100:
                    reason = "Anno fuori intervallo"
                elif name == "ownership_share" and not 0 < number <= 1:
                    reason = "Quota fuori intervallo"
                elif name == "annual_rate" and not 0 <= number <= 100:
                    reason = "Tasso fuori intervallo"
                elif name == "annual_interest" and number < 0:
                    reason = "Interessi negativi"
                elif name not in {"tax_year", "ownership_share", "annual_rate", "annual_interest"} and number <= 0:
                    reason = "Valore non positivo"
            except (InvalidOperation, ValueError):
                reason = "Valore numerico non valido"
        if reason:
            problems.append({"field": name, "reason": reason})
    # Per S-01 i valori contrattuali devono descrivere la stessa situazione.
    if scenario == Scenario.MORTGAGE:
        periods = {getattr(profile, n).period for n in REQUIRED[scenario] if getattr(profile, n) is not None}
        if len(periods) > 1:
            problems.append({"field": "period", "reason": "Date contrattuali non allineate"})
    if scenario == Scenario.TAX and profile.tax_year and profile.annual_interest:
        try:
            if int(str(profile.tax_year.value)) != profile.annual_interest.period.year:
                problems.append({"field": "period", "reason": "Interessi non riferiti all'anno d'imposta"})
        except ValueError:
            pass
    return problems


def make_view(profile: Profile, scenario: Scenario) -> dict:
    if scenario == Scenario.MORTGAGE:
        months = int(str(profile.remaining_months.value))
        # Fasce (0,60], (60,120], ...: nessun valore esatto nella vista.
        lower = ((months - 1) // 60) * 5
        return {"mortgage_type": profile.mortgage_type.value, "rate_type": profile.rate_type.value,
                "remaining_years_band": {"lower_exclusive": lower, "upper_inclusive": lower + 5}}
    return {"tax_year": int(str(profile.tax_year.value)), "expense_category": "mortgage_interest", "purpose": profile.purpose.value}
