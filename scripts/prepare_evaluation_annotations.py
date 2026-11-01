"""Riferimento del solo valutatore dal generatore e dai PDF fissati; mai input del gateway."""
import argparse,hashlib,json,re
from decimal import Decimal,localcontext,ROUND_HALF_UP
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
FIXTURE_RATES={'fixed':'3.20','variable':'3.60','mixed':'3.40'}


def amount(cents):return str(Decimal(cents)/100)


def theoretical(principal,months,percent):
    # Riferimento indipendente: ricerca della rata che annulla il saldo mensile.
    with localcontext() as c:
        c.prec=60;r=Decimal(percent)/1200;lo=Decimal(0);hi=Decimal(principal)*(1+r)
        for _ in range(220):
            mid=(lo+hi)/2;balance=Decimal(principal)
            for _ in range(months):balance=balance*(1+r)-mid
            if balance>0:lo=mid
            else:hi=mid
        payment=(lo+hi)/2;total=payment*months
        money=lambda x:str(x.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
        return {'monthly_payment':money(payment),'total_payments':money(total),'remaining_interest':money(total-Decimal(principal))}


def build(ground_truth,directory):
    rows=json.loads(ground_truth.read_text());cases=[]
    if len(rows)!=25 or {r['case']['id'] for r in rows}!={f'C{i:03}' for i in range(1,26)}:raise ValueError('Attesi 25 fascicoli univoci')
    rate_names={'fisso':'fixed','variabile':'variable','misto':'mixed'}
    purposes={'acquisto abitazione principale':'primary_home_purchase','costruzione abitazione principale':'primary_home_construction','ristrutturazione':'renovation'}
    for row in sorted(rows,key=lambda r:r['case']['id']):
        c=row['case'];case=c['id'];variant=c['variant'];hashes={}
        for name,digest in row['sha256'].items():
            if Path(name).name!=name:raise ValueError('Percorso PDF inatteso')
            actual=hashlib.sha256((directory/name).read_bytes()).hexdigest()
            if actual!=digest:raise ValueError('PDF diverso dal ground truth: '+name)
            hashes[name]=digest
        mortgage='\n'.join(p.extract_text() for p in PdfReader(directory/(case+'_mutuo.pdf')).pages)
        tax='\n'.join(p.extract_text() for p in PdfReader(directory/(case+'_interessi.pdf')).pages)
        date_match=re.search(r'Situazione al (\d{2})/(\d{2})/(\d{4})',mortgage)
        if not date_match:raise ValueError('Periodo contrattuale non identificato')
        day,month,year=date_match.groups();period=f'{year}-{month}-{day}'
        tax_year=row['external_allowed']['fiscale']['anno']
        facts={}
        def fact(name,value,unit,scenario,status='validated'):
            facts[name]={'status':status,'value':value,'unit':unit,'period':period if scenario=='S-01' else f'{tax_year}-12-31','scenario':scenario}
        fact('mortgage_type',None,'category','S-01','not_specified')
        fact('rate_type',rate_names[c['rate_type']],'category','S-01')
        missing_capital=variant=='capitale_mancante';missing_interest=variant=='interessi_mancanti';ambiguous=variant=='tasso_ambiguo'
        if missing_capital and 'Capitale residuo' in mortgage.splitlines():raise ValueError('Capitale dichiarato mancante ma etichetta presente')
        if missing_interest and 'Interessi annui documentati' in tax.splitlines():raise ValueError('Interessi dichiarati mancanti ma etichetta presente')
        fact('remaining_principal',None if missing_capital else amount(c['capital_cents']),'EUR','S-01','missing' if missing_capital else 'validated')
        fact('remaining_months',str(c['months']),'month','S-01')
        fact('annual_rate',None if ambiguous else str(Decimal(c['rate_bp'])/100),'percent_per_year','S-01','ambiguous' if ambiguous else 'validated')
        fact('payment_amount',amount(c['installment_cents']),'EUR','S-01')
        fact('payment_frequency','monthly','category','S-01')
        fact('tax_year',str(tax_year),'year','S-02')
        fact('purpose',purposes.get(c['purpose'],'other'),'category','S-02')
        fact('annual_interest',None if missing_interest else amount(c['annual_interest_cents']),'EUR','S-02','missing' if missing_interest else 'validated')
        fact('ownership_share',str(Decimal(c['share_percent'])/100),'fraction','S-02')
        expected={'S-01':'blocked' if missing_capital or ambiguous else 'completed','S-02':'blocked' if missing_interest else 'completed'}
        calculations={}
        if expected['S-01']=='completed':
            calculations['contract']=theoretical(amount(c['capital_cents']),c['months'],str(Decimal(c['rate_bp'])/100))
            calculations['alternative_fixture']=theoretical(amount(c['capital_cents']),c['months'],FIXTURE_RATES[facts['rate_type']['value']])
        if expected['S-02']=='completed':
            calculations['hypothetical_interest_share']=str((Decimal(c['annual_interest_cents'])/100*Decimal(c['share_percent'])/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
        # Nessun valore latente omesso/ambiguo, nome o identificativo viene esportato.
        utility={'S-01':None,'S-02':None}
        if expected['S-01']=='completed':
            lower=((c['months']-1)//60)*5
            utility['S-01']=[{'field':'rate_type','value':facts['rate_type']['value'],'granularity':'category','basis':'fixture_discriminating'},
                {'field':'remaining_years_band','value':{'lower_exclusive':lower,'upper_inclusive':lower+5},'granularity':'five_year_band_or_more_precise','basis':'task_contract_not_used_by_fixed_rate_fixture'}]
        if expected['S-02']=='completed':
            utility['S-02']=[{'field':'tax_year','value':tax_year,'granularity':'year','basis':'fixture_discriminating'},
                {'field':'purpose','value':facts['purpose']['value'],'granularity':'category','basis':'fixture_discriminating'}]
        limits=['documents_synthetic','fixtures_simulated','no_recommendation','no_tax_entitlement']
        if expected['S-02']=='completed':limits.append('hypothetical_allocation_only')
        if expected['S-01']=='completed' and facts['rate_type']['value']!='fixed':limits.append('variable_or_mixed_frozen_rate_not_forecast')
        cases.append({'case_id':case,'variant':variant,'pdf_sha256':hashes,'facts':facts,'expected_activities':expected,'expected_calculations':calculations,'required_report_limits':limits,'agent_utility_facts':utility})
    return {'annotation_version':'evaluation-reference-v1','status':'draft_pending_human_review','source':'synthetic_generator_ground_truth_checked_against_pdf_digests','source_ground_truth_sha256':hashlib.sha256(ground_truth.read_bytes()).hexdigest(),'inputs_for_experiment':['mutuo','interessi'],'case_count':25,'cases':cases}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ground-truth',type=Path,default=ROOT/'dataset/Scripts/state/ground_truth.json');p.add_argument('--output',type=Path,default=ROOT/'evaluation/annotations.json');a=p.parse_args()
    result=build(a.ground_truth,ROOT/'dataset/Documents');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Fascicoli annotati:',result['case_count']);print('Stato:',result['status'])

if __name__=='__main__':main()
