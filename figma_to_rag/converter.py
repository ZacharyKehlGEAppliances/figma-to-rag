import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Union, Any
import requests
from rich.progress import Progress, SpinnerColumn, TextColumn
from .models import FigmaComponent, RAGDocument, FigmaAPIResponse
from .exceptions import FigmaAPIError, ConversionError

logger = logging.getLogger(__name__)

class FigmaRAGConverter:
    """Converts Figma design elements to RAG-optimized format."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "X-Figma-Token": access_token,
            "Accept": "application/json"
        }

    def _make_request(self, url: str) -> FigmaAPIResponse:
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            return FigmaAPIResponse(
                status=response.status_code,
                data=response.json() if response.ok else {},
                error=None if response.ok else response.text
            )
        except requests.RequestException as e:
            raise FigmaAPIError(f"Failed to fetch data from Figma: {str(e)}")

    def get_file_content(self, file_key: str) -> Dict[str, Any]:
        """
        Fetch entire file content including frames and layers.
        """
        url = f"https://api.figma.com/v1/files/{file_key}"
        response = self._make_request(url)
        if response.error:
            raise FigmaAPIError(response.error)
        return response.data

    def extract_text_content(self, node: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
        """
        Recursively extract text content from nodes.
        """
        elements = []
        
        # Extract current node if it has text
        if node.get("type") == "TEXT":
            elements.append({
                "type": "text",
                "content": node.get("characters", ""),
                "style": node.get("style", {}),
                "path": path,
                "name": node.get("name", ""),
                "metadata": {
                    "id": node.get("id", ""),
                    "path": path,
                    "style": node.get("style", {}),
                    "constraints": node.get("constraints", {}),
                }
            })
        
        # Handle frame descriptions and names
        elif node.get("type") in ["FRAME", "GROUP", "SECTION"]:
            if node.get("name"):
                elements.append({
                    "type": "frame",
                    "content": f"Frame: {node.get('name')}",
                    "description": node.get("description", ""),
                    "path": path,
                    "name": node.get("name", ""),
                    "metadata": {
                        "id": node.get("id", ""),
                        "path": path,
                        "background": node.get("background", []),
                        "layoutMode": node.get("layoutMode", ""),
                        "counterAxisSizingMode": node.get("counterAxisSizingMode", ""),
                    }
                })
        
        # Process children recursively
        children = node.get("children", [])
        current_path = f"{path}/{node.get('name', '')}" if path else node.get('name', '')
        
        for child in children:
            elements.extend(self.extract_text_content(child, current_path))
        
        return elements

    def convert_to_rag_format(self, element: Dict[str, Any]) -> RAGDocument:
        """Convert design element to RAG format."""
        try:
            content = ""
            if element["type"] == "text":
                content = f"""
Text Content: {element['content']}
Location: {element['path']}
Style: {json.dumps(element['style'], indent=2)}
                """.strip()
            elif element["type"] == "frame":
                content = f"""
Frame: {element['name']}
Description: {element.get('description', 'No description')}
Path: {element['path']}
                """.strip()
            
            return RAGDocument(
                content=content,
                metadata={
                    "type": element["type"],
                    "path": element["path"],
                    "name": element["name"],
                    **element["metadata"]
                }
            )
        except Exception as e:
            raise ConversionError(f"Failed to convert element to RAG format: {str(e)}")

    def process_file(
        self, 
        file_key: str, 
        output_path: Union[str, Path]
    ) -> List[RAGDocument]:
        """Process entire Figma file and convert all relevant elements."""
        output_path = Path(output_path)
        converted_documents = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("Fetching file content...", total=None)
            file_content = self.get_file_content(file_key)
            
            if "document" not in file_content:
                raise FigmaAPIError("Invalid file content received from Figma")
            
            progress.add_task("Extracting elements...", total=None)
            elements = self.extract_text_content(file_content["document"])
            
            progress.add_task(f"Converting {len(elements)} elements...", total=None)
            for element in elements:
                try:
                    rag_doc = self.convert_to_rag_format(element)
                    converted_documents.append(rag_doc)
                except Exception as e:
                    logger.error(f"Error processing element: {str(e)}")
                    continue
            
            progress.add_task("Saving results...", total=None)
            self.save_to_jsonl(converted_documents, output_path)
            
        return converted_documents

    def save_to_jsonl(
        self, 
        documents: List[RAGDocument], 
        output_path: Path
    ) -> None:
        """Save converted elements to JSONL format."""
        try:
            with open(output_path, 'w') as f:
                for doc in documents:
                    f.write(doc.model_dump_json() + '\n')
        except IOError as e:
            raise ConversionError(f"Failed to save output: {str(e)}")