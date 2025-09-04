#!/usr/bin/env python3
"""Query the ServiceNow documentation vector store"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint
import json

from vector_store import VectorStoreManager
from config import settings

console = Console()


@click.command()
@click.argument('query', required=False)
@click.option(
    '--interactive', '-i',
    is_flag=True,
    help='Interactive query mode'
)
@click.option(
    '--max-results', '-k',
    type=int,
    default=5,
    help='Maximum number of results to return'
)
@click.option(
    '--threshold', '-t',
    type=float,
    default=0.7,
    help='Minimum similarity score threshold'
)
@click.option(
    '--show-metadata', '-m',
    is_flag=True,
    help='Show full metadata for results'
)
@click.option(
    '--json-output', '-j',
    is_flag=True,
    help='Output results as JSON'
)
def query_documentation(query, interactive, max_results, threshold, show_metadata, json_output):
    """Query the ServiceNow documentation vector store"""
    
    # Initialize vector store
    try:
        vector_store = VectorStoreManager()
        info = vector_store.get_collection_info()
        
        if not json_output:
            console.print(f"[green]✓[/green] Connected to vector store")
            console.print(f"  Collection: {info['name']}")
            console.print(f"  Documents: {info['count']}")
            console.print()
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to connect to vector store: {e}")
        console.print("[yellow]Run 'python index_docs.py' first to index the documentation[/yellow]")
        return
    
    # Interactive mode
    if interactive:
        console.print("[bold cyan]ServiceNow Documentation Query Tool[/bold cyan]")
        console.print("Type 'quit' or 'exit' to stop, 'help' for commands\n")
        
        while True:
            try:
                query_input = console.input("[bold green]Query>[/bold green] ")
                
                if query_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                
                if query_input.lower() == 'help':
                    show_help()
                    continue
                
                if query_input.lower().startswith('config'):
                    show_config()
                    continue
                
                if query_input.strip():
                    perform_search(
                        vector_store, 
                        query_input, 
                        max_results, 
                        threshold, 
                        show_metadata,
                        json_output=False
                    )
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    # Single query mode
    elif query:
        perform_search(
            vector_store, 
            query, 
            max_results, 
            threshold, 
            show_metadata,
            json_output
        )
    
    else:
        console.print("[yellow]Please provide a query or use --interactive mode[/yellow]")
        console.print("Usage: python query_docs.py 'your query here'")
        console.print("   or: python query_docs.py --interactive")


def perform_search(vector_store, query, max_results, threshold, show_metadata, json_output=False):
    """Perform a search and display results"""
    
    # Search
    results = vector_store.search_with_relevance(
        query=query,
        k=max_results,
        distance_threshold=threshold
    )
    
    if json_output:
        # JSON output mode
        output = {
            "query": query,
            "results_count": len(results),
            "results": results
        }
        print(json.dumps(output, indent=2))
        return
    
    # Display results
    if not results:
        console.print(f"[yellow]No results found for: '{query}'[/yellow]")
        console.print(f"Try lowering the threshold (current: {threshold}) or using different keywords")
        return
    
    console.print(f"\n[bold cyan]Found {len(results)} results for: '{query}'[/bold cyan]\n")
    
    for i, result in enumerate(results, 1):
        # Create result panel
        headers = result.get('headers', {})
        if isinstance(headers, dict):
            headers_str = ' > '.join([v for k, v in sorted(headers.items())]) if headers else "No headers"
        else:
            headers_str = str(headers) if headers else "No headers"
        
        # Truncate content for display
        content = result['content']
        if len(content) > 500:
            content = content[:500] + "..."
        
        # Create panel content
        panel_content = f"[bold]Score:[/bold] {result['score']:.3f}\n"
        panel_content += f"[bold]Section:[/bold] {headers_str}\n\n"
        panel_content += content
        
        console.print(Panel(
            panel_content,
            title=f"[bold green]Result {i}[/bold green]",
            border_style="green"
        ))
        
        if show_metadata:
            # Show metadata in a table
            table = Table(title="Metadata", show_header=True)
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="white")
            
            for key, value in result['metadata'].items():
                if key != 'headers':  # Skip headers as we show them above
                    table.add_row(key, str(value))
            
            console.print(table)
        
        console.print()


def show_help():
    """Show help information"""
    help_text = """
[bold cyan]Available Commands:[/bold cyan]
  
  [green]<query>[/green]     - Search for documentation
  [green]help[/green]       - Show this help message
  [green]config[/green]     - Show current configuration
  [green]quit/exit[/green]  - Exit the program
  
[bold cyan]Search Tips:[/bold cyan]
  - Use specific technical terms for better results
  - Include context like "configuration", "setup", "api", etc.
  - Results are ranked by relevance score
  
[bold cyan]Examples:[/bold cyan]
  - "Now Assist configuration"
  - "AI agents setup"
  - "Knowledge Graph API"
    """
    console.print(Panel(help_text, title="Help", border_style="blue"))


def show_config():
    """Show current configuration"""
    config_table = Table(title="Current Configuration", show_header=True)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_table.add_row("Embedding Model Type", settings.embedding_model_type)
    config_table.add_row("Embedding Model", settings.embedding_model_name)
    config_table.add_row("Collection Name", settings.collection_name)
    config_table.add_row("Chunk Size", str(settings.chunk_size))
    config_table.add_row("Chunk Overlap", str(settings.chunk_overlap))
    config_table.add_row("Max Results", str(settings.max_results))
    config_table.add_row("Similarity Threshold", str(settings.similarity_threshold))
    
    console.print(config_table)


if __name__ == "__main__":
    query_documentation()
