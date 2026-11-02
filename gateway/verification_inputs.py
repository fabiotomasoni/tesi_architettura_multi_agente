"""Tre artefatti sintetici fissati per raggiungere il parser nel laboratorio."""
import hashlib,json
from pathlib import Path
from .verification_config import SHARED

def admitted_negative(content):
    if not SHARED:return False
    manifest=json.loads((Path(__file__).parent/'fixtures/verification_inputs.json').read_text())
    return hashlib.sha256(content).hexdigest() in {v['sha256'] for v in manifest.values()}
