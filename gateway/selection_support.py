"""Utility locali condivise dalle selezioni mercati/fiscale; nessun I/O."""
import re


def _leaves(data, prefix):
    for name, value in data.items():
        path = f'{prefix}.{name}'
        if isinstance(value, dict):
            yield from _leaves(value, path)
        else:
            yield path, value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Chiave JSON ripetuta')
        result[key] = value
    return result


def supported_numbers(text, cited_refs, available_refs):
    """Confronto lessicale dei numeri con i soli campi citati, non del significato.

    Non autorizza risparmi, nuove quantità o periodi: un numero esistente
    può comunque essere usato in un'affermazione scorretta. Nomi di quantità,
    unità e pertinenza restano oggetto dei controlli di dominio e della review.
    """
    from decimal import Decimal, InvalidOperation
    if any(char.isnumeric() and char not in '0123456789' for char in text):
        return False
    date = r'[0-9]{4}-[0-9]{2}(?:-[0-9]{2})?'
    numeric = r'[+\-−]?[0-9]+(?:[.,][0-9]+)?(?:[eE][+\-]?[0-9]+)?'
    def canonical(raw):
        if re.fullmatch(date, raw):
            return raw
        value = Decimal(raw.replace('−', '-').replace(',', '.'))
        if not value.is_finite():
            raise ValueError('Numero non finito')
        return value
    try:
        allowed = set()
        for ref in cited_refs:
            value = str(available_refs.get(ref, ''))
            # Un identificativo come source-v1 non autorizza un importo pari a uno.
            if re.fullmatch(date, value) or re.fullmatch(numeric, value):
                allowed.add(canonical(value))
        return {canonical(item.group()) for item in re.finditer(date + '|' + numeric, text)} <= allowed
    except (ValueError, InvalidOperation):
        return False
