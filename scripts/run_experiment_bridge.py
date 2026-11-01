"""Ponte del solo pilota S+P/M+P: inferenza locale, nessuna fonte Internet."""
import argparse,asyncio,os
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--organization',choices=['single','multi'],required=True)
a=p.parse_args();os.environ['TESI_EXPERIMENT']=a.organization
from run_ollama_bridge import main
try:asyncio.run(main())
except KeyboardInterrupt:pass
