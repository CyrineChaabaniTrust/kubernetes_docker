import logging
import traceback
from functools import wraps

logger = logging.getLogger(__name__)

class CrossplaneError(Exception):
    """Base exception class for Crossplane chatbot errors"""
    def __init__(self, message, user_message=None, details=None):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An error occurred while processing your request."
        self.details = details

class ValidationError(CrossplaneError):
    """Error raised when input validation fails"""
    pass

class ResourceNotSupportedError(CrossplaneError):
    """Error raised when a requested resource is not supported"""
    pass

class ProviderNotSupportedError(CrossplaneError):
    """Error raised when a requested provider is not supported"""
    pass

class ManifestGenerationError(CrossplaneError):
    """Error raised when YAML manifest generation fails"""
    pass

def handle_errors(func):
    """Decorator to handle exceptions in a consistent way"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CrossplaneError as e:
            logger.error(f"Crossplane error: {e.message}", exc_info=True)
            return {"error": True, "message": e.user_message, "details": e.details}
        except Exception as e:
            error_id = generate_error_id()
            logger.critical(
                f"Unexpected error (ID: {error_id}): {str(e)}", 
                exc_info=True
            )
            return {
                "error": True, 
                "message": f"An unexpected error occurred. Error reference: {error_id}",
                "details": None
            }
    return wrapper

def generate_error_id():
    """Generate a unique ID for error tracking"""
    import uuid
    return str(uuid.uuid4())[:8]

def log_and_reraise(e, message=None, user_message=None):
    """Log an exception and re-raise it as a CrossplaneError"""
    logger.error(message or str(e), exc_info=True)
    error_details = {
        "exception": str(e),
        "traceback": traceback.format_exc()
    }
    raise CrossplaneError(
        message=message or str(e),
        user_message=user_message or f"An error occurred: {str(e)}",
        details=error_details
    ) 