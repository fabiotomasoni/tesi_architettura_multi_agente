"""La scheda facilita la lettura, senza creare una falsa revisione umana."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.prepare_annotation_review import FIRST_CASES, render, source_fragments

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'evaluation/annotations.json'


def test_review_shows_source_ambiguity_absence_and_separate_periods_without_identities(tmp_path):
    before = REFERENCE.read_bytes()
    result = render(REFERENCE, FIRST_CASES, ROOT / 'dataset/Documents', ROOT / 'runs/review.html')
    assert '3,10% oppure 4,25%' in result
    assert 'Nessun valore utilizzabile' in result
    assert 'Etichetta «Capitale residuo» non trovata' in result
    assert 'Etichetta «Interessi annui documentati» non trovata' in result
    assert '2024-12-31' in result and '2025-12-31' in result
    assert 'non costituiscono da sole un conflitto' in result
    assert '1604.32' in result and '3.20% annuo' in result
    assert 'Non è una detrazione' in result
    assert 'non usata dalla fixture' in result
    assert result.count('Controllo umano del riferimento.') == 5
    for absent in ['example.invalid', 'TSTFNT', 'IT00X', '/Users/', 'Anagrafica', '<script', '<iframe']:
        assert absent not in result
    assert REFERENCE.read_bytes() == before


def test_changed_pdf_digest_prevents_publishing_stale_reference(tmp_path):
    reference = json.loads(REFERENCE.read_text())
    reference['cases'][0]['pdf_sha256']['C001_mutuo.pdf'] = '0' * 64
    path = tmp_path / 'changed.json'
    path.write_text(json.dumps(reference))
    with pytest.raises(ValueError, match='PDF cambiato'):
        render(path, ['C001'], ROOT / 'dataset/Documents', tmp_path / 'review.html')


@pytest.mark.parametrize('ids', [[], ['C001', 'C001'], ['C999'], ['../../x']])
def test_invalid_selection_is_refused(ids, tmp_path):
    with pytest.raises(ValueError):
        render(REFERENCE, ids, ROOT / 'dataset/Documents', tmp_path / 'review.html')


def test_text_fragments_preserve_ambiguous_source_and_do_not_guess_monthly_value():
    assert 'non trovata' in source_fragments(['Nessuna rata indicata'], 'payment_frequency')
    result = source_fragments(['Tasso annuo nominale\n3% oppure 4%'], 'annual_rate')
    assert '3% oppure 4%' in result and 'Pagina 1' in result


def test_all_cases_can_be_read_and_html_is_escaped(tmp_path):
    data = deepcopy(json.loads(REFERENCE.read_text()))
    data['cases'][0]['facts']['rate_type']['value'] = '<script>bad()</script>'
    # Lo strumento non certifica l'annotazione: mostra anche modifiche da rivedere.
    data['cases'][0]['expected_calculations'].pop('alternative_fixture')
    path = tmp_path / 'escaped.json'
    path.write_text(json.dumps(data))
    result = render(path, [f'C{i:03}' for i in range(1, 26)], ROOT / 'dataset/Documents', tmp_path / 'review.html')
    assert '&lt;script&gt;bad()&lt;/script&gt;' in result
    assert '<script' not in result
    assert result.count('Controllo umano del riferimento.') == 25


def test_cli_creates_offline_sheet_without_changing_or_approving_reference(tmp_path):
    output = tmp_path / 'review.html'
    paths = [REFERENCE, ROOT / 'evaluation/protocol.json', ROOT / 'evaluation/human_review_template.csv']
    before = [p.read_bytes() for p in paths]
    command = [sys.executable, 'scripts/prepare_annotation_review.py', '--output', str(output)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert output.exists() and 'Nessuna annotazione approvata automaticamente' in result.stdout
    generated = output.read_bytes()
    repeated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert repeated.returncode != 0 and 'File già presente' in repeated.stderr
    assert output.read_bytes() == generated
    assert [p.read_bytes() for p in paths] == before
