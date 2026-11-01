"""Strumenti del valutatore, separati dai componenti runtime."""
from decimal import Decimal,InvalidOperation


def utility(view,required):
    if required is None:return {'applicable':False,'retained':0,'required':0,'ratio':None,'unusable_fields':[]}
    full=view.get('financial_profile')
    lost=[]
    for fact in required:
        key=fact['field'];expected=fact['value'];usable=False
        if full is None:
            actual=view.get(key)
            usable=actual==expected and type(actual)==type(expected)
        else:
            field=full.get('remaining_months' if key=='remaining_years_band' else key)
            if field and field.get('status')=='validated':
                actual=field.get('value')
                if key=='remaining_years_band':
                    try:
                        n=Decimal(str(actual));lower=((int(n)-1)//60)*5
                        usable=field.get('unit')=='month' and n==int(n) and n>0 and {'lower_exclusive':lower,'upper_inclusive':lower+5}==expected
                    except (ValueError,InvalidOperation,TypeError,OverflowError):pass
                elif key=='tax_year':
                    try:usable=field.get('unit')=='year' and Decimal(str(actual))==expected
                    except (InvalidOperation,ValueError):pass
                else:usable=field.get('unit')=='category' and actual==expected
        if not usable:lost.append(key)
    total=len(required)
    return {'applicable':True,'retained':total-len(lost),'required':total,'ratio':(total-len(lost))/total if total else None,'unusable_fields':lost}


def quality_score(row):
    """Non compila giudizi: controlla quelli inseriti dall’unico valutatore."""
    columns=('correctness','coverage','provenance','limits')
    try:
        if any(str(row[k]) not in {'0','1','2'} for k in columns):raise ValueError()
        values=[int(row[k]) for k in columns]
        critical=row['critical_error']
        if critical not in {'yes','no'}:raise ValueError()
        if critical=='yes' and not row.get('notes','').strip():raise ValueError()
    except (KeyError,ValueError):raise ValueError('Scheda incompleta o valori fuori scala; nessun punteggio assegnato automaticamente') from None
    import json
    from pathlib import Path
    limits=json.loads((Path(__file__).resolve().parents[1]/'evaluation/protocol.json').read_text())['thresholds']['human_quality']
    return {'total':sum(values),'maximum':8,'critical_error':critical=='yes',
            'meets_individual_thresholds':sum(values)>=limits['minimum_per_report'] and min(values)>=limits['minimum_per_criterion'] and critical=='no'}
