"""Coerenza del report con la citazione BCE salvata; non esegue nuove richieste Internet."""
import argparse
import csv
from datetime import datetime
from decimal import Decimal
import hashlib
from io import StringIO
import json
from pathlib import Path
from urllib.parse import urlsplit,parse_qs


def verify(report):
    sources=[s for s in report.get('external_sources',[]) if s.get('scenario')=='S-01']
    checks={'institutional_source_present':len(sources)==1}
    if len(sources)!=1:return checks
    source=sources[0];data=source.get('evidence',{})
    try:
        raw=data['source_csv'];rows=list(csv.DictReader(StringIO(raw)))
        row=rows[0] if len(rows)==1 else {}
        url=urlsplit(data['source_url'])
        checks.update(
            real_not_simulated=data['simulated'] is False,
            official_fixed_endpoint=url.scheme=='https' and url.netloc=='data-api.ecb.europa.eu' and url.path=='/service/data/MIR/M.IT.B.A2C.A.R.A.2250.EUR.N' and parse_qs(url.query)=={'lastNObservations':['1'],'format':['csvdata']},
            series_and_unit=row.get('KEY')=='MIR.M.IT.B.A2C.A.R.A.2250.EUR.N' and data['series_key']==row.get('KEY') and row.get('UNIT')=='PCPA' and row.get('UNIT_MULT')=='0' and row.get('DATA_TYPE_MIR')=='R',
            value_matches_quote=Decimal(data['annual_rate_percent'])==Decimal(row['OBS_VALUE']),
            period_matches_quote=data['observation_period']==row['TIME_PERIOD'],
            response_digest_matches=hashlib.sha256(raw.encode('utf8')).hexdigest()==data['response_sha256'],
            retrieval_time_explicit=datetime.fromisoformat(data['retrieved_at'].replace('Z','+00:00')).tzinfo is not None,
            gateway_receipt_checked=source.get('verification')=='gateway_retrieval_and_series_checked' and source.get('institutional_retrieval_verified') is True,
            not_used_as_nominal_offer=report['mortgage_comparison']['status']=='not_calculated' and report['mortgage_comparison']['reason']=='incompatible_market_measure',
            no_recommendation=report['mortgage_comparison']['personalized_recommendation'] is False,
            no_simulated_market_fallback=not any(s.get('scenario')=='S-01' for s in report.get('simulated_sources',[])),
        )
        facts=next(d['facts'] for d in report['document_data'] if d['scenario']=='S-01')
        checks['document_payment_preserved']=Decimal(report['mortgage_comparison']['documented_monthly_payment'])==Decimal(facts['payment_amount']['value'])
    except (KeyError,ValueError,TypeError,StopIteration):checks['complete_verifiable_contract']=False
    return checks


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('report',type=Path);args=parser.parse_args()
    checks=verify(json.loads(args.report.read_text()))
    for name,value in checks.items():print(name+': '+str(value))
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__=='__main__':main()
