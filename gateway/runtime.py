"""Topologia fidata: nessun endpoint viene scelto da Card, tool o modello."""
import os

MODE = os.environ.get('TESI_RUNTIME', 'local')
if MODE not in {'local', 'isolated'}:
    raise RuntimeError('Modalità di esecuzione non riconosciuta')
ISOLATED = MODE == 'isolated'
EXPERIMENT = os.environ.get('TESI_EXPERIMENT', 'off')
if EXPERIMENT not in {'off','single','multi'}:
    raise RuntimeError('Profilo sperimentale non riconosciuto')
SINGLE = EXPERIMENT == 'single'
MINIMIZATION=os.environ.get('TESI_MINIMIZATION','active')
if MINIMIZATION not in {'active','disabled'} or MINIMIZATION=='disabled' and EXPERIMENT=='off':
    raise RuntimeError('Minimizzazione disattivabile solo nei profili sperimentali locali')
UNMINIMIZED=MINIMIZATION=='disabled'
AGENT_ENDPOINTS = ({'S-01': 'http://172.30.241.3:8001/', 'S-02': 'http://172.30.242.3:8002/'}
                   if ISOLATED else {'S-01': 'http://127.0.0.1:8001/', 'S-02': 'http://127.0.0.1:8002/'})
GATEWAY_ENDPOINTS = ({'S-01': 'http://172.30.241.2:8000', 'S-02': 'http://172.30.242.2:8000'}
                     if ISOLATED else {'S-01': 'http://127.0.0.1:8000', 'S-02': 'http://127.0.0.1:8000'})
PEER_SCENARIOS = {'172.30.241.3': 'S-01', '172.30.242.3': 'S-02'}
IDENTITY_VERSION = 'service-identity-0.1.0'

if SINGLE:
    AGENT_ENDPOINTS={**AGENT_ENDPOINTS,'S-02':AGENT_ENDPOINTS['S-01'],'BATCH':AGENT_ENDPOINTS['S-01']}
    GATEWAY_ENDPOINTS={**GATEWAY_ENDPOINTS,'S-02':GATEWAY_ENDPOINTS['S-01']}
    PEER_SCENARIOS={'172.30.241.3':'S-01'}
