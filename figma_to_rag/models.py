from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

class FigmaComponent(BaseModel):
    """Representation of a Figma component with its properties."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: Optional[str] = Field(default=None)
    key: str
    component_id: str
    props: Dict[str, Any] = Field(default_factory=dict)
    variants: List[Dict[str, Any]] = Field(default_factory=list)

class RAGDocument(BaseModel):
    """Standard RAG document format."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    content: str
    metadata: Dict[str, Any] = Field(
        description="Additional metadata about the document",
        default_factory=dict
    )

class FigmaAPIResponse(BaseModel):
    """Representation of a Figma API response."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: int = Field(description="HTTP status code")
    data: Dict[str, Any] = Field(
        description="Response data from Figma API",
        default_factory=dict
    )
    error: Optional[str] = Field(default=None, description="Error message if any")

class FigmaComponentSet(BaseModel):
    """Representation of a Figma component set."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    key: str
    components: List[FigmaComponent] = Field(default_factory=list)
    description: Optional[str] = None
    documentation: Optional[str] = None