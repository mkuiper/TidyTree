import os
import sys
import click
from pathlib import Path
from .scanner import perform_scan
from .analyzer import analyze_tree
from .models import TreeNode
from .dotenv_loader import load_dotenv


def render_ascii_tree(node: TreeNode, indent: str = "", is_last: bool = True, is_root: bool = True) -> str:
    """
    Renders a TreeNode structure into a beautiful ASCII tree.
    """
    lines = []
    
    if is_root:
        lines.append(f"{node.name}/")
        child_indent = ""
    else:
        prefix = "└── " if is_last else "├── "
        display_name = node.name
        
        # Append rename note if title was overridden
        if not node.is_dir and node.metadata and node.metadata.title_override:
            display_name = f"{display_name} [Stratus Resolved]"
            
        lines.append(f"{indent}{prefix}{display_name}{'/' if node.is_dir else ''}")
        child_indent = indent + ("    " if is_last else "│   ")
        
    if node.is_dir and node.children:
        # Sort children so directories are listed first
        sorted_children = sorted(node.children, key=lambda x: (not x.is_dir, x.name.lower()))
        for idx, child in enumerate(sorted_children):
            last_child = (idx == len(sorted_children) - 1)
            lines.append(render_ascii_tree(child, child_indent, last_child, is_root=False))
            
    return "\n".join(lines)

@click.group()
def cli():
    """TidyTree: Intelligent Directory Organization Assistant."""
    pass

@cli.command()
@click.option("--path", "-p", required=True, type=click.Path(exists=True, file_okay=False, dir_okay=True), help="Root directory to analyze.")
@click.option("--format", "-f", type=click.Choice(["text", "json", "markdown"]), default="text", help="Output format.")
@click.option("--max-depth", "-d", default=5, type=int, help="Maximum scanning depth.")
@click.option("--taxonomy", "-t", type=click.Choice(["generic", "government", "corporate", "academic"]), default="generic", help="Target organizational structure template.")
@click.option("--guidance", "-g", help="Over-arching purpose or structural guidelines for semantic sorting.")
@click.option("--provider", type=click.Choice(["none", "gemini", "openai", "anthropic"]), default="none", help="AI provider to use for semantic sorting.")
@click.option("--api-key", help="API Key for the chosen AI provider.")
@click.option("--model", help="AI model name override (e.g. gpt-4o-mini).")
def scan(path, format, max_depth, taxonomy, guidance, provider, api_key, model):
    """Safely scan and analyze a directory, suggesting optimizations."""
    target_path = Path(path).resolve()
    
    try:
        # Load environment variables from .env files
        load_dotenv(str(target_path))
        
        # Perform scan
        original_tree = perform_scan(str(target_path), max_depth=max_depth)
        
        # Load API key and provider from inputs, fallback to environment keys if none
        ai_provider = provider
        ai_api_key = api_key
        ai_model = model
        
        if not ai_api_key:
            if ai_provider == "gemini":
                ai_api_key = os.environ.get("GEMINI_API_KEY")
            elif ai_provider == "openai":
                ai_api_key = os.environ.get("OPENAI_API_KEY")
            elif ai_provider == "anthropic":
                ai_api_key = os.environ.get("ANTHROPIC_API_KEY")
            elif not ai_provider or ai_provider == "none":
                if os.environ.get("GEMINI_API_KEY"):
                    ai_provider = "gemini"
                    ai_api_key = os.environ.get("GEMINI_API_KEY")
                elif os.environ.get("OPENAI_API_KEY"):
                    ai_provider = "openai"
                    ai_api_key = os.environ.get("OPENAI_API_KEY")
                elif os.environ.get("ANTHROPIC_API_KEY"):
                    ai_provider = "anthropic"
                    ai_api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        # Perform analysis
        tidy_result = analyze_tree(
            original_tree,
            str(target_path),
            taxonomy=taxonomy,
            custom_guidance=guidance,
            ai_provider=ai_provider,
            ai_api_key=ai_api_key,
            ai_model=ai_model
        )
        
        if format == "json":
            click.echo(tidy_result.model_dump_json(indent=2))
            
        elif format == "markdown":
            click.echo("# TidyTree Directory Organization Report")
            click.echo(f"**Target Path:** `{target_path}`\n")
            click.echo("> [!IMPORTANT]")
            click.echo("> **Safety First:** This report is strictly advisory. No files have been moved or modified on disk.\n")
            
            click.echo("## Proposed Optimized Tree Structure")
            click.echo("```text")
            click.echo(render_ascii_tree(tidy_result.suggested_tree))
            click.echo("```\n")
            
            click.echo("## Relocation Rationales")
            if not tidy_result.rationales:
                click.echo("The directory structure is already optimal. No changes recommended.")
            else:
                click.echo("| Action | Original Rel Path | Suggested Rel Path | Rationale |")
                click.echo("|---|---|---|---|")
                for r in tidy_result.rationales:
                    # Clean paths for markdown display
                    orig = r.original_path if r.original_path else "/"
                    sug = r.suggested_path if r.suggested_path else "/"
                    click.echo(f"| `{r.action}` | `{orig}` | `{sug}` | {r.reasoning} |")
                    
        else: # text
            click.echo("=" * 80)
            click.echo("                     TIDYTREE ADVISORY REPORT")
            click.echo("=" * 80)
            click.echo(f"Target Directory: {target_path}")
            click.echo("-" * 80)
            click.echo("NOTE: Safety First. No directories or files were altered. This is advisory.\n")
            
            click.echo("PROPOSED DIRECTORY STRUCTURE:")
            click.echo(render_ascii_tree(tidy_result.suggested_tree))
            click.echo("\n" + "-" * 80)
            
            click.echo("ORGANIZATION RATIONALES:")
            if not tidy_result.rationales:
                click.echo("No structural changes suggested. Everything is tidy!")
            else:
                for idx, r in enumerate(tidy_result.rationales, 1):
                    orig = r.original_path if r.original_path else "/"
                    sug = r.suggested_path if r.suggested_path else "/"
                    click.echo(f"{idx}. [{r.action}]")
                    click.echo(f"   From: {orig}")
                    click.echo(f"   To:   {sug}")
                    click.echo(f"   Why:  {r.reasoning}\n")
            click.echo("=" * 80)
            
    except Exception as e:
        click.echo(f"Error during scan/analysis: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the server to.")
@click.option("--port", default=8000, type=int, help="Port to run the dashboard on.")
def dashboard(host, port):
    """Launch the Web Dashboard for visual folder comparison."""
    import uvicorn
    click.echo(f"Starting TidyTree Dashboard at http://{host}:{port}")
    uvicorn.run("tidytree.web:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    cli()
