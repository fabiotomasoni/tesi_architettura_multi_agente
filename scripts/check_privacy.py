"""Pilota privacy riproducibile; nessun payload sensibile nell'output."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
from gateway.pdf_input import extract_profile
from gateway.privacy import SensitiveContext, PRIVACY_VERSION, ENTITY_RECOGNIZER_VERSION, view_paths
from gateway.policy import issues, make_view
from gateway.models import Scenario

ROOT = Path(__file__).resolve().parents[1]


def annotated_pilot():
    corpus = json.loads((ROOT / 'tests/fixtures/privacy_cases.json').read_text())
    contents = [(ROOT / 'dataset/Documents' / f'C001_{kind}.pdf').read_bytes()
                for kind in ('mutuo', 'interessi', 'conto', 'paga')]
    profile, _ = extract_profile(contents)
    context = SensitiveContext.from_profile(profile)
    context.add_documents(contents)
    context.amounts.update(Decimal(a) for a in corpus['context']['extra_amounts'])
    counts = dict(true_positive=0, false_negative=0, false_positive=0, true_negative=0)
    outcomes = []
    for case in corpus['cases']:
        detected = bool(context.findings(case['payload'], allowed_paths=view_paths()))
        key = ('true_positive' if detected else 'false_negative') if case['forbidden'] else ('false_positive' if detected else 'true_negative')
        counts[key] += 1
        outcomes.append({'id': case['id'], 'expected_forbidden': case['forbidden'], 'detected': detected})
    counts['miss_rate'] = counts['false_negative'] / (counts['true_positive'] + counts['false_negative'])
    counts['false_block_rate'] = counts['false_positive'] / (counts['true_negative'] + counts['false_positive'])
    return {'corpus_version': corpus['version'], 'counts': counts, 'outcomes': outcomes,
            'limitations': corpus['limitations']}


def dataset_pilot():
    counts = dict(legitimate_views=0, legitimate_blocked=0)
    for n in range(1, 26):
        contents = [(ROOT / 'dataset/Documents' / f'C{n:03}_{kind}.pdf').read_bytes()
                    for kind in ('mutuo', 'interessi', 'conto', 'paga')]
        profile, _ = extract_profile(contents)
        context = SensitiveContext.from_profile(profile)
        context.add_documents(contents)
        for scenario in Scenario:
            if not issues(profile, scenario):
                counts['legitimate_views'] += 1
                counts['legitimate_blocked'] += bool(context.findings(make_view(profile, scenario), allowed_paths=view_paths()))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Salva soltanto conteggi e ID delle sonde.')
    args = parser.parse_args()
    result = {'scope': 'local_detector_pilot_not_final_campaign_or_network_isolation',
              'privacy_version': PRIVACY_VERSION, 'entity_recognizer_version': ENTITY_RECOGNIZER_VERSION,
              'annotated': annotated_pilot(), 'dataset': dataset_pilot()}
    counts = result['annotated']['counts']
    result['regression_passed'] = not (counts['false_positive'] or counts['false_negative'] or result['dataset']['legitimate_blocked'])
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + '\n')
    summary = {**result, 'annotated': {k:v for k,v in result['annotated'].items() if k != 'outcomes'}}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not result['regression_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
