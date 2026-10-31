"""Genera credenziali locali S03; non stampa né sovrascrive segreti esistenti."""
import json
from pathlib import Path
from secrets import token_hex
import os

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / '.local/s03'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    paths = [directory / (role + '.json') for role in ('gateway','markets','tax','bridge')]
    if any(p.exists() for p in paths):
        if all(p.exists() for p in paths):
            print('Credenziali già presenti: mantenute. Nessuna rotazione eseguita.')
            return
        raise SystemExit('Configurazione incompleta: non viene sovrascritta. Verificare i file locali prima di proseguire.')
    keys = {name: token_hex(32) for name in ('gateway_to_markets','gateway_to_tax','markets_to_gateway','tax_to_gateway','bridge')}
    for role,path in zip(('gateway','markets','tax','bridge'), paths):
        names = list(keys) if role=='gateway' else ['bridge'] if role=='bridge' else ['gateway_to_'+role,role+'_to_gateway']
        # Docker Desktop condivide i file tramite bind-mount: la directory host è privata,
        # il file montato deve essere leggibile dal UID applicativo non privilegiato.
        with path.open('x') as handle:
            json.dump({'role':role,'keys':{name:keys[name] for name in names}},handle)
            handle.write('\n')
        os.chmod(path,0o444)
    print('Create quattro identità locali separate. Valori esclusi dall’output e da Git.')


if __name__=='__main__':
    main()
