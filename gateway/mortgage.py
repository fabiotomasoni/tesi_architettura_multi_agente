"""Scenari matematici locali a tasso costante: nessuna raccomandazione."""
from decimal import Decimal, localcontext, ROUND_HALF_UP
from .models import Scenario
from .policy import issues, make_view
from .agent_contracts import MarketView, is_ecb_evidence
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
    def not_calculated(reason, **context):
        # Le ipotesi del modello e le note della fixture valgono solo per un calcolo eseguito.
        return {**base, 'assumptions': [],
                'limits': ['Calcolo non eseguito; nessun risultato numerico derivato o conclusione personalizzata.'],
                'status': 'not_calculated', 'reason': reason, **context}

    if has_conflicts:return not_calculated('unresolved_conflict')
    if issues(profile,Scenario.MORTGAGE):return not_calculated('input_not_ready')
    if profile.payment_frequency.value!='monthly':return not_calculated('unsupported_payment_frequency')
    if activity['status']!='completed' or not activity.get('result',{}).get('evidence'):
        return not_calculated('market_evidence_unavailable')
    evidence,digest=verify_evidence(activity['result']['evidence'],MarketView.model_validate(make_view(profile,Scenario.MORTGAGE)))
    if is_ecb_evidence(evidence):
        return not_calculated('incompatible_market_measure',
                limits=['La serie BCE AAR/NDER è aggregata e non è un TAN o un’offerta: non usata nella formula della rata.'],
                documented_monthly_payment=money(Decimal(str(profile.payment_amount.value))),
                context_source={'source_id':evidence.source_id,'observation_period':evidence.observation_period,'measure':evidence.measure})
    principal=Decimal(str(profile.remaining_principal.value));months=int(str(profile.remaining_months.value))
    current=Decimal(str(profile.annual_rate.value));alternative=Decimal(evidence.annual_rate_percent)
    try:
        current_payment=payment(principal,months,current)
        alternative_payment=payment(principal,months,alternative)
    except ValueError:return not_calculated('unsupported_model_parameters')
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


def analyze_contract(profile, *, has_conflicts=False):
    """Modello locale documentale, indipendente da agenti, fonti o offerte alternative."""
    base={'model_version':'0.1.0','method':'constant_monthly_payment','unit':'EUR',
          'personalized_recommendation':False,'assumptions':[],'limits':[]}
    def unavailable(reason):
        return {**base,'status':'not_calculated','reason':reason,
                'limits':['Modello contrattuale non calcolato; nessun valore mancante stimato.']}
    if has_conflicts:return unavailable('unresolved_conflict')
    if issues(profile,Scenario.MORTGAGE):return unavailable('input_not_ready')
    if profile.payment_frequency.value!='monthly':return unavailable('unsupported_payment_frequency')
    principal=Decimal(str(profile.remaining_principal.value))
    months=int(str(profile.remaining_months.value))
    rate=Decimal(str(profile.annual_rate.value))
    documented=Decimal(str(profile.payment_amount.value))
    try:
        with localcontext() as ctx:
            ctx.prec=50
            installment=payment(principal,months,rate)
            total=installment*months
            values={'annual_rate_percent':str(rate),'theoretical_monthly_payment':money(installment),
                    'theoretical_total_payments':money(total),'theoretical_total_interest':money(total-principal)}
            difference=money(documented-installment)
    except ValueError:return unavailable('unsupported_model_parameters')
    assumptions=[
        'Capitale e durata residui, TAN e rata provengono dalla medesima situazione documentale.',
        'Ammortamento teorico a rate mensili posticipate costanti; tasso mensile pari al TAN diviso 12.',
        'TAN mantenuto costante per tutta la durata residua ipotetica.',
        'Costi, imposte, assicurazioni e condizioni accessorie non sono inclusi nel modello.',
        'Totali dalla rata non arrotondata; importi esposti arrotondati ai centesimi.']
    limits=[
        'Ricostruzione teorica, non verifica esaustiva del piano di ammortamento contrattuale.',
        'Interessi residui teorici, non interessi già pagati né interessi fiscalmente detraibili.',
        'Nessuna offerta alternativa utilizzata; nessuna conclusione di convenienza o risparmio.']
    if profile.rate_type.value!='fixed':
        limits.append('Mutuo variabile o misto: scenario a tasso congelato, non previsione delle rate future.')
    return {**base,'status':'calculated','calculation_type':'documentary_contract_model_only',
        'input_refs':{n:f'document_data/S-01/facts/{n}' for n in ['remaining_principal','remaining_months','annual_rate','payment_amount','payment_frequency','rate_type']},
        'inputs':{'remaining_principal':money(principal),'remaining_months':months,
                  'reference_date':profile.annual_rate.period.isoformat(),'rate_type':profile.rate_type.value},
        'documented_monthly_payment':money(documented),'contract_rate_scenario':values,
        'documented_vs_model':{'difference_documented_minus_model':difference,
            'matches_rounded_model':documented==Decimal(values['theoretical_monthly_payment']),
            'interpretation':'Lo scostamento non corregge la rata documentale e non prova da solo un errore del contratto.'},
        'assumptions':assumptions,'limits':limits}
