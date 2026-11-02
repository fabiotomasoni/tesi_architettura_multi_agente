"""Selettori chiusi del laboratorio autorizzato, mai provenienti dalle richieste."""
import os

PROFILES=frozenset({'nominal','source_timeout','source_malformed','both_unavailable',
    'missing_market','both_missing','hostile_result','metadata','conflict_agents',
    'conflict_document','equivalent_units','different_period','different_product','unfaithful_result','utility_loss','payload_identifier','payload_financial','card_identity','card_endpoint','card_capabilities'})
PROFILE=os.environ.get('TESI_VERIFICATION_PROFILE','nominal')
SHARED=os.environ.get('TESI_SHARED_REFERENCE','0')
if SHARED not in {'0','1'} or PROFILE not in PROFILES:
    raise RuntimeError('Configurazione di verifica non riconosciuta')
SHARED=SHARED=='1'
if PROFILE!='nominal' and (not SHARED or os.environ.get('TESI_EXPERIMENT','off')=='off'
        or any(os.environ.get(k,'simulated')!='simulated' for k in ('TESI_MARKET_SOURCE','TESI_TAX_SOURCE'))):
    raise RuntimeError('Le fixture di verifica richiedono il laboratorio con fonti simulate e riferimento comune')
