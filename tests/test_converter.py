import json
from pathlib import Path
import pytest
import responses
from figma_to_rag.converter import FigmaRAGConverter
from figma_to_rag.exceptions import FigmaAPIError, ConversionError
from figma_to_rag.models import FigmaComponent, RAGDocument

@pytest.fixture
def converter():
    return FigmaRAGConverter("test-token")

@pytest.fixture
def sample_component_data():
    return {
        "name": "Button",
        "description": "Primary button component",
        "key": "btn-123",
        "node_id": "1:123",
        "componentProperties": {
            "variant": "primary",
            "size": "medium"
        }
    }

@responses.activate
def test_get_file_components(converter):
    responses.add(
        responses.GET,
        "https://api.figma.com/v1/files/test-file/components",
        json={
            "meta": {
                "components": [
                    {
                        "name": "Button",
                        "key": "btn-123",
                        "node_id": "1:123"
                    }
                ]
            }
        },
        status=200
    )
    
    components = converter.get_file_components("test-file")
    assert len(components) == 1
    assert components[0]["name"] == "Button"

def test_parse_component(converter, sample_component_data):
    component = converter.parse_component(sample_component_data)
    assert isinstance(component, FigmaComponent)
    assert component.name == "Button"
    assert component.key == "btn-123"
    assert component.props == {"variant": "primary", "size": "medium"}

def test_convert_to_rag_format(converter, sample_component_data):
    component = converter.parse_component(sample_component_data)
    rag_doc = converter.convert_to_rag_format(component)
    
    assert isinstance(rag_doc, RAGDocument)
    assert "Button" in rag_doc.content
    assert rag_doc.metadata["component_key"] == "btn-123"
    assert rag_doc.metadata["type"] == "figma_component"

def test_save_to_jsonl(converter, tmp_path):
    test_doc = RAGDocument(
        content="Test content",
        metadata={"type": "figma_component"}
    )
    output_path = tmp_path / "test.jsonl"
    
    converter.save_to_jsonl([test_doc], output_path)
    
    assert output_path.exists()
    with open(output_path) as f:
        data = json.loads(f.readline())
        assert data["content"] == "Test content"