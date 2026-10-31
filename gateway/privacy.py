"""Filtro locale deterministico: nessuna promessa di anonimizzazione generale."""
from dataclasses import dataclass,field
from datetime import datetime
from decimal import Decimal,InvalidOperation
from io import BytesIO
import re
from html import unescape
import unicodedata
from urllib.parse import unquote
from pypdf import PdfReader
from .a2a_egress import EgressDenied

PRIVACY_VERSION='0.2.0'
ENTITY_RECOGNIZER_VERSION='it-context-rules-0.1.0'


def normalize(text):
    text=str(text)
    for _ in range(3):
        decoded=unescape(unquote(text))
        if decoded==text:break
        text=decoded
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKC',text).casefold()
                           if unicodedata.category(c)!='Cf').split())


def numbers(text):
    result=set()
    text=re.sub(r"(?<=\d)['’](?=\d)",'',text)
    for token in re.findall(r'(?<!\w)\d+(?:[.,\s]\d+)*(?:[eE][+-]?\d+)?(?!\w)',text):
        token=token.replace(' ','')
        variants={token}
        if 'e' in token.lower():
            try:result.add(Decimal(token.replace(',','.')))
            except InvalidOperation:pass
            continue
        if ',' in token and '.' in token:
            last=max(token.rfind(','),token.rfind('.'))
            variants={re.sub(r'[.,]','',token[:last])+'.'+token[last+1:]}
        elif ',' in token:variants={token.replace(',','.'),token.replace(',','')}
        elif '.' in token:variants={token,token.replace('.','')}
        for value in variants:
            try:result.add(Decimal(value))
            except InvalidOperation:pass
    return result


# Riconoscimento locale euristico, senza servizi remoti o modelli scaricati.
# Individua persone contestuali, indirizzi e organizzazioni; non è NER generale.
_WORD = r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:[’'-][A-ZÀ-ÖØ-Þ]?[a-zà-öø-ÿ]+)*"
_PERSON = _WORD + r"(?:[ \t]+(?:di |de |del |della )?" + _WORD + r"){1,3}"
_PERSON_PATTERNS = (
    r"(?:mi chiamo|nome e cognome|intestatario|beneficiario|dipendente|cliente|sig\.?|sig.ra|signor[ae]?)\s*[:=]?\s*(" + _PERSON + r")",
    r"\b(" + _PERSON + r")\b",
)


def recognize_entities(text):
    """Restituisce categoria e span testuale; non registra contenuti nei log."""
    results=[]
    for pattern in _PERSON_PATTERNS:
        for match in re.finditer(pattern,text):
            results.append(('person',match.group(1)))
    for match in re.finditer(r'\bmi chiamo[ \t]+([a-zà-öø-ÿ]+[ \t]+[a-zà-öø-ÿ]+)',text):
        results.append(('person',match.group(1)))
    for pattern,kind in (
        (r"\b(?:[Vv]ia|[Vv]iale|[Pp]iazza|[Cc]orso|[Vv]icolo)\s+[^\n,;]{2,60}?\s+\d+[A-Za-z]?\b",'address'),
        (r"\b"+_WORD+r"(?:\s+"+_WORD+r"){0,3}\s+(?:S\.?r\.?l\.?|S\.?p\.?A\.?|SRL|SPA)\b",'organization'),
    ):
        for match in re.finditer(pattern,text):results.append((kind,match.group()))
    return results


# Eccezioni solo per numeri in campi autorizzati da contratti/template fidati.
# Non applicare a testo libero, chiavi, URL o intestazioni.
VIEW_NUMERIC_PATHS=frozenset({('tax_year',),
    ('remaining_years_band','lower_exclusive'),('remaining_years_band','upper_inclusive')})


def view_paths(prefix=()):
    return frozenset(prefix+path for path in VIEW_NUMERIC_PATHS)


@dataclass(repr=False)
class SensitiveContext:
    entities: set[str]=field(default_factory=set)
    amounts: set[Decimal]=field(default_factory=set)
    dates: set[str]=field(default_factory=set)

    @classmethod
    def from_profile(cls,profile):
        context=cls()
        for fact in profile.model_dump().values():
            if not fact:continue
            if fact['unit']=='EUR':
                try:
                    amount=Decimal(str(fact['value']))
                    if amount.is_finite():context.amounts.add(amount)
                except InvalidOperation:pass
            context.dates.add(str(fact['period']))
        return context

    def add_documents(self,contents):
        labels=('Intestatario','Codice fiscale di test (non validato)','IBAN di test (non operativo)',
                'Residenza','Contatto','Datore','Contratto')
        for content in contents:
            text='\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(content)).pages)
            for label in labels:
                for match in re.finditer(r'^\s*'+re.escape(label)+r'\s*\n([^\n]+)',text,re.M):
                    value=match.group(1)
                    self.entities.add(normalize(value))
                    if label=='Intestatario':
                        self.entities.update(normalize(word) for word in value.split() if len(word)>2)
            for kind,entity in recognize_entities(text):
                self.entities.add(normalize(entity))
                if kind=='person':
                    self.entities.update(normalize(word) for word in entity.split() if len(word)>2)
            for match in re.finditer(r'\b(\d{1,2}/\d{1,2}/\d{4})\b',text):
                try:self.dates.add(datetime.strptime(match.group(1),'%d/%m/%Y').date().isoformat())
                except ValueError:pass
            for match in re.finditer(r'([\d.,]+)\s*EUR\b',text):
                # Il template supportato usa importi italiani, senza ambiguità di locale.
                try:self.amounts.add(Decimal(match.group(1).replace('.','').replace(',','.')))
                except InvalidOperation:pass

    def findings(self,value,*,allowed_paths=frozenset(),public_paths=frozenset(),_path=()):
        found=set()
        if isinstance(value,dict):
            for key,item in value.items():
                found.update(self.findings(str(key)))
                found.update(self.findings(item,allowed_paths=allowed_paths,public_paths=public_paths,_path=_path+(key,)))
            return found
        if isinstance(value,(list,tuple)):
            for i,item in enumerate(value):
                found.update(self.findings(item,allowed_paths=allowed_paths,public_paths=public_paths,_path=_path+(i,)))
            return found
        if value is None or isinstance(value,bool):return found
        # Analisi prima del casefold per preservare gli indizi delle maiuscole.
        local_text=unescape(unquote(unicodedata.normalize('NFKC',str(value))))
        if recognize_entities(local_text):found.add('local_entity_candidate')
        text=normalize(value)
        compact=re.sub(r'[\s-]','',text)
        if re.search(r'(?<![a-z0-9])[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}(?!\w)',text):found.add('email')
        if re.search(r'(?<!\w)\+\d(?:[ .()-]*\d){7,14}(?!\d)',text) or re.search(r'\b(?:telefono|cellulare|tel\.?)\s*[:=]?\s*\d(?:[ .()-]*\d){7,14}(?!\d)',text):found.add('phone_candidate')
        if re.search(r'(?<![a-z0-9])[a-z]{2}\d{2}[a-z0-9]{11,30}(?![a-z0-9])',compact):found.add('iban_candidate')
        if re.search(r'(?<![a-z0-9])[a-z]{6}\d{2}[a-z]\d{2}[a-z]\d{3}[a-z0-9](?![a-z0-9])',compact):found.add('fiscal_code_candidate')
        for entity in self.entities:
            if entity and (re.search(r'(?<!\w)'+re.escape(entity)+r'(?!\w)',text) or re.sub(r'[\s-]','',entity) in compact):
                found.add('known_entity')
        exempt_number=(_path in allowed_paths and type(value) is int) or _path in public_paths
        if not exempt_number and self.amounts & numbers(text):found.add('known_amount')
        for match in re.finditer(r'\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}[/.]\d{4})(?!\d)',text):
            raw=match.group()
            try:
                date=datetime.strptime(raw,'%Y-%m-%d' if '-' in raw else '%d/%m/%Y' if '/' in raw else '%d.%m.%Y').date().isoformat()
                if _path not in public_paths and date in self.dates:found.add('known_date')
            except ValueError:pass
        for date in self.dates:
            for compact_date in (date.replace('-',''),date[8:10]+date[5:7]+date[:4]):
                if _path not in public_paths and re.search(r'(?<!\d)'+re.escape(compact_date)+r'(?!\d)',text):found.add('known_date')
        return found


def check(context,value,*,allowed_paths=frozenset(),public_paths=frozenset()):
    categories=context.findings(value,allowed_paths=allowed_paths,public_paths=public_paths)
    if categories:raise EgressDenied('Payload con dati vietati: '+','.join(sorted(categories)))
