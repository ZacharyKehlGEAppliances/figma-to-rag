import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.traceback import install
from .converter import FigmaRAGConverter
from .exceptions import FigmaAPIError, ConversionError

# Install rich traceback handler
install(show_locals=True)

app = typer.Typer(help="Convert Figma designs to RAG-optimized format")
console = Console()

def validate_token(ctx: typer.Context, token: Optional[str]) -> Optional[str]:
    """Validate the access token from CLI or environment."""
    if token:
        return token
    env_token = os.getenv("FIGMA_ACCESS_TOKEN")
    if env_token:
        return env_token
    console.print(Panel(
        "No access token provided. Please provide it via --access-token or set FIGMA_ACCESS_TOKEN environment variable.",
        title="Error",
        style="red"
    ))
    ctx.exit(1)
    return None

@app.command()
def inspect(
    ctx: typer.Context,
    file_key: str = typer.Argument(..., help="Figma file identifier"),
    access_token: Optional[str] = typer.Option(
        None,
        "--access-token",
        "-t",
        callback=validate_token,
        help="Figma API access token. Can also be set via FIGMA_ACCESS_TOKEN environment variable.",
    ),
) -> None:
    """Inspect a Figma file and show available content."""
    try:
        converter = FigmaRAGConverter(access_token)
        file_content = converter.get_file_content(file_key)
        
        if not file_content:
            console.print(Panel(
                "⚠️ No content found in this file.",
                title="Warning",
                style="yellow"
            ))
            return

        # Extract document name and type
        document = file_content.get("document", {})
        file_name = file_content.get("name", "Unnamed File")
        file_type = document.get("type", "Unknown")
        
        # Create summary table
        table = Table(title=f"File Content Summary: {file_name}")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Location", style="yellow")

        # Extract content recursively
        elements = converter.extract_text_content(document)
        
        # Count element types
        element_counts = {}
        for element in elements:
            element_type = element.get("type", "unknown")
            element_counts[element_type] = element_counts.get(element_type, 0) + 1
        
        # Add rows to table
        for element_type, count in element_counts.items():
            table.add_row(
                element_type.capitalize(),
                str(count),
                "Various locations"
            )

        console.print(Panel(
            "✅ Successfully accessed Figma file!",
            title="Connection Success",
            style="green"
        ))
        
        console.print(Panel(
            f"File Type: {file_type}\nTotal Elements: {len(elements)}",
            title="File Information",
            style="blue"
        ))
        
        console.print(table)
        
    except FigmaAPIError as e:
        console.print(Panel(
            f"❌ Failed to access Figma file: {str(e)}",
            title="Error",
            style="red"
        ))
        raise typer.Exit(code=1)

@app.command()
def convert(
    ctx: typer.Context,
    file_key: str = typer.Argument(..., help="Figma file identifier"),
    access_token: Optional[str] = typer.Option(
        None,
        "--access-token",
        "-t",
        callback=validate_token,
        help="Figma API access token. Can also be set via FIGMA_ACCESS_TOKEN environment variable.",
    ),
    output: Path = typer.Option(
        Path("components.jsonl"),
        "--output",
        "-o",
        help="Output file path"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed processing information"
    )
) -> None:
    """Convert Figma design elements to RAG-optimized format."""
    try:
        converter = FigmaRAGConverter(access_token)
        
        if verbose:
            console.print("🔍 Fetching file content...")
        
        documents = converter.process_file(file_key, output)
        
        if verbose:
            console.print(f"Processed {len(documents)} elements")
            type_counts = {}
            for doc in documents:
                doc_type = doc.metadata.get("type", "unknown")
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            for doc_type, count in type_counts.items():
                console.print(f"  - {count} {doc_type} elements")
        
        console.print(Panel(
            f"Successfully converted {len(documents)} elements to {output}",
            title="Success",
            style="green"
        ))
    except (FigmaAPIError, ConversionError) as e:
        console.print(Panel(
            str(e),
            title="Error",
            style="red"
        ))
        raise typer.Exit(code=1)

@app.command()
def help_token() -> None:
    """Show help about getting the Figma access token."""
    help_text = """
To get your Figma access token:

1. Log in to Figma (https://www.figma.com)
2. Go to Account Settings (click your profile picture → Settings)
3. Scroll to "Access tokens" section
4. Click "Generate new token"
5. Give it a name (e.g., "RAG Converter")
6. Copy the token immediately (you won't see it again!)

To get your file key:
The file key is in your Figma file URL:
https://www.figma.com/file/XXXXXXXXXXXXX/FileName
                            ↑
                       This is your file key

Note: Make sure you have appropriate access permissions to the file.
"""
    console.print(Panel(help_text, title="Getting Started", style="blue"))

if __name__ == "__main__":
    app()