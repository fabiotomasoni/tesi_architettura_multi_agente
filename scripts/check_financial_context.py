"""Controlla il contesto mensile e la sua provenienza, senza voti o inferenze."""
import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

if __package__:
    from .check_report_provenance import verify as provenance
else:
    from check_report_provenance import verify as provenance

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'payslip_net', 'account_opening_balance', 'account_closing_balance'}


def expected_context(facts):
    """Ricalcolo indipendente dai derivatori del gateway."""
    def usable(name):
        f = facts.get(name, {})
        if f.get('status') != 'validated' or f.get('unit') != 'EUR':
            return None
        try:
            n = Decimal(str(f['value']))
            period = date.fromisoformat(f['period'])
            return (n, period) if n.is_finite() and 1900 <= period.year <= 2100 else None
        except (KeyError, ValueError, TypeError, InvalidOperation):
            return None
    def sign(n):
        return 'positive' if n > 0 else 'negative' if n < 0 else 'zero'
    result = {'payslip': None, 'account': None}
    net, opening, closing = (usable(name) for name in ('payslip_net', 'account_opening_balance', 'account_closing_balance'))
    if net:
        result['payslip'] = {'period': {'year': net[1].year, 'month': net[1].month}, 'net_sign': sign(net[0])}
    if closing:
        change = 'not_comparable'
        if opening and opening[1] == closing[1]:
            change = 'increased' if closing[0] > opening[0] else 'decreased' if closing[0] < opening[0] else 'unchanged'
        result['account'] = {'period': {'year': closing[1].year, 'month': closing[1].month},
                            'closing_balance_sign': sign(closing[0]), 'balance_change': change}
    return result if any(result.values()) else None


def verify(report, directory=ROOT/'dataset/Documents'):
    section = report.get('financial_context') or {}
    facts = section.get('facts', {})
    checked, problems = provenance(report, directory)
    return {'optional_context_present': section.get('scope') == 'optional_single_month_document_context',
        'fact_inventory': set(facts) == FIELDS,
        'documentary_provenance': checked > 0 and not problems,
        'monthly_periods_declared': all(f.get('period_granularity') == 'month' for f in facts.values() if f.get('status') != 'missing'),
        'reduced_context_matches_documents': section.get('agent_context') == expected_context(facts),
        'no_affordability_claim': section.get('affordability_assessed') is False,
        'no_annual_income_claim': section.get('annual_income_assessed') is False,
        'no_tax_entitlement_claim': section.get('tax_entitlement_assessed') is False,
        'limits_present': len(section.get('limits', [])) >= 4,
        'no_scenario_field_substitution': all(not FIELDS.intersection(s['facts']) for s in report['document_data'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    try:
        checks = verify(json.loads(args.report.read_text()))
    except (ValueError, KeyError, TypeError, OSError):
        parser.error('Report non leggibile o struttura non valida.')
    for name, passed in checks.items():
        print(name + ':', passed)
    print('passed:', all(checks.values()))
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == '__main__':
    main()
