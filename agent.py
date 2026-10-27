"""Ask a change-impact question in plain language. Claude answers through the MCP server.

    python agent.py "Vortex Seals is closing its Dutch plant. What do we need to worry about?"
"""
import asyncio
import sys

import anthropic
from anthropic.lib.tools.mcp import async_mcp_tool
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SYSTEM = """You help engineers at a pump manufacturer answer "what does this change affect?" in minutes.
Your tools sit on an enterprise ontology joining PLM, ERP, MES and CRM.

Resolve every name with find_entity first. Answer with:
1. The direct hit: parts, and for a supplier which of them are sole sourced (no second source: the real risk).
2. What it reaches: products, customers, installation count.
3. Open quality issues that make it worse.
4. Two or three concrete next actions.
Cite entity IDs. If a match came from fuzzy resolution, say so and offer source_evidence. Be brief."""


async def ask(question):
    client = anthropic.AsyncAnthropic()
    server = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as mcp_client:
        await mcp_client.initialize()
        tools = [async_mcp_tool(t, mcp_client) for t in (await mcp_client.list_tools()).tools]
        runner = client.beta.messages.tool_runner(
            model="claude-opus-5-5",
            max_tokens=16000,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # route a refusal to a fallback model instead of failing
            system=SYSTEM,
            tools=tools,
            messages=[{"role": "user", "content": question}],
        )
        final = None
        async for message in runner:
            for block in message.content:
                if block.type == "tool_use":
                    print(f"  -> {block.name}({block.input})", file=sys.stderr)
            final = message
        if final is None:
            return "No response from the model."
        if final.stop_reason == "refusal":
            return "The model declined this request."
        return "".join(b.text for b in final.content if b.type == "text")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(asyncio.run(ask(" ".join(sys.argv[1:]) or "Vortex Seals is closing its Dutch plant. What is affected?")))
