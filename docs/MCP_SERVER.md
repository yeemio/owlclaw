# MCP Server (MVP)

## Overview

`owlclaw.mcp` provides a minimal MCP protocol server that maps OwlClaw Skills/Handlers to MCP `resources` and `tools`.

Current MVP scope:
- `initialize`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`
- stdio line processing (`process_stdio_line`)

Out of current MVP scope:
- HTTP/SSE transport
- Prompt/Sampling support
- standalone `owlclaw-mcp` package layout

## Quick Start

```python
from owlclaw import OwlClaw
from owlclaw.mcp import McpProtocolServer

app = OwlClaw("demo")
app.mount_skills("./capabilities")

@app.handler("echo-tool")
async def echo_tool(message: str) -> dict[str, str]:
    return {"echo": message}

server = McpProtocolServer.from_app(app)
```

Handle one JSON-RPC message:

```python
response = await server.handle_message(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "echo-tool", "arguments": {"message": "hello"}},
    }
)
```

Handle one stdio line:

```python
line = await server.process_stdio_line(
    '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
)
```

## Resource Mapping

Skill files are exposed as resources with URI format:

`skill://<category>/<name>`

Where:
- `category` is the parent folder under capabilities
- `name` is the skill folder name

## Error Codes

Implemented JSON-RPC/MCP error codes:
- `-32700`: parse error
- `-32600`: invalid request
- `-32601`: method not found
- `-32602`: invalid params
- `-32001`: tool not found
- `-32002`: resource not found
- `-32005`: internal execution error

