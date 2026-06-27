"""Pre-warm and verify the package-runner MCP servers the agents launch on demand.

Run once after install (`make setup`) so the first real query isn't a slow cold
download, and to confirm `uv`/`node` + network can actually reach the servers.
A failure here is the usual cause of a cryptic "Tool 'search_flights' not found"
at runtime (ADK silently drops a toolset whose server won't start).
"""
import asyncio
import sys
import warnings

warnings.filterwarnings("ignore")
from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

SERVERS = [
    ("weather  (npx @dangahagan/weather-mcp)", "npx", ["-y", "@dangahagan/weather-mcp@1.8.0"]),
    ("flights  (uvx fli)", "uvx", ["--from", "flights[mcp]", "fli-mcp"]),
]


async def check(name: str, command: str, args: list[str]) -> bool:
    try:
        async with stdio_client(StdioServerParameters(command=command, args=args)) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = (await s.list_tools()).tools
        print(f"  OK    {name}: {len(tools)} tools")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL  {name}: {type(e).__name__} — is the runner installed and network up?")
        return False


async def main() -> None:
    print("Pre-warming MCP servers (first run downloads packages — be patient)...")
    results = [await check(*s) for s in SERVERS]
    if not all(results):
        print("\nSome servers failed; agents will be missing those tools until fixed.")
        sys.exit(1)
    print("All MCP servers ready.")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=300))
