import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.logging import RichHandler
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.traceback import install

from .converter import FigmaRAGConverter
from .processors.openai_processor import OpenAIProcessor
from .exceptions import FigmaAPIError, ConversionError, ProcessingError
from .models import RAGDocument

# Install rich traceback handler
install(show_locals=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("figma-to-rag")

# Create Typer app
app = typer.Typer(
    help="Convert Figma designs to RAG-optimized format",
    add_completion=False
)
console = Console()

def setup_output_dir(output_dir: Path) -> None:
    """Setup output directory with logs and data folders."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "logs").mkdir(exist_ok=True)
        (output_dir / "data").mkdir(exist_ok=True)
    except Exception as e:
        raise ProcessingError(f"Failed to create output directories: {str(e)}")

def validate_token(
    ctx: typer.Context, 
    token: Optional[str], 
    env_var: str,
    error_message: str
) -> Optional[str]:
    """Validate token from CLI or environment."""
    if token:
        return token
    env_token = os.getenv(env_var)
    if env_token:
        return env_token
    console.print(Panel(
        error_message,
        title="Error",
        style="red"
    ))
    ctx.exit(1)
    return None

def save_jsonl(documents: List[Dict[str, Any]], output_path: Path) -> None:
    """Save documents to JSONL format with error handling."""
    try:
        with open(output_path, 'w') as f:
            for doc in documents:
                f.write(json.dumps(doc) + '\n')
    except Exception as e:
        raise ProcessingError(f"Failed to save output: {str(e)}")

@app.command()
def inspect(
    ctx: typer.Context,
    file_key: str = typer.Argument(..., help="Figma file identifier"),
    access_token: Optional[str] = typer.Option(
        None,
        "--access-token",
        "-t",
        help="Figma API access token. Can also be set via FIGMA_ACCESS_TOKEN environment variable.",
        envvar="FIGMA_ACCESS_TOKEN"
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        "-o",
        help="Output directory for inspection results"
    ),
) -> None:
    """Inspect a Figma file and show detailed content analysis."""
    try:
        # Validate token
        token = validate_token(
            ctx, 
            access_token, 
            "FIGMA_ACCESS_TOKEN",
            "No Figma access token provided. Please provide via --access-token or set FIGMA_ACCESS_TOKEN environment variable."
        )

        # Setup output directory
        setup_output_dir(output_dir)
        
        # Setup logging
        log_file = output_dir / "logs" / f"inspect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        logger.addHandler(file_handler)
        
        converter = FigmaRAGConverter(token)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Fetch file content
            task = progress.add_task("Fetching file content...", total=None)
            file_content = converter.get_file_content(file_key)
            progress.update(task, completed=True)
            
            # Extract document info
            document = file_content.get("document", {})
            file_name = file_content.get("name", "Unnamed File")
            
            # Extract elements
            task = progress.add_task("Analyzing elements...", total=None)
            elements = converter.extract_text_content(document)
            progress.update(task, completed=True)
        
        # Create summary table
        table = Table(title=f"File Content Summary: {file_name}")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Location", style="yellow")
        
        # Count element types
        element_counts = {}
        element_locations = {}
        for element in elements:
            element_type = element.get("type", "unknown")
            element_counts[element_type] = element_counts.get(element_type, 0) + 1
            
            path = element.get("path", "unknown")
            if element_type not in element_locations:
                element_locations[element_type] = set()
            element_locations[element_type].add(path)
        
        # Add rows to table
        for element_type, count in element_counts.items():
            locations = list(element_locations[element_type])
            location_str = f"{len(locations)} unique locations"
            table.add_row(
                element_type.capitalize(),
                str(count),
                location_str
            )
        
        # Print results
        console.print(Panel(
            "✅ Analysis Complete",
            title="Success",
            style="green"
        ))
        
        console.print(Panel(
            f"File: {file_name}\nTotal Elements: {len(elements)}",
            title="File Information",
            style="blue"
        ))
        
        console.print(table)
        
        # Save analysis
        analysis_file = output_dir / "data" / f"analysis_{file_key}.json"
        with open(analysis_file, 'w') as f:
            json.dump({
                "file_name": file_name,
                "element_counts": element_counts,
                "element_locations": {k: list(v) for k, v in element_locations.items()},
                "total_elements": len(elements)
            }, f, indent=2)
            
        logger.info(f"Analysis saved to {analysis_file}")
        
    except Exception as e:
        logger.error(f"Inspection failed: {str(e)}", exc_info=True)
        console.print(Panel(
            f"❌ Failed to inspect file: {str(e)}",
            title="Error",
            style="red"
        ))
        raise typer.Exit(1)
    finally:
        if 'file_handler' in locals():
            logger.removeHandler(file_handler)

@app.command()
def convert(
    ctx: typer.Context,
    file_key: str = typer.Argument(..., help="Figma file identifier"),
    access_token: Optional[str] = typer.Option(
        None,
        "--access-token",
        "-t",
        help="Figma API access token. Can also be set via FIGMA_ACCESS_TOKEN environment variable.",
        envvar="FIGMA_ACCESS_TOKEN"
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        "-o",
        help="Output directory"
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
        # Validate token
        token = validate_token(
            ctx, 
            access_token, 
            "FIGMA_ACCESS_TOKEN",
            "No Figma access token provided. Please provide via --access-token or set FIGMA_ACCESS_TOKEN environment variable."
        )
        
        # Setup output directory
        setup_output_dir(output_dir)
        
        # Setup logging
        log_file = output_dir / "logs" / f"convert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        logger.addHandler(file_handler)
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        converter = FigmaRAGConverter(token)
        output_file = output_dir / "data" / f"{file_key}_raw.jsonl"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Process file
            task = progress.add_task("Converting file...", total=None)
            documents = converter.process_file(file_key, output_file)
            progress.update(task, completed=True)
            
            if verbose:
                for doc in documents:
                    logger.debug(f"Processed: {doc.metadata.get('name', 'Unnamed')}")
        
        console.print(Panel(
            f"Successfully converted {len(documents)} elements to {output_file}",
            title="Success",
            style="green"
        ))
        
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}", exc_info=True)
        console.print(Panel(
            f"❌ Failed to convert file: {str(e)}",
            title="Error",
            style="red"
        ))
        raise typer.Exit(1)
    finally:
        if 'file_handler' in locals():
            logger.removeHandler(file_handler)

@app.command()
def process(
    ctx: typer.Context,
    input_file: Path = typer.Argument(..., help="Input JSONL file from Figma conversion"),
    openai_key: Optional[str] = typer.Option(
        None,
        "--openai-key",
        "-k",
        help="OpenAI API key. Can also be set via OPENAI_API_KEY environment variable.",
        envvar="OPENAI_API_KEY"
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir",
        "-o",
        help="Output directory"
    ),
    model: str = typer.Option(
        "gpt-4",
        "--model",
        "-m",
        help="OpenAI model to use"
    ),
    batch_size: int = typer.Option(
        5,
        "--batch-size",
        "-b",
        help="Number of elements to process in parallel"
    ),
    retry_attempts: int = typer.Option(
        3,
        "--retry",
        "-r",
        help="Number of retry attempts for failed processing"
    )
) -> None:
    """Process Figma content using OpenAI to create RAG-optimized content."""
    try:
        # Validate token
        token = validate_token(
            ctx, 
            openai_key, 
            "OPENAI_API_KEY",
            "No OpenAI API key provided. Please provide via --openai-key or set OPENAI_API_KEY environment variable."
        )
        
        # Setup output directory
        setup_output_dir(output_dir)
        
        # Setup logging
        log_file = output_dir / "logs" / f"process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        logger.addHandler(file_handler)
        
        # Read input file
        if not input_file.exists():
            raise ProcessingError(f"Input file not found: {input_file}")
        
        with open(input_file, 'r') as f:
            elements = [json.loads(line) for line in f]
        
        processor = OpenAIProcessor(token, model)
        output_file = output_dir / "data" / f"processed_{input_file.stem}.jsonl"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"Processing {len(elements)} elements...", 
                total=len(elements)
            )
            
            documents = []
            failed_elements = []
            
            for i in range(0, len(elements), batch_size):
                batch = elements[i:i + batch_size]
                
                for attempt in range(retry_attempts):
                    try:
                        processed_batch = asyncio.run(
                            processor.batch_process(batch, batch_size)
                        )
                        documents.extend(processed_batch)
                        progress.update(task, advance=len(batch))
                        break
                    except Exception as e:
                        if attempt == retry_attempts - 1:
                            logger.error(f"Failed to process batch after {retry_attempts} attempts")
                            failed_elements.extend(batch)
                        else:
                            logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                            continue
        
        # Save processed documents
        save_jsonl([doc.dict() for doc in documents], output_file)
        
        # Save failed elements if any
        if failed_elements:
            failed_file = output_dir / "data" / f"failed_{input_file.stem}.jsonl"
            save_jsonl(failed_elements, failed_file)
            logger.warning(f"Failed elements saved to {failed_file}")
        
        # Print summary
        console.print(Panel(
            f"""Processing Summary:
- Successfully processed: {len(documents)} elements
- Failed to process: {len(failed_elements)} elements
- Output saved to: {output_file}""",
            title="Success",
            style="green"
        ))
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        console.print(Panel(
            f"❌ Failed to process elements: {str(e)}",
            title="Error",
            style="red"
        ))
        raise typer.Exit(1)
    finally:
        if 'file_handler' in locals():
            logger.removeHandler(file_handler)

@app.command()
def help_token() -> None:
    """Show help about getting the required API tokens."""
    help_text = """
Figma Access Token:
1. Log in to Figma (https://www.figma.com)
2. Go to Account Settings (click your profile picture → Settings)
3. Scroll to "Access tokens" section
4. Click "Generate new token"
5. Give it a name (e.g., "RAG Converter")
6. Copy the token immediately (you won't see it again!)

OpenAI API Key:
1. Go to OpenAI website (https://platform.openai.com)
2. Sign in to your account
3. Go to API settings
4. Create new API key
5. Copy the key (you won't see it again!)

File Key:
The file key is in your Figma file URL:
https://www.figma.com/file/XXXXXXXXXXXXX/FileName
                            ↑
                       This is your file key

Environment Variables:
You can set these environment variables instead of passing them as arguments:
- FIGMA
- ACCESS_TOKEN=your_figma_token
- OPENAI_API_KEY=your_openai_key

Workflow Example:
1. First inspect the Figma file:
   figma-to-rag inspect your_file_key

2. Convert to RAG format:
   figma-to-rag convert your_file_key --output-dir ./output

3. Process with OpenAI:
   figma-to-rag process ./output/data/your_file_key_raw.jsonl
"""
    console.print(Panel(help_text, title="Getting Started", style="blue"))

@app.command()
def validate(
    ctx: typer.Context,
    input_file: Path = typer.Argument(..., help="Processed JSONL file to validate"),
    schema_file: Optional[Path] = typer.Option(
        None,
        "--schema",
        "-s",
        help="Custom JSON schema file for validation"
    )
) -> None:
    """Validate processed RAG documents against schema."""
    try:
        # Setup logging
        log_file = Path("logs") / f"validate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        logger.addHandler(file_handler)
        
        if not input_file.exists():
            raise ProcessingError(f"Input file not found: {input_file}")
        
        validation_errors = []
        processed_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            # Read and validate documents
            task = progress.add_task("Validating documents...", total=None)
            
            with open(input_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        doc_data = json.loads(line)
                        RAGDocument(**doc_data)  # Validate against Pydantic model
                        processed_count += 1
                    except Exception as e:
                        validation_errors.append({
                            "line": line_num,
                            "error": str(e)
                        })
            
            progress.update(task, completed=True)
        
        # Create validation report
        if validation_errors:
            console.print(Panel(
                f"""Validation Results:
- Total documents: {processed_count + len(validation_errors)}
- Valid documents: {processed_count}
- Invalid documents: {len(validation_errors)}
                """,
                title="Warning",
                style="yellow"
            ))
            
            # Show detailed errors
            error_table = Table(title="Validation Errors")
            error_table.add_column("Line", style="cyan")
            error_table.add_column("Error", style="red")
            
            for error in validation_errors:
                error_table.add_row(
                    str(error["line"]),
                    error["error"]
                )
            
            console.print(error_table)
        else:
            console.print(Panel(
                f"All {processed_count} documents are valid!",
                title="Success",
                style="green"
            ))
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}", exc_info=True)
        console.print(Panel(
            f"❌ Failed to validate documents: {str(e)}",
            title="Error",
            style="red"
        ))
        raise typer.Exit(1)
    finally:
        if 'file_handler' in locals():
            logger.removeHandler(file_handler)

@app.command()
def stats(
    ctx: typer.Context,
    input_file: Path = typer.Argument(..., help="Processed JSONL file to analyze"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for statistics (JSON format)"
    )
) -> None:
    """Generate statistics about processed RAG documents."""
    try:
        if not input_file.exists():
            raise ProcessingError(f"Input file not found: {input_file}")
        
        stats_data = {
            "total_documents": 0,
            "element_types": {},
            "avg_content_length": 0,
            "metadata_fields": set(),
            "style_tokens": set()
        }
        
        content_lengths = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing documents...", total=None)
            
            with open(input_file, 'r') as f:
                for line in f:
                    try:
                        doc = json.loads(line)
                        
                        # Count documents
                        stats_data["total_documents"] += 1
                        
                        # Track element types
                        element_type = doc.get("metadata", {}).get("element_type", "unknown")
                        stats_data["element_types"][element_type] = stats_data["element_types"].get(element_type, 0) + 1
                        
                        # Track content length
                        content_length = len(doc.get("content", ""))
                        content_lengths.append(content_length)
                        
                        # Track metadata fields
                        stats_data["metadata_fields"].update(doc.get("metadata", {}).keys())
                        
                        # Track style tokens
                        if "style_tokens" in doc.get("metadata", {}):
                            stats_data["style_tokens"].update(doc["metadata"]["style_tokens"].keys())
                    
                    except Exception as e:
                        logger.warning(f"Error processing document: {str(e)}")
                        continue
            
            progress.update(task, completed=True)
        
        # Calculate averages
        if content_lengths:
            stats_data["avg_content_length"] = sum(content_lengths) / len(content_lengths)
        
        # Convert sets to lists for JSON serialization
        stats_data["metadata_fields"] = list(stats_data["metadata_fields"])
        stats_data["style_tokens"] = list(stats_data["style_tokens"])
        
        # Create statistics table
        table = Table(title="Document Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Documents", str(stats_data["total_documents"]))
        table.add_row("Average Content Length", f"{stats_data['avg_content_length']:.2f} characters")
        table.add_row("Element Types", ", ".join(f"{k}: {v}" for k, v in stats_data["element_types"].items()))
        table.add_row("Metadata Fields", ", ".join(stats_data["metadata_fields"]))
        table.add_row("Style Tokens", ", ".join(stats_data["style_tokens"]))
        
        console.print(table)
        
        # Save statistics if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(stats_data, f, indent=2)
            console.print(Panel(
                f"Statistics saved to {output_file}",
                title="Success",
                style="green"
            ))
        
    except Exception as e:
        logger.error(f"Statistics generation failed: {str(e)}", exc_info=True)
        console.print(Panel(
            f"❌ Failed to generate statistics: {str(e)}",
            title="Error",
            style="red"
        ))
        raise typer.Exit(1)

def main():
    """Entry point for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n❌ Operation cancelled by user", style="yellow")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"❌ Unexpected error: {str(e)}", style="red")
        logger.error("Unexpected error", exc_info=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    main()