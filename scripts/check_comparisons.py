"""Fixture RF-07 locali: controlli semantici, conversioni, conflitti e provenienza."""
import json
from pathlib import Path
import sys
# Consente l'esecuzione dalla repository anche senza reinstallare il pacchetto.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gateway.comparisons import Observation,compare


def main():
    base=dict(observation_id='doc',quantity='contract_annual_rate',product='mortgage-demo',period='2025-12-31',value='3.10',unit='percent_per_year',source_kind='document',source_ref='synthetic-document#page/1',verified=True)
    cases=[
        ('agent_document_conflict',{'value':'4.25','source_kind':'agent'},'conflict'),
        ('equivalent_basis_points',{'value':'310','unit':'basis_points_per_year'},'consistent'),
        ('different_period',{'value':'4.25','period':'2024-12-31'},'not_comparable'),
        ('different_product',{'value':'4.25','product':'other'},'not_comparable'),
        ('contract_vs_market',{'value':'3.20','quantity':'market_annual_rate'},'not_comparable'),
        ('different_quantity',{'value':'800','quantity':'payment_amount','unit':'EUR'},'not_comparable'),
    ]
    rows=[]
    for name,changes,expected in cases:
        right={**base,**changes,'observation_id':'other','source_ref':'synthetic-other'}
        result=compare(Observation(**base),Observation(**right))
        passed=result['status']==expected and result['left']==base and result['right']==right
        print(name,result['status'],'passed:',passed)
        rows.append({'case':name,'passed':passed,'result':result})
    out=Path('runs/comparisons.json');out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows,indent=2)+'\n')
    raise SystemExit(0 if all(r['passed'] for r in rows) else 1)


if __name__=='__main__':main()
