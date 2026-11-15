# Throwaway spike code (task 1.7). Minimal stdio MCP server (newline-delimited JSON-RPC), no deps.
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stub_ops
TOOLS = [
 {"name": "create_task", "description": "Create a Pixie task that runs once, now or soon. Returns the task id.",
  "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "instructions": {"type": "string"}}, "required": ["title"]}},
 {"name": "propose_schedule", "description": "Propose a recurring schedule for a task (not active until approved). Returns the schedule id.",
  "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "cadence": {"type": "string", "description": "e.g. daily 08:00"}, "instructions": {"type": "string"}}, "required": ["title", "cadence"]}}]
def send(o): sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    m = json.loads(line); mid = m.get("id"); meth = m.get("method")
    if mid is None: continue
    if meth == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": m["params"].get("protocolVersion", "2025-06-18"),
              "capabilities": {"tools": {}}, "serverInfo": {"name": "pixie-stub", "version": "0"}}})
    elif meth == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
    elif meth == "tools/call":
        n = m["params"]["name"]; a = m["params"].get("arguments") or {}
        try:
            if n == "create_task": r = stub_ops.create_task(a["title"], a.get("instructions", ""))
            elif n == "propose_schedule": r = stub_ops.propose_schedule(a["title"], a["cadence"], a.get("instructions", ""))
            else: raise KeyError(n)
            send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": json.dumps({"id": r})}], "isError": False}})
        except Exception as e:
            send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": "error: %s" % e}], "isError": True}})
    else:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})
