"""Confronta gli ultimi record di timeout e recupero senza stampare dati personali."""
import json
from pathlib import Path


def last(name):
    return json.loads(Path('runs', name).read_text().splitlines()[-1])


first = last('same_process_timeout.jsonl')
second = last('same_process_recovery.jsonl')
a = first.get('measurements', {}).get('agent_boot_id')
b = second.get('measurements', {}).get('agent_boot_id')
checks = {
    'timeout_atteso': first.get('passed') is True and first.get('error_code') == 'timeout',
    'recupero_completato': second.get('passed') is True and second.get('status') == 'completed',
    'stesso_avvio_agente': bool(a) and a == b,
    'sessioni_gateway_cancellate': first.get('cleanup_verified') is True and second.get('cleanup_verified') is True,
}
for name, passed in checks.items():
    print(name + ': ' + str(passed))
raise SystemExit(0 if all(checks.values()) else 1)
