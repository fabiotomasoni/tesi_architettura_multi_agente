"""Controllo locale indipendente della sola ripartizione ipotetica, non della fiscalità."""
import argparse,json
from fractions import Fraction
from pathlib import Path


def verify(report):
    application=report['tax_application']
    checks={'no_deduction':application['deduction_calculated'] is False,
            'no_entitlement':application['tax_entitlement']=='not_assessed',
            'no_recommendation':application['personalized_recommendation'] is False}
    if application['status']!='calculated':
        checks['not_calculated_as_declared']=True
        return checks
    facts=next(s['facts'] for s in report['document_data'] if s['scenario']=='S-02')
    interest=str(facts['annual_interest']['value']);share=str(facts['ownership_share']['value'])
    # Razionali e arrotondamento intero, indipendenti dal Decimal del calcolatore.
    cents=Fraction(interest)*Fraction(share)*100
    rounded=(2*cents.numerator+cents.denominator)//(2*cents.denominator)
    context=application['documentary_context']
    checks['documentary_values_preserved']=Fraction(context['annual_interest_EUR'])==Fraction(interest) and Fraction(context['ownership_share'])==Fraction(share)
    checks['context_preserved']=context['tax_year']==int(facts['tax_year']['value']) and context['purpose']==facts['purpose']['value']
    checks['hypothetical_product']=Fraction(application['hypothetical_allocation']['amount_EUR'])*100==rounded
    checks['not_documented_personal_amount']=application['hypothetical_allocation']['documented_as_personal_amount'] is False
    checks['simulated_source']=application['source']['simulated'] is True
    checks['assumptions_present']=bool(application['assumptions']) and bool(application['limits'])
    return checks


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);args=parser.parse_args()
    checks=verify(json.loads(args.report.read_text()))
    for key,value in checks.items():print(key+': '+str(value))
    raise SystemExit(0 if all(checks.values()) else 1)

if __name__=='__main__':main()
