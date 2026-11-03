"""Contesto documentale facoltativo: importi locali, soli segnali nelle viste."""
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import Field, model_serializer
from .models import Contract

FIELDS = ('payslip_net', 'account_opening_balance', 'account_closing_balance')
MONTHS = {name: i for i, name in enumerate(('gennaio', 'febbraio', 'marzo', 'aprile',
    'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'), 1)}
LIMITS = [
    'Contesto facoltativo: il netto riguarda un solo mese e non dimostra un reddito ricorrente o annuo.',
    'I saldi riguardano un solo conto e un solo mese: non rappresentano il patrimonio complessivo, né la differenza tra saldi equivale a reddito o risparmio.',
    'Nei metadati il periodo mensile è codificato con l’ultimo giorno del mese, non con la data di un movimento.',
    'Il mese di competenza della paga è distinto dalla data di accredito. Periodi diversi restano espliciti e non vengono allineati artificialmente.',
    'Questi dati non dimostrano sostenibilità del mutuo, reddito imponibile annuo o pagamento degli interessi; nessuna detrazione è determinata.',
]


class MonthPeriod(Contract):
    year: int = Field(strict=True, ge=1900, le=2100)
    month: int = Field(strict=True, ge=1, le=12)


class PayslipContext(Contract):
    period: MonthPeriod
    net_sign: Literal['positive', 'zero', 'negative']


class AccountContext(Contract):
    period: MonthPeriod
    closing_balance_sign: Literal['positive', 'zero', 'negative']
    balance_change: Literal['increased', 'unchanged', 'decreased', 'not_comparable']


class DocumentContext(Contract):
    payslip: PayslipContext | None = None
    account: AccountContext | None = None


class ContextView(Contract):
    document_context: DocumentContext | None = None

    @model_serializer(mode='wrap')
    def without_absent_context(self, handler):
        data = handler(self)
        if self.document_context is None:
            data.pop('document_context', None)
        return data


def _fact(profile, key):
    return profile.get(key) if isinstance(profile, dict) else getattr(profile, key, None)


def usable_number(fact):
    if fact is None or fact.status != 'validated' or fact.unit != 'EUR' or not 1900 <= fact.period.year <= 2100:
        return None
    try:
        value = Decimal(str(fact.value))
        return value if value.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def _sign(value):
    return 'positive' if value > 0 else 'negative' if value < 0 else 'zero'


def summarize(profile):
    """Stessa derivazione nelle viste ridotte e nel laboratorio completo."""
    result = {}
    net = _fact(profile, 'payslip_net')
    value = usable_number(net)
    if value is not None:
        result['payslip'] = {'period': {'year': net.period.year, 'month': net.period.month},
                             'net_sign': _sign(value)}
    opening, closing = (_fact(profile, key) for key in FIELDS[1:])
    initial, final = usable_number(opening), usable_number(closing)
    if final is not None:
        change = 'not_comparable'
        if initial is not None and opening.period == closing.period:
            change = 'increased' if final > initial else 'decreased' if final < initial else 'unchanged'
        result['account'] = {'period': {'year': closing.period.year, 'month': closing.period.month},
            'closing_balance_sign': _sign(final), 'balance_change': change}
    return DocumentContext.model_validate(result) if result else None


def source_arguments(view):
    """Il contesto paga/conto serve al ragionamento locale, non alle ricerche pubbliche."""
    data = view.model_dump(mode='json')
    data.pop('document_context', None)
    return data


def context_statements(view, scenario):
    """Enunciati ricostruibili: il modello sceglie, non inventa dati o conclusioni."""
    context = view.document_context
    if context is None:
        return []
    full = hasattr(view, 'financial_profile')
    def refs(kind, names):
        if full:
            fields = ('payslip_net',) if kind == 'payslip' else ('account_closing_balance',)
            if kind == 'account' and context.account.balance_change != 'not_comparable':
                fields += ('account_opening_balance',)
            return [f'context.financial_profile.{key}.{part}' for key in fields for part in ('value', 'period', 'status')]
        return [f'context.document_context.{kind}.{name}' for name in names]
    statements = []
    def add(sid, text, paths):
        statements.append({'statement_id': sid, 'kind': 'context', 'text': text,
                           'references': paths, 'origin': 'authorized_view_derivation'})
    if context.payslip:
        word = {'positive': 'positivo', 'zero': 'pari a zero', 'negative': 'negativo'}[context.payslip.net_sign]
        text = f'La busta paga indica un netto {word} per un solo mese; non dimostra un reddito stabile o annuo.'
        if scenario == 'S-02':
            text += ' Non certifica il reddito imponibile annuo o la spettanza di detrazioni.'
        add('context_single_payslip', text, refs('payslip', ('net_sign', 'period.year', 'period.month')))
    if context.account:
        change = context.account.balance_change
        text = {'increased': 'Il saldo finale è maggiore del saldo iniziale nel mese osservato.',
                'decreased': 'Il saldo finale è minore del saldo iniziale nel mese osservato.',
                'unchanged': 'I saldi iniziale e finale coincidono nel mese osservato.',
                'not_comparable': 'Il saldo finale è disponibile, ma la variazione mensile non è confrontabile.'}[change]
        text += ' Un solo conto e un solo mese non descrivono la liquidità complessiva o il reddito.'
        if scenario == 'S-02':
            text += ' Il saldo non prova il pagamento degli interessi del mutuo.'
        add('context_single_account', text, refs('account', ('balance_change', 'period.year', 'period.month')))
    return statements


def local_context(profile):
    facts = {}
    for name in FIELDS:
        fact = getattr(profile, name)
        if fact is None:
            facts[name] = {'status': 'missing'}
            continue
        data = fact.model_dump(mode='json')
        source = fact.source
        data['provenance_status'] = ('text_span_available' if source.quote is not None and
            source.start is not None and source.end is not None and source.document_sha256 else
            'caller_declared_not_document_verified')
        data['validation_issues'] = [] if usable_number(fact) is not None else ['Valore facoltativo non utilizzabile.']
        facts[name] = data
    reduced = summarize(profile)
    return {'scope': 'optional_single_month_document_context', 'facts': facts,
            'agent_context': reduced.model_dump(mode='json') if reduced else None,
            'limits': LIMITS, 'affordability_assessed': False, 'annual_income_assessed': False,
            'tax_entitlement_assessed': False}
