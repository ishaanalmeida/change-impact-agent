"""MCP server exposing the change-impact tools. Any MCP client (Claude Code, Claude Desktop,
Cursor, or agent.py here) can reason over the enterprise ontology through it.

    python mcp_server.py            # stdio
"""
from mcp.server.mcpserver import MCPServer

from impact import ImpactGraph

graph = ImpactGraph()
mcp = MCPServer(
    "change-impact",
    instructions=(
        "Tools over an enterprise ontology that joins PLM (bill of materials), ERP (suppliers), "
        "MES (quality issues) and CRM (installed base) for a pump manufacturer. Resolve names to IDs "
        "with find_entity before calling other tools. Use source_evidence to show which source records "
        "an answer rests on."
    ),
)


@mcp.tool()
def find_entity(query: str, entity_type: str | None = None) -> list[dict]:
    """Find entities by name, ID or any spelling a source system used.

    Args:
        query: free text, e.g. "vortex seals", "FluxaPro 200", "O-ring 45mm".
        entity_type: optional filter: Product, Assembly, Part, Supplier, Customer, Installation, QualityIssue.
    """
    return graph.find_entity(query, entity_type)


@mcp.tool()
def describe(entity_id: str) -> dict:
    """Type, label and direct links of one entity (components, suppliers, where it is used)."""
    return graph.describe(entity_id)


@mcp.tool()
def change_impact(entity_id: str) -> dict:
    """What a change to a supplier, part or assembly reaches: parts (and which are sole sourced),
    assemblies, products, customers, installation count and open quality issues."""
    return graph.change_impact(entity_id)


@mcp.tool()
def source_evidence(entity_id: str) -> list[str]:
    """The ERP, MES and CRM records that were resolved onto this entity, with the match method and score."""
    return graph.source_evidence(entity_id)


@mcp.tool()
def sparql(query: str) -> dict:
    """Read-only SPARQL SELECT or ASK over the graph, for questions the other tools do not cover.
    Prefixes fx: <https://example.org/fluxa/> and rdfs: are predefined. Classes: fx:Product, fx:Assembly,
    fx:Part, fx:Supplier, fx:Customer, fx:Installation, fx:QualityIssue. Properties: fx:hasComponent,
    fx:suppliedBy, fx:ofProduct, fx:ownedBy, fx:concerns, fx:status, fx:defect, rdfs:label."""
    return graph.sparql(query)


if __name__ == "__main__":
    mcp.run()
