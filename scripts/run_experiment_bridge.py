"""Ponte del pilota 2x2 locale: inferenza locale, nessuna fonte Internet."""
import argparse,asyncio,os
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--organization',choices=['single','multi'],required=True)
p.add_argument('--minimization',choices=['active','disabled'],default='active')
a=p.parse_args();os.environ['TESI_EXPERIMENT']=a.organization;os.environ['TESI_MINIMIZATION']=a.minimization
from run_ollama_bridge import main
try:asyncio.run(main())
except KeyboardInterrupt:pass
