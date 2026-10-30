"""Verifica indipendente delle rate con ricerca numerica sul saldo mensile."""
import argparse,json
from decimal import Decimal,localcontext,ROUND_HALF_UP
from pathlib import Path


def reference(principal,months,percent):
    rate=percent/1200
    low=Decimal(0);high=principal*(1+rate)
    for _ in range(220):
        installment=(low+high)/2
        balance=principal
        for _ in range(months):balance=balance*(1+rate)-installment
        if balance>0:low=installment
        else:high=installment
    return (low+high)/2


def money(value):return str(value.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))


def verify(report):
    comparison=report['mortgage_comparison']
    if comparison['status']!='calculated':return {'not_calculated_as_declared':True}
    facts=next(d['facts'] for d in report['document_data'] if d['scenario']=='S-01')
    with localcontext() as ctx:
        ctx.prec=60
        principal=Decimal(str(facts['remaining_principal']['value']));months=int(facts['remaining_months']['value'])
        checks={};amounts=[]
        for key in ['contract_rate_scenario','simulated_rate_scenario']:
            scenario=comparison[key]
            value=reference(principal,months,Decimal(scenario['annual_rate_percent']))
            amounts.append(value)
            checks[key]=scenario['theoretical_monthly_payment']==money(value) and scenario['theoretical_total_payments']==money(value*months) and scenario['theoretical_total_interest']==money(value*months-principal)
        source=next(s['evidence'] for s in report['simulated_sources'] if s['scenario']=='S-01')
        checks['rates_match_sources']=Decimal(comparison['contract_rate_scenario']['annual_rate_percent'])==Decimal(str(facts['annual_rate']['value'])) and Decimal(comparison['simulated_rate_scenario']['annual_rate_percent'])==Decimal(source['annual_rate_percent'])
        checks['differences']=comparison['difference_contract_minus_simulated']['monthly_payment']==money(amounts[0]-amounts[1]) and comparison['difference_contract_minus_simulated']['total_interest']==money((amounts[0]-amounts[1])*months)
        checks['document_payment_preserved']=Decimal(comparison['documented_monthly_payment'])==Decimal(str(facts['payment_amount']['value']))
        checks['no_recommendation']=comparison['personalized_recommendation'] is False
        return checks


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);args=parser.parse_args()
    checks=verify(json.loads(args.report.read_text()))
    for key,value in checks.items():print(key+': '+str(value))
    raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
