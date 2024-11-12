from typing import Optional

class FigmaToRAGError(Exception):
    """Base exception for all figma-to-rag errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class FigmaAPIError(FigmaToRAGError):
    """
    Raised when there's an error communicating with the Figma API.
    
    Examples:
        * Authentication failures
        * Rate limiting
        * Network errors
        * Invalid API responses
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[dict] = None
    ):
        details = {
            "status_code": status_code,
            "response_body": response_body
        }
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body

class ConversionError(FigmaToRAGError):
    """
    Raised when there's an error converting Figma components to RAG format.
    
    Examples:
        * Invalid component structure
        * Missing required fields
        * Data validation errors
    """
    
    def __init__(
        self,
        message: str,
        component_id: Optional[str] = None,
        component_name: Optional[str] = None
    ):
        details = {
            "component_id": component_id,
            "component_name": component_name
        }
        super().__init__(message, details)
        self.component_id = component_id
        self.component_name = component_name

class ValidationError(FigmaToRAGError):
    """
    Raised when there's an error validating input or output data.
    
    Examples:
        * Invalid data types
        * Missing required fields
        * Data format violations
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        validation_errors: Optional[list] = None
    ):
        details = {
            "field_name": field_name,
            "validation_errors": validation_errors
        }
        super().__init__(message, details)
        self.field_name = field_name
        self.validation_errors = validation_errors

class FileOperationError(FigmaToRAGError):
    """
    Raised when there's an error performing file operations.
    
    Examples:
        * Permission denied
        * Disk space issues
        * Invalid file paths
    """
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None
    ):
        details = {
            "file_path": file_path,
            "operation": operation
        }
        super().__init__(message, details)
        self.file_path = file_path
        self.operation = operation

class ConfigurationError(FigmaToRAGError):
    """
    Raised when there's an error in the configuration.
    
    Examples:
        * Missing required environment variables
        * Invalid configuration values
        * Conflicting settings
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        invalid_value: Optional[str] = None
    ):
        details = {
            "config_key": config_key,
            "invalid_value": invalid_value
        }
        super().__init__(message, details)
        self.config_key = config_key
        self.invalid_value = invalid_value

def handle_api_error(status_code: int, response_body: Optional[dict] = None) -> FigmaAPIError:
    """
    Helper function to create appropriate FigmaAPIError based on status code.
    
    Args:
        status_code (int): HTTP status code
        response_body (Optional[dict]): Response body from the API
        
    Returns:
        FigmaAPIError: Appropriate error instance with helpful message
    """
    error_messages = {
        400: "Bad request - please check your input parameters",
        401: "Authentication failed - please check your access token",
        403: "Access forbidden - you don't have permission to access this resource",
        404: "Resource not found - please check the file or component ID",
        429: "Rate limit exceeded - please try again later",
        500: "Figma API server error - please try again later",
        502: "Bad gateway - Figma API is temporarily unavailable",
        503: "Service unavailable - Figma API is temporarily unavailable",
        504: "Gateway timeout - request to Figma API timed out"
    }
    
    message = error_messages.get(
        status_code,
        f"Unexpected error occurred with status code: {status_code}"
    )
    
    return FigmaAPIError(
        message=message,
        status_code=status_code,
        response_body=response_body
    )
