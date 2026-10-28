"""Estrazione deterministica dei soli prospetti sintetici del dataset v1."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from uuid import uuid4

from pypdf import PdfReader
from .models import Fact, Profile, Source


class PDFInputError(ValueError):
    pass


def extract_profile(documents: list[bytes]) -> tuple[Profile, list[dict]]:
    profile = Profile()
    summaries = []
    identities = set()
    seen = set()
    for content in documents:
        if not content.startswith(b'%PDF-'):
            raise PDFInputError('Un file non è un PDF valido.')
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise PDFInputError('PDF cifrato non supportato.')
            if len(reader.pages) > 20:
                raise PDFInputError('Massimo 20 pagine per documento.')
            pages = [page.extract_text() or '' for page in reader.pages]
        except PDFInputError:
            raise
        except Exception:
            raise PDFInputError('PDF corrotto o non leggibile.') from None
        text = '\n'.join(pages)
        if not text.strip():
            raise PDFInputError('PDF senza testo estraibile: OCR non supportato.')
        if 'FACSIMILE SINTETICO' not in text:
            raise PDFInputError('Formato non supportato: usare i PDF del dataset sintetico.')
        # Nessuna identità viene conservata nel profilo o restituita alla UI.
        identity = re.search(r'IBAN di test \(non operativo\)\s*\n([^\n]+)', text)
        if not identity:
            raise PDFInputError('Impossibile verificare che i PDF appartengano allo stesso fascicolo.')
        identities.add(identity.group(1).strip())
        if len(identities) > 1:
            raise PDFInputError('Caricare documenti di un solo fascicolo alla volta.')
        if 'Situazione del mutuo' in text:
            kind = 'mutuo'
        elif 'Certificazione interessi mutuo' in text:
            kind = 'interessi'
        elif 'Estratto conto dicembre' in text:
            kind = 'conto'
        elif 'Prospetto retribuzione novembre' in text:
            kind = 'paga'
        else:
            raise PDFInputError('Tipo di prospetto non riconosciuto.')
        if kind in seen:
            raise PDFInputError('Documento duplicato per la stessa tipologia.')
        seen.add(kind)
        document_id = 'doc-' + uuid4().hex
        summaries.append({'document_id': document_id, 'type': kind, 'pages': len(pages),
                          'used_for_scenarios': kind in {'mutuo', 'interessi'}})

        def field(label):
            matches = []
            for page_number, page in enumerate(pages, 1):
                for match in re.finditer(r'^\s*' + re.escape(label) + r'\s*\n([^\n]+)', page, re.M):
                    matches.append((match.group(1).strip(), page_number))
            if len(matches) > 1:
                raise PDFInputError('Etichetta ripetuta nel prospetto: estrazione ambigua.')
            return matches[0] if matches else None

        def add(name, label, unit, period, transform=lambda value: value):
            found = field(label)
            if not found:
                return
            raw, page = found
            try:
                value = transform(raw)
                status = 'validated'
            except (ValueError, InvalidOperation, KeyError):
                # Non conservare testo arbitrario come valore di un campo finanziario.
                value, status = 'ambiguous', 'ambiguous'
            setattr(profile, name, Fact(value=value, unit=unit, period=period,
                    source=Source(document_id=document_id, page=page), status=status))

        def number(value):
            cleaned = value.removesuffix(' EUR').removesuffix('%').strip()
            if not re.fullmatch(r'-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?', cleaned):
                raise ValueError()
            return Decimal(cleaned.replace('.', '').replace(',', '.'))

        if kind == 'mutuo':
            reference = field('Riferimento')
            try:
                period = datetime.strptime(reference[0], 'Situazione al %d/%m/%Y').date()
            except (ValueError, TypeError):
                raise PDFInputError('Data della situazione mutuo mancante o non valida.') from None
            # Il template documenta un mutuo immobiliare; non si deduce la residenzialità.
            profile.mortgage_type = Fact(value='other', unit='category', period=period,
                source=Source(document_id=document_id, page=reference[1]), status='validated')
            add('rate_type', 'Tipo tasso', 'category', period, lambda v: {'fisso':'fixed','variabile':'variable','misto':'mixed'}[v])
            add('remaining_principal', 'Capitale residuo', 'EUR', period, number)
            add('remaining_months', 'Durata residua', 'month', period, lambda v: number(v.removesuffix(' mesi')))
            add('annual_rate', 'Tasso annuo nominale', 'percent_per_year', period, number)
            add('payment_amount', 'Rata mensile', 'EUR', period, number)
            if field('Rata mensile'):
                profile.payment_frequency = Fact(value='monthly', unit='category', period=period,
                    source=Source(document_id=document_id, page=field('Rata mensile')[1]), status='validated')
        elif kind == 'interessi':
            year = field('Anno imposta')
            try:
                period = date(int(year[0]), 12, 31)
            except (ValueError, TypeError):
                raise PDFInputError("Anno d'imposta mancante o non valido.") from None
            add('tax_year', 'Anno imposta', 'year', period, number)
            add('purpose', 'Finalita', 'category', period, lambda v: {'acquisto abitazione principale':'primary_home_purchase', 'ristrutturazione':'other'}[v])
            add('annual_interest', 'Interessi annui documentati', 'EUR', period, number)
            add('ownership_share', 'Quota intestazione', 'fraction', period, lambda v: number(v) / 100)
    return profile, summaries
