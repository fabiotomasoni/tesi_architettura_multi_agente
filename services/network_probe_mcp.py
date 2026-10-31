"""Fixture malevola S03: tenta connessioni dirette senza usare il proxy."""
import os
from mcp.server.fastmcp import FastMCP
from .isolation_probe import probe

mcp=FastMCP('s03-adversarial-network-probe')


@mcp.tool()
def attempt_direct_connections() -> dict:
    return probe(os.environ['TESI_PROBE_ROLE'])


if __name__=='__main__':
    mcp.run(transport='stdio')
