from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from gateway.app import create_app

ROOT = Path(__file__).resolve().parents[1] / 'dataset' / 'Documents'


def upload(client, case, kinds=('mutuo','interessi','conto','paga')):
    return client.post('/sessions/pdf', files=[('files',(f'{case}_{kind}.pdf',(ROOT / f'{case}_{kind}.pdf').read_bytes(),'application/pdf')) for kind in kinds], data={'scenarios':['S-01','S-02']})


@pytest.mark.parametrize('number', range(1,26))
def test_all_dataset_cases(number):
    with TestClient(create_app()) as client:
        response = upload(client, f'C{number:03}')
        assert response.status_code == 201, response.text
        result = response.json()
        assert result['scenarios']['S-01']['ready'] == (number not in range(6,11) and number not in range(16,21))
        assert result['scenarios']['S-02']['ready'] == (number not in range(11,16))
        assert 'IBAN' not in response.text and 'example.invalid' not in response.text
        if number >= 21:
            assert result['profile']['tax_year']['value'] == '2024'
        sid = result['session_id']
        assert client.delete('/sessions/'+sid).status_code == 204


def test_invalid_mixed_duplicate_and_unknown_pdf():
    with TestClient(create_app()) as client:
        assert client.get('/').status_code == 200
        assert client.post('/sessions/pdf',files=[('files',('x.pdf',b'broken','application/pdf'))],data={'scenarios':'S-01'}).status_code == 400
        mixed=[('files',('a.pdf',(ROOT/'C001_mutuo.pdf').read_bytes())),('files',('b.pdf',(ROOT/'C002_interessi.pdf').read_bytes()))]
        assert client.post('/sessions/pdf',files=mixed,data={'scenarios':'S-01'}).status_code == 400
        assert upload(client,'C001',('mutuo','mutuo')).status_code == 400
