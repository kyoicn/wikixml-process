import argparse
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from parser import process_xml

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(CURRENT_DIR, "../data/raw/sample.xml")
OUTPUT_FILE = os.path.join(CURRENT_DIR, "../data/processed/output.json")

from rich.console import Console, Group
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich import print as rprint
import llm_client

console = Console()

def main():
    parser = argparse.ArgumentParser(description="Extract Wikipedia data from XML dump.")
    parser.add_argument("input_file", nargs='?', default=INPUT_FILE, help="Path to input XML file")
    parser.add_argument("output_file", nargs='?', default=OUTPUT_FILE, help="Path to output JSON file")
    
    args = parser.parse_args()
    
    # Configuration Panel contents
    config_table = Table.grid(padding=1)
    config_table.add_column(style="cyan", justify="right")
    config_table.add_column(style="magenta")
    config_table.add_row("Input File:", args.input_file)
    config_table.add_row("Output File:", args.output_file)
    config_table.add_row("LLM Host:", llm_client.OLLAMA_HOST)
    config_table.add_row("LLM Model:", llm_client.OLLAMA_MODEL)
    
    config_panel = Panel(
        config_table,
        title="[bold]Configuration[/bold]",
        border_style="blue",
        expand=True,
        padding=(1, 2)
    )
    
    if not os.path.exists(args.input_file):
        console.print(config_panel)
        console.print(f"[bold red]Error:[/bold red] Input file '{args.input_file}' not found.")
        sys.exit(1)
        
    data = []
    count = 0
    
    # Status Panel state
    current_status = {"title": "Waiting...", "stage": "Initializing", "details": ""}

    def get_status_panel():
        status_table = Table.grid(padding=1)
        status_table.add_column(style="yellow", justify="right")
        status_table.add_column(style="white")
        
        status_table.add_row("Current Page:", current_status["title"])
        status_table.add_row("Stage:", current_status["stage"])
        if current_status["details"]:
             status_table.add_row("Details:", current_status["details"])
             
        return Panel(
            status_table, 
            title="[bold]Processing Status[/bold]", 
            border_style="green",
            expand=True,
            padding=(1, 2)
        )

    # Progress bar
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed} pages"),
        TimeElapsedColumn(),
    )
    task_id = progress.add_task("[cyan]Overall Progress[/cyan]", total=None)

    def update_status(info):
        nonlocal current_status
        # Sync title if present
        if "title" in info:
            current_status["title"] = info["title"]

        if info["stage"] == "start":
            current_status["stage"] = "Reading XML..."
            current_status["details"] = ""
            # Progress bar remains "Overall Progress"
            
        elif info["stage"] == "content":
            current_status["stage"] = "Found Wikitext"
            current_status["details"] = f"{info['len']} chars"
            
        elif info["stage"] == "llm":
            current_status["stage"] = "[bold magenta]Calling LLM...[/bold magenta]"

    try:
        # Use Live display to render the group of widgets
        # Reordered: Config -> Status -> Progress
        with Live(Group(config_panel, get_status_panel(), progress), refresh_per_second=10, console=console) as live:
            
            for entry in process_xml(args.input_file, status_callback=update_status):
                data.append(entry)
                count += 1
                progress.update(task_id, advance=1)
                
                # Update panel with the live context (Reordered)
                live.update(Group(config_panel, get_status_panel(), progress))
                
        # Final Summary
        console.print(f"\n[bold green]Finished processing![/bold green]")
        
        # Summary Table
        summary_table = Table(title="Processing Summary")
        summary_table.add_column("Metric", style="cyan", no_wrap=True)
        summary_table.add_column("Value", style="magenta")
        summary_table.add_row("Total Pages", str(count))
        summary_table.add_row("LLM Model", llm_client.OLLAMA_MODEL)
        
        console.print(summary_table)

        if data:
            console.print("\n[bold]Last processed item sample:[/bold]")
            sample_item = data[-1].copy()
            if len(sample_item.get('raw_content', '')) > 200:
                sample_item['raw_content'] = sample_item['raw_content'][:200] + "..."
            if len(sample_item.get('plain_text_content', '')) > 200:
                sample_item['plain_text_content'] = sample_item['plain_text_content'][:200] + "..."
                
            json_str = json.dumps(sample_item, indent=2, ensure_ascii=False)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            console.print(syntax)
        
        console.print(f"\nWriting to '[cyan]{args.output_file}[/cyan]'...")
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        console.print("[bold green]Done.[/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Processing interrupted by user.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error during processing:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
