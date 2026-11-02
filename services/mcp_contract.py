"""Il server locale non può estendere capacità o argomenti tramite metadati."""
from gateway.a2a_egress import EgressDenied
FIELDS={'lookup_rates':{'mortgage_type','rate_type','remaining_years_band','financial_profile'},
        'lookup_tax':{'tax_year','expense_category','purpose','financial_profile'},'lookup_reference':set()}
async def check_tools(client,tool,module=None):
    listed=await client.list_tools()
    legacy=module in {'services.missing_source_mcp','services.slow_rates_mcp','services.forbidden_source_mcp'}
    names={'lookup_rates','lookup_tax'} if module=='services.missing_source_mcp' else {tool}
    if listed.nextCursor is not None or {t.name for t in listed.tools}!=names or len(listed.tools)!=len(names):raise EgressDenied('Catalogo MCP difforme')
    descriptor=next(t for t in listed.tools if t.name==tool)
    schema=descriptor.inputSchema
    if descriptor.name!=tool or schema.get('type')!='object' or set(schema.get('properties',{}))!=(FIELDS[tool]-{'financial_profile'} if legacy else FIELDS[tool]):
        raise EgressDenied('Capacità MCP difforme')
