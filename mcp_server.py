# mcp_server.py

#!/usr/bin/env python3
"""ServiceNow MCP server with standard capabilities detection"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add current directory to path  
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

# Try to import vector store
try:
    from vector_store import VectorStoreManager
    VECTOR_STORE_AVAILABLE = True
except Exception as e:
    print(f"Vector store not available: {e}", file=sys.stderr)
    VECTOR_STORE_AVAILABLE = False


class FixedServiceNowServer:
    def __init__(self):
        self.vector_store = None
        
    async def search_docs(self, query: str, max_results: int = 5):
        """Search ServiceNow documentation"""
        if not VECTOR_STORE_AVAILABLE:
            return "Vector store not available"
            
        if self.vector_store is None:
            # This will now initialize with telemetry disabled
            self.vector_store = VectorStoreManager()
            
        results = self.vector_store.search_with_relevance(
            query=query,
            k=max_results,
            distance_threshold=0.5
        )
        
        if not results:
            return f"No results found for '{query}'"
            
        response_parts = [f"ServiceNow Search Results for: '{query}'\n"]
        
        for i, result in enumerate(results, 1):
            headers = result.get("headers", {})
            if isinstance(headers, str):
                try:
                    headers = json.loads(headers)
                except:
                    headers = {}
                    
            section = ""
            if headers:
                section_parts = [v for k, v in sorted(headers.items()) if v and v.strip()]
                if section_parts:
                    section = f"Section: {' > '.join(section_parts)}\n"
                    
            content = result['content']
            if len(content) > 300:
                content = content[:300] + "..."
                
            response_parts.append(f"## Result {i} (Score: {result['score']:.3f})\n{section}{content}\n")
            
        return "\n".join(response_parts)


async def main():
    # Create server
    server = Server("servicenow-vectorizer", version="1.0.0")
    servicenow = FixedServiceNowServer()
    
    @server.list_tools()
    async def list_tools():
        print("ServiceNow tools requested", file=sys.stderr)
        return [
            Tool(
                name="search_servicenow_docs",
                description="Search ServiceNow documentation for information about Now Assist, AI agents, Knowledge Graph, and other ServiceNow features",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for ServiceNow documentation"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results to return (default: 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_servicenow_status",
                description="Get status of the ServiceNow documentation system",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        print(f"ServiceNow tool called: {name}", file=sys.stderr)
        
        if name == "search_servicenow_docs":
            query = arguments.get("query")
            max_results = arguments.get("max_results", 5)
            
            if not query:
                raise ValueError("Query is required")
            
            result = await servicenow.search_docs(query, max_results)
            return [TextContent(type="text", text=result)]
            
        elif name == "get_servicenow_status":
            if VECTOR_STORE_AVAILABLE:
                if servicenow.vector_store is None:
                    servicenow.vector_store = VectorStoreManager()
                info = servicenow.vector_store.get_collection_info()
                status = f"ServiceNow Documentation System\nStatus: Active\nDocuments: {info.get('count', 0):,}\nCollection: {info.get('name', 'Unknown')}"
            else:
                status = "ServiceNow Documentation System\nStatus: Vector store not available"
            
            return [TextContent(type="text", text=status)]
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    print("Starting ServiceNow MCP server with standard capabilities...", file=sys.stderr)
    
    # Initialize vector store
    if VECTOR_STORE_AVAILABLE:
        try:
            servicenow.vector_store = VectorStoreManager()
            info = servicenow.vector_store.get_collection_info()
            print(f"Loaded {info.get('count', 0)} documents", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Vector store init failed: {e}", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())