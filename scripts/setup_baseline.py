"""Identità del generalista e del suo gateway: nessuna modifica ai segreti della demo."""
import json,os
from pathlib import Path
from secrets import token_hex
ROOT=Path(__file__).resolve().parents[1]


def main():
    directory=ROOT/'.local/baseline';directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    roles=('gateway','generalist','bridge');paths=[directory/(r+'.json') for r in roles]
    if any(p.exists() for p in paths):
        if all(p.exists() for p in paths):print('Identità baseline già presenti: mantenute.');return
        raise SystemExit('Identità baseline incomplete: nessuna sovrascrittura.')
    keys={k:token_hex(32) for k in ('gateway_to_generalist','generalist_to_gateway','bridge')}
    for role,path in zip(roles,paths):
        names=list(keys) if role=='gateway' else ['bridge'] if role=='bridge' else ['gateway_to_generalist','generalist_to_gateway']
        with path.open('x') as f:json.dump({'role':role,'keys':{k:keys[k] for k in names}},f)
        os.chmod(path,0o444)
    print('Create identità baseline separate, escluse da Git. Nessun segreto stampato.')

if __name__=='__main__':main()
