# mcp_flexric_server.py
import os
import requests
from typing import Any, Dict, Optional

XAPP_URL = os.environ.get("XAPP_URL", "http://127.0.0.1:8088")
TIMEOUT_S = float(os.environ.get("XAPP_TIMEOUT_S", "1.5"))

def _get(path: str, params: Optional[dict] = None) -> Dict[str, Any]:
    r = requests.get(f"{XAPP_URL}{path}", params=params, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json()

def _post(path: str, payload: dict) -> Dict[str, Any]:
    r = requests.post(f"{XAPP_URL}{path}", json=payload, timeout=TIMEOUT_S)
    r.raise_for_status()
    return r.json()

# ---- MCP glue (example with FastMCP) ----
# If your MCP SDK differs, keep the tool functions and adjust registration.
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("flexric-oran-tools")

@mcp.tool()
def ric_health() -> Dict[str, Any]:
    """Check xApp RPC health (FlexRIC init path)."""
    return _get("/health")

@mcp.tool()
def ric_list_e2_nodes() -> Dict[str, Any]:
    """List connected E2 nodes as seen by FlexRIC."""
    return _get("/e2/nodes")

@mcp.tool()
def slice_subscribe(e2_node_id: str, interval_ms: int = 10) -> Dict[str, Any]:
    """Subscribe to SLICE SM indications for a node."""
    return _post("/slice/subscribe", {"e2_node_id": e2_node_id, "interval_ms": interval_ms})

@mcp.tool()
def slice_poll(sub_id: str, max_items: int = 200) -> Dict[str, Any]:
    """Poll cached SLICE SM indications."""
    return _post("/slice/poll", {"sub_id": sub_id, "max_items": max_items})

@mcp.tool()
def slice_unsubscribe(sub_id: str) -> Dict[str, Any]:
    """Remove SLICE SM subscription."""
    return _post("/slice/unsubscribe", {"sub_id": sub_id})

@mcp.tool()
def slice_set_static(
    e2_node_id: str,
    dl_slice_id: int, dl_pos_low: int, dl_pos_high: int,
    ul_slice_id: int, ul_pos_low: int, ul_pos_high: int,
) -> Dict[str, Any]:
    """Apply a simple static slice config (demo control)."""
    payload = {
        "e2_node_id": e2_node_id,
        "dl_slice_id": dl_slice_id, "dl_pos_low": dl_pos_low, "dl_pos_high": dl_pos_high,
        "ul_slice_id": ul_slice_id, "ul_pos_low": ul_pos_low, "ul_pos_high": ul_pos_high,
    }
    return _post("/slice/control/static", payload)

if __name__ == "__main__":
    # Usually MCP runs over stdio
    mcp.run()
