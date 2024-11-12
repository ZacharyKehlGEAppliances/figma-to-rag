import os
from pathlib import Path
import pytest
import responses
from typer.testing import CliRunner
from figma_to_rag.cli import app

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_figma_response():
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://api.figma.com/v1/files/test-file/components",
            json={
                "meta": {
                    "components": [
                        {
                            "name": "Button",
                            "key": "btn-123",
                            "node_id": "1:123",
                            "description": "Test button"
                        }
                    ]
                }
            },
            status=200
        )
        yield rsps

def test_cli_missing_token(runner):
    # Ensure environment variable is not set
    if "FIGMA_ACCESS_TOKEN" in os.environ:
        del os.environ["FIGMA_ACCESS_TOKEN"]
    
    result = runner.invoke(app, ["convert", "test-file"])
    assert result.exit_code == 1
    assert "No access token provided" in result.stdout

def test_cli_with_token(runner, mock_figma_response, tmp_path):
    output_file = tmp_path / "output.jsonl"
    
    result = runner.invoke(app, [
        "convert",
        "test-file",
        "--access-token", "test-token",
        "--output", str(output_file)
    ])
    
    assert result.exit_code == 0
    assert "Successfully converted" in result.stdout
    assert output_file.exists()

def test_cli_with_env_token(runner, mock_figma_response, tmp_path, monkeypatch):
    monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
    output_file = tmp_path / "output.jsonl"
    
    result = runner.invoke(app, [
        "convert",
        "test-file",
        "--output", str(output_file)
    ])
    
    assert result.exit_code == 0
    assert "Successfully converted" in result.stdout
    assert output_file.exists()

def test_cli_invalid_file(runner):
    result = runner.invoke(app, [
        "convert",
        "invalid-file",
        "--access-token", "test-token"
    ])
    
    assert result.exit_code == 1
    assert "Error" in result.stdout