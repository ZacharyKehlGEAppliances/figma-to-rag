import json
from typing import List, Dict, Any
import openai
from pydantic import BaseModel, Field
from ..models import RAGDocument

class ProcessedDesignElement(BaseModel):
    """Structured format for design system elements."""
    element_type: str = Field(..., description="Type of design element (text, frame, component)")
    title: str = Field(..., description="Name or title of the element")
    description: str = Field(..., description="Descriptive content about the element")
    context: str = Field(..., description="Where this element exists in the design hierarchy")
    style_tokens: Dict[str, Any] = Field(default_factory=dict, description="Relevant style information")
    usage_guidelines: str = Field(default="", description="How to use this element")
    related_elements: List[str] = Field(default_factory=list, description="Related design elements")

class OpenAIProcessor:
    """Process Figma content using OpenAI for better RAG formatting."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize with OpenAI API key."""
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def _create_system_prompt(self) -> str:
        return """You are a design system documentation expert. Your task is to analyze Figma design elements and create clear, structured documentation.
Please format your response as JSON with the following structure:
{
    "element_type": "type of the design element",
    "title": "clear name/title",
    "description": "comprehensive description",
    "context": "usage context and location",
    "style_tokens": {"key style information"},
    "usage_guidelines": "how to use this element",
    "related_elements": ["related components or styles"]
}"""

    def _create_user_prompt(self, element: Dict[str, Any]) -> str:
        return f"""Please analyze this Figma design element and provide structured documentation:

Element Data:
{json.dumps(element, indent=2)}

Focus on making the content useful for designers and developers using the design system.
Ensure your response is valid JSON matching the specified structure."""

    async def process_element(self, element: Dict[str, Any]) -> ProcessedDesignElement:
        """Process a single design element using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._create_system_prompt()},
                    {"role": "user", "content": self._create_user_prompt(element)}
                ],
                temperature=0.7,
            )
            
            # Parse the response text as JSON
            content = json.loads(response.choices[0].message.content)
            return ProcessedDesignElement(**content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse OpenAI response as JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to process element: {str(e)}")

    def create_rag_document(self, processed: ProcessedDesignElement) -> RAGDocument:
        """Convert processed element into RAG document format."""
        content = f"""
# {processed.title}

## Description
{processed.description}

## Usage Guidelines
{processed.usage_guidelines}

## Context
{processed.context}

## Style Information
{json.dumps(processed.style_tokens, indent=2)}

## Related Elements
{', '.join(processed.related_elements)}
        """.strip()
        
        return RAGDocument(
            content=content,
            metadata={
                "element_type": processed.element_type,
                "title": processed.title,
                "context": processed.context,
                "related_elements": processed.related_elements,
                "style_tokens": processed.style_tokens
            }
        )

    async def batch_process(
        self, 
        elements: List[Dict[str, Any]], 
        batch_size: int = 5
    ) -> List[RAGDocument]:
        """Process multiple elements in batches."""
        processed_documents = []
        failed_elements = []
        
        for i in range(0, len(elements), batch_size):
            batch = elements[i:i + batch_size]
            processed_batch = []
            
            for element in batch:
                try:
                    processed = await self.process_element(element)
                    rag_doc = self.create_rag_document(processed)
                    processed_batch.append(rag_doc)
                except Exception as e:
                    failed_elements.append({
                        "element": element,
                        "error": str(e)
                    })
                    continue
            
            processed_documents.extend(processed_batch)
        
        return processed_documents