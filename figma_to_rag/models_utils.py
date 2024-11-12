from typing import Dict, Any, TypeVar, Type, Optional
from .models import FigmaComponent, RAGDocument, FigmaAPIResponse

T = TypeVar('T')

def ensure_dict(value: Any) -> Dict[str, Any]:
    """Ensure a value is a dictionary."""
    if isinstance(value, dict):
        return value
    return {}

def safe_create_model(
    model_cls: Type[T],
    data: Dict[str, Any],
    default: Optional[T] = None
) -> Optional[T]:
    """
    Safely create a Pydantic model instance.
    
    Args:
        model_cls: The Pydantic model class to instantiate
        data: The data to create the model from
        default: Default value if creation fails
        
    Returns:
        Optional[T]: Model instance or default value
    """
    try:
        return model_cls(**data)
    except Exception as e:
        if default is not None:
            return default
        raise ValueError(f"Failed to create {model_cls.__name__}: {str(e)}") from e

def component_to_rag(component: FigmaComponent) -> RAGDocument:
    """Convert a FigmaComponent to a RAGDocument."""
    content = f"""
Component: {component.name}
Description: {component.description or 'No description provided'}
Properties: {component.props}
Variants: {len(component.variants)} variant(s)
    """.strip()
    
    return RAGDocument(
        content=content,
        metadata={
            "type": "figma_component",
            "component_key": component.key,
            "component_id": component.component_id,
            "name": component.name,
            "props": component.props,
            "variant_count": len(component.variants)
        }
    )
