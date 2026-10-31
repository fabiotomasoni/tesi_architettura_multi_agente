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


def verify_comparison(report):
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


def verify_contract(report):
    local=report.get('mortgage_contract_analysis')
    if local is None:
        return {'contract_analysis_present':False} if report.get('report_version')=='0.11.0' else {}
    checks={'contract_no_recommendation':local['personalized_recommendation'] is False,
            'contract_no_alternative':not any(k in local for k in ('alternative_source','simulated_rate_scenario','difference_contract_minus_simulated'))}
    facts=next(d['facts'] for d in report['document_data'] if d['scenario']=='S-01')
    if local['status']!='calculated':
        reason=local.get('reason')
        invalid=any(facts[n].get('status')!='validated' or facts[n].get('validation_issues') for n in ('remaining_principal','remaining_months','annual_rate','payment_amount','payment_frequency','rate_type'))
        checks['contract_not_calculated_reason']=(reason=='input_not_ready' and invalid or
            reason=='unresolved_conflict' and report['consistency']['unresolved_conflicts']>0 or
            reason=='unsupported_payment_frequency' and facts['payment_frequency'].get('value')!='monthly' or
            reason=='unsupported_model_parameters' and int(facts['remaining_months']['value'])>1200)
        checks['contract_no_applied_assumptions']=local['assumptions']==[]
        return checks
    with localcontext() as ctx:
        ctx.prec=60
        principal=Decimal(facts['remaining_principal']['value']);months=int(facts['remaining_months']['value'])
        rate=Decimal(facts['annual_rate']['value']);documented=Decimal(facts['payment_amount']['value'])
        value=reference(principal,months,rate);scenario=local['contract_rate_scenario']
        required=('remaining_principal','remaining_months','annual_rate','payment_amount','payment_frequency','rate_type')
        checks.update(
            contract_inputs_validated=all(facts[n].get('status')=='validated' and not facts[n].get('validation_issues') for n in required) and len({facts[n]['period'] for n in required})==1 and facts['payment_frequency']['value']=='monthly' and not report['consistency']['unresolved_conflicts'],
            contract_rate_matches_document=Decimal(scenario['annual_rate_percent'])==rate,
            contract_monthly_payment=scenario['theoretical_monthly_payment']==money(value),
            contract_totals=scenario['theoretical_total_payments']==money(value*months) and scenario['theoretical_total_interest']==money(value*months-principal),
            contract_document_payment_preserved=Decimal(local['documented_monthly_payment'])==documented,
            contract_difference=local['documented_vs_model']['difference_documented_minus_model']==money(documented-value),
            contract_match_flag=local['documented_vs_model']['matches_rounded_model']==(documented==Decimal(money(value))),
            contract_inputs=Decimal(local['inputs']['remaining_principal'])==principal and local['inputs']['remaining_months']==months and local['inputs']['reference_date']==facts['annual_rate']['period'] and local['inputs']['rate_type']==facts['rate_type']['value'],
            contract_assumptions_explicit=bool(local['assumptions']) and bool(local['limits']),
            contract_variable_limit=facts['rate_type']['value']=='fixed' or any('non previsione' in t for t in local['limits']))
    return checks


def verify(report):
    return {**verify_comparison(report),**verify_contract(report)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);args=parser.parse_args()
    checks=verify(json.loads(args.report.read_text()))
    for key,value in checks.items():print(key+': '+str(value))
    raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
