# figma-to-rag
Convert Figma components into a format optimized for RAG (Retrieval-Augmented Generation) workflows. This tool helps bridge the gap between design systems and AI-assisted development by making your Figma components queryable through RAG.



## Features ✨

Extract component metadata, properties, and variants from Figma
Convert components into RAG-optimized format with content and metadata fields
Rich CLI with progress indicators
Environment variable support
Comprehensive error handling and logging
Pydantic models for data validation
Output in JSONL format for easy integration with RAG pipelines

## Installation 🚀

### Using pip
```
pip install figma-to-rag
```

### Using Poetry (for development)
```
git clone https://github.com/yourusername/figma-to-rag.git
cd figma-to-rag
poetry install
```

## Usage 💻

### Command Line Interface

1. Set your Figma access token (either method)
```
# Option 1: Environment variable
export FIGMA_ACCESS_TOKEN=your_token_here

# Option 2: Pass directly to CLI
figma-to-rag convert your-file-key --access-token your_token_here
```
1. Basic usage:
```
figma-to-rag convert your-file-key
```

1. Specify output location:
```
figma-to-rag convert your-file-key -o output/components.jsonl
```

## Python API
```
from figma_to_rag import FigmaRAGConverter

# Initialize converter
converter = FigmaRAGConverter(access_token="your_token_here")

# Process entire file
documents = converter.process_file(
    file_key="your_file_key",
    output_path="components.jsonl"
)

# Or process components individually
components = converter.get_file_components("your_file_key")
for component_data in components:
    component = converter.parse_component(component_data)
    rag_doc = converter.convert_to_rag_format(component)
```

## Output Format 📄
The tool generates a JSONL file where each line is a JSON object with the following structure:
```
{
  "content": "Component: Button\nDescription: Primary action button component\nProperties: {\n  \"variant\": \"primary\",\n  \"size\": \"medium\",\n  \"disabled\": false\n}\nVariants: 6 variant(s)",
  "metadata": {
    "type": "figma_component",
    "component_key": "btn-123",
    "component_id": "1:123",
    "name": "Button",
    "props": {
      "variant": "primary",
      "size": "medium",
      "disabled": false
    },
    "variant_count": 6
  }
}
```

## Integration Examples 🔄
### LangChain
```
from langchain.document_loaders import JSONLoader

# Load documents
loader = JSONLoader(
    file_path="components.jsonl",
    jq_schema='.content',
    metadata_func=lambda x: x.get('metadata', {})
)
documents = loader.load()

# Create vector store
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents, embeddings)
```
### LlamaIndex
```
from llama_index import SimpleDirectoryReader, VectorStoreIndex
from llama_index.node_parser import SimpleNodeParser

# Load and parse documents
reader = SimpleDirectoryReader(input_files=["components.jsonl"])
documents = reader.load_data()

# Create index
parser = SimpleNodeParser()
nodes = parser.get_nodes_from_documents(documents)
index = VectorStoreIndex(nodes)
```

## Development 🛠️
Setup
```
# Clone repository
git clone https://github.com/yourusername/figma-to-rag.git
cd figma-to-rag

# Install dependencies with Poetry
poetry install

# Run tests
poetry run pytest

# Run type checks
poetry run mypy figma_to_rag

# Format code
poetry run black figma_to_rag
poetry run isort figma_to_rag
```

Running Tests
```
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=figma_to_rag

# Run specific test file
poetry run pytest tests/test_converter.py
```

#Contributing 🤝

Fork the repository

Create your feature branch (`git checkout -b feature/AmazingFeature`)

Run tests and type checks (`poetry run pytest && poetry run mypy figma_to_rag`)

Commit your changes (`git commit -m 'Add some AmazingFeature'`)

Push to the branch (`git push origin feature/AmazingFeature`)

Open a Pull Request

## Support 💬

📫 For bugs and feature requests, please open an issue

💡 For questions and discussions, please use GitHub Discussions

📖 Check out our Wiki for additional documentation

## Acknowledgments 🙏

Figma API Documentation
RAG (Retrieval-Augmented Generation) research papers
The open-source community
All contributors
