"""Scenari matematici locali a tasso costante: nessuna raccomandazione."""
from decimal import Decimal, localcontext, ROUND_HALF_UP
from .models import Scenario
from .policy import issues, make_view
from .agent_contracts import MarketView
from .market_evidence import verify_evidence


def payment(principal: Decimal, months: int, annual_percent: Decimal) -> Decimal:
    if not principal.is_finite() or principal<=0 or type(months) is not int or not 1<=months<=1200 or not annual_percent.is_finite() or not 0<=annual_percent<=100:
        raise ValueError('Parametri del modello non supportati')
    with localcontext() as ctx:
        ctx.prec=50
        rate=annual_percent/Decimal(1200)
        return principal/Decimal(months) if rate==0 else principal*rate/(1-(1+rate)**(-months))


def money(value):return str(value.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))


def compare_mortgage(profile, activity, *, has_conflicts=False):
    base={'model_version':'0.1.0','method':'constant_monthly_payment','unit':'EUR','personalized_recommendation':False,
        'assumptions':['Stesso capitale residuo e stessa durata per i due scenari.',
            'Rate mensili posticipate costanti; tasso mensile pari al tasso annuo nominale diviso 12.',
            'Tassi mantenuti costanti per tutta la durata ipotetica.',
            'Costi, imposte, assicurazioni e variazioni contrattuali esclusi perché non documentati.',
            'Totali teorici da rata non arrotondata; solo gli importi esposti sono arrotondati ai centesimi.'],
        'limits':['Tasso alternativo simulato: non è un’offerta reale.',
            'Differenze matematiche, non risparmio garantito né convenienza contrattuale.']}
    if has_conflicts:return {**base,'status':'not_calculated','reason':'unresolved_conflict'}
    if issues(profile,Scenario.MORTGAGE):return {**base,'status':'not_calculated','reason':'input_not_ready'}
    if profile.payment_frequency.value!='monthly':return {**base,'status':'not_calculated','reason':'unsupported_payment_frequency'}
    if activity['status']!='completed' or not activity.get('result',{}).get('evidence'):
        return {**base,'status':'not_calculated','reason':'market_evidence_unavailable'}
    evidence,digest=verify_evidence(activity['result']['evidence'],MarketView.model_validate(make_view(profile,Scenario.MORTGAGE)))
    principal=Decimal(str(profile.remaining_principal.value));months=int(str(profile.remaining_months.value))
    current=Decimal(str(profile.annual_rate.value));alternative=Decimal(evidence.annual_rate_percent)
    try:
        current_payment=payment(principal,months,current)
        alternative_payment=payment(principal,months,alternative)
    except ValueError:return {**base,'status':'not_calculated','reason':'unsupported_model_parameters'}
    documented=Decimal(str(profile.payment_amount.value))
    if profile.rate_type.value!='fixed':base['limits'].append('Mutuo variabile o misto: scenari a tasso congelato, non previsioni delle rate future.')
    def scenario(rate,amount):
        total=amount*months
        return {'annual_rate_percent':str(rate),'theoretical_monthly_payment':money(amount),
            'theoretical_total_payments':money(total),'theoretical_total_interest':money(total-principal)}
    return {**base,'status':'calculated','input_refs':{n:f'document_data/S-01/facts/{n}' for n in ['remaining_principal','remaining_months','annual_rate','payment_amount','payment_frequency','rate_type']},
        'inputs':{'remaining_principal':money(principal),'remaining_months':months,'reference_date':profile.annual_rate.period.isoformat()},
        'alternative_source':{'source_id':evidence.source_id,'source_sha256':digest,'simulated':True,'reference_date':evidence.reference_date},
        'documented_monthly_payment':money(documented),
        'documented_vs_model':{'difference_documented_minus_model':money(documented-current_payment),
            'matches_rounded_model':documented==Decimal(money(current_payment)),
            'interpretation':'Eventuale scostamento dal modello non modifica il valore documentale e non prova da solo un errore del contratto.'},
        'contract_rate_scenario':scenario(current,current_payment),'simulated_rate_scenario':scenario(alternative,alternative_payment),
        'difference_contract_minus_simulated':{'monthly_payment':money(current_payment-alternative_payment),
            'total_interest':money((current_payment-alternative_payment)*months),
            'sign_convention':'Positivo: scenario simulato inferiore; negativo: scenario simulato superiore. Nessuna conclusione di convenienza.'}}
