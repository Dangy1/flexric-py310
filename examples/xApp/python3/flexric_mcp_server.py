#!/usr/bin/env python3
"""
FlexRIC MCP Server
Model Context Protocol server for FlexRIC xApp integration with Langchain agents
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# FlexRIC client interface (you'll need to implement based on your FlexRIC setup)
from flexric_client import FlexRICClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flexric-mcp")

# Initialize MCP server
app = Server("flexric-mcp-server")

# Global FlexRIC client instance
flexric_client: Optional[FlexRICClient] = None


@app.list_tools()
async def list_tools() -> List[Tool]:
    """
    List all available FlexRIC tools for the Langchain agent.
    """
    return [
        Tool(
            name="get_kpi_metrics",
            description=(
                "Retrieve Key Performance Indicators (KPIs) from RAN base stations. "
                "Returns metrics like throughput, latency, PRB utilization, connected UEs, etc. "
                "Parameters: "
                "- e2_node_id (optional): Specific E2 node ID, if not provided returns all nodes "
                "- metric_types (optional): List of specific metrics to retrieve (throughput, latency, prb_util, num_ues)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "e2_node_id": {
                        "type": "string",
                        "description": "E2 Node ID (optional)"
                    },
                    "metric_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific metrics to retrieve (optional)"
                    }
                }
            }
        ),
        Tool(
            name="get_slice_metrics",
            description=(
                "Get RAN slice-specific metrics and configurations. "
                "Retrieves information about network slices including slice ID, PRB allocation, "
                "scheduler type, and per-slice KPIs. "
                "Parameters: "
                "- e2_node_id: E2 Node ID "
                "- slice_id (optional): Specific slice ID to query"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "e2_node_id": {
                        "type": "string",
                        "description": "E2 Node ID"
                    },
                    "slice_id": {
                        "type": "integer",
                        "description": "Slice ID (optional)"
                    }
                },
                "required": ["e2_node_id"]
            }
        ),
        Tool(
            name="get_ue_metrics",
            description=(
                "Retrieve UE (User Equipment) specific metrics. "
                "Returns per-UE statistics including RNTI, CQI, RSRP, throughput, buffer status. "
                "Parameters: "
                "- e2_node_id: E2 Node ID "
                "- rnti (optional): Specific UE RNTI to query"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "e2_node_id": {
                        "type": "string",
                        "description": "E2 Node ID"
                    },
                    "rnti": {
                        "type": "integer",
                        "description": "UE RNTI (optional)"
                    }
                },
                "required": ["e2_node_id"]
            }
        ),
        Tool(
            name="send_rc_control",
            description=(
                "Send RAN Control (RC) commands to modify RAN behavior. "
                "Can adjust slice parameters, UE scheduling priorities, handover decisions, etc. "
                "Parameters: "
                "- e2_node_id: E2 Node ID "
                "- control_type: Type of control (slice_config, ue_priority, handover, prb_allocation) "
                "- parameters: Dict of control-specific parameters"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "e2_node_id": {
                        "type": "string",
                        "description": "E2 Node ID"
                    },
                    "control_type": {
                        "type": "string",
                        "enum": ["slice_config", "ue_priority", "handover", "prb_allocation"],
                        "description": "Type of control command"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Control-specific parameters"
                    }
                },
                "required": ["e2_node_id", "control_type", "parameters"]
            }
        ),
        Tool(
            name="configure_slice",
            description=(
                "Configure RAN slicing parameters. "
                "Allows modification of slice PRB allocation, scheduler type, and slice priorities. "
                "Parameters: "
                "- e2_node_id: E2 Node ID "
                "- slice_id: Slice ID to configure "
                "- prb_quota: PRB quota for the slice (0-100) "
                "- scheduler: Scheduler type (round_robin, proportional_fair, max_throughput) "
                "- priority: Slice priority level (1-10)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "e2_node_id": {
                        "type": "string",
                        "description": "E2 Node ID"
                    },
                    "slice_id": {
                        "type": "integer",
                        "description": "Slice ID"
                    },
                    "prb_quota": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "PRB quota percentage"
                    },
                    "scheduler": {
                        "type": "string",
                        "enum": ["round_robin", "proportional_fair", "max_throughput"],
                        "description": "Scheduler type"
                    },
                    "priority": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Slice priority"
                    }
                },
                "required": ["e2_node_id", "slice_id"]
            }
        ),
        Tool(
            name="list_e2_nodes",
            description=(
                "List all connected E2 nodes (base stations) and their status. "
                "Returns node IDs, connection status, supported service models, and basic info."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_cell_metrics",
            description=(
                "Get cell-level metrics from a specific base station. "
                "Returns cell ID, frequency, bandwidth, transmission power, and cell-level KPIs. "
                "Parameters: "
                "- e2_node_id: E2 Node ID "
                "- cell_id (optional): Specific cell ID"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "e2_node_id": {
                        "type": "string",
                        "description": "E2 Node ID"
                    },
                    "cell_id": {
                        "type": "integer",
                        "description": "Cell ID (optional)"
                    }
                },
                "required": ["e2_node_id"]
            }
        ),
        Tool(
            name="trigger_handover",
            description=(
                "Trigger a handover for a specific UE to a target cell. "
                "Parameters: "
                "- e2_node_id: Source E2 Node ID "
                "- rnti: UE RNTI "
                "- target_cell_id: Target cell ID for handover"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "e2_node_id": {
                        "type": "string",
                        "description": "Source E2 Node ID"
                    },
                    "rnti": {
                        "type": "integer",
                        "description": "UE RNTI"
                    },
                    "target_cell_id": {
                        "type": "integer",
                        "description": "Target cell ID"
                    }
                },
                "required": ["e2_node_id", "rnti", "target_cell_id"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """
    Handle tool calls from the Langchain agent.
    """
    global flexric_client
    
    if flexric_client is None:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": "FlexRIC client not initialized",
                "status": "error"
            })
        )]
    
    try:
        result = None
        
        if name == "get_kpi_metrics":
            result = await flexric_client.get_kpi_metrics(
                e2_node_id=arguments.get("e2_node_id"),
                metric_types=arguments.get("metric_types")
            )
        
        elif name == "get_slice_metrics":
            result = await flexric_client.get_slice_metrics(
                e2_node_id=arguments["e2_node_id"],
                slice_id=arguments.get("slice_id")
            )
        
        elif name == "get_ue_metrics":
            result = await flexric_client.get_ue_metrics(
                e2_node_id=arguments["e2_node_id"],
                rnti=arguments.get("rnti")
            )
        
        elif name == "send_rc_control":
            result = await flexric_client.send_rc_control(
                e2_node_id=arguments["e2_node_id"],
                control_type=arguments["control_type"],
                parameters=arguments["parameters"]
            )
        
        elif name == "configure_slice":
            result = await flexric_client.configure_slice(
                e2_node_id=arguments["e2_node_id"],
                slice_id=arguments["slice_id"],
                prb_quota=arguments.get("prb_quota"),
                scheduler=arguments.get("scheduler"),
                priority=arguments.get("priority")
            )
        
        elif name == "list_e2_nodes":
            result = await flexric_client.list_e2_nodes()
        
        elif name == "get_cell_metrics":
            result = await flexric_client.get_cell_metrics(
                e2_node_id=arguments["e2_node_id"],
                cell_id=arguments.get("cell_id")
            )
        
        elif name == "trigger_handover":
            result = await flexric_client.trigger_handover(
                e2_node_id=arguments["e2_node_id"],
                rnti=arguments["rnti"],
                target_cell_id=arguments["target_cell_id"]
            )
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Unknown tool: {name}",
                    "status": "error"
                })
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "result": result,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            })
        )]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "status": "error",
                "tool": name
            })
        )]


async def main():
    """
    Main entry point for the MCP server.
    """
    global flexric_client
    
    # Initialize FlexRIC client
    try:
        flexric_client = FlexRICClient(
            near_ric_ip="127.0.0.1",  # Configure as needed
            near_ric_port=36421
        )
        await flexric_client.connect()
        logger.info("FlexRIC client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize FlexRIC client: {e}")
        # Continue anyway - some operations might work
    
    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
