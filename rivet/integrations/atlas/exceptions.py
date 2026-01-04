"""Custom exceptions for Atlas CMMS integration.

This module defines a hierarchy of exceptions for handling various error
conditions that may occur when interacting with the Atlas CMMS API.
"""


class AtlasError(Exception):
    """Base exception for all Atlas CMMS integration errors.

    This is the parent class for all Atlas-related exceptions. Catching this
    will catch any Atlas-specific error.

    Attributes:
        message: Human-readable error description
        details: Optional dictionary with additional error context
    """

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class AtlasAuthError(AtlasError):
    """Authentication or authorization failed.

    Raised when:
    - Invalid credentials provided during login
    - JWT token is expired or invalid
    - User lacks permission for requested operation
    - Token refresh fails

    Example:
        raise AtlasAuthError(
            "Invalid credentials",
            details={"email": "admin@example.com"}
        )
    """

    pass


class AtlasAPIError(AtlasError):
    """Generic API communication error.

    Raised when:
    - Network connectivity issues occur
    - Atlas server returns 5xx error
    - Request times out
    - Unexpected response format received

    Attributes:
        status_code: HTTP status code if applicable
        response_body: Raw response content if available

    Example:
        raise AtlasAPIError(
            "Connection timeout",
            details={"timeout": 30, "endpoint": "/work-orders"}
        )
    """

    def __init__(self, message: str, details: dict = None, status_code: int = None, response_body: str = None):
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body


class AtlasNotFoundError(AtlasError):
    """Requested resource does not exist (404).

    Raised when:
    - Work order ID not found
    - Asset ID not found
    - User ID not found
    - Endpoint does not exist

    Example:
        raise AtlasNotFoundError(
            "Work order not found",
            details={"work_order_id": "WO-12345"}
        )
    """

    pass


class AtlasValidationError(AtlasError):
    """Request validation failed (400).

    Raised when:
    - Required fields are missing
    - Field values are invalid (wrong type, out of range)
    - Business logic constraints violated

    Attributes:
        field_errors: Dictionary mapping field names to error messages

    Example:
        raise AtlasValidationError(
            "Invalid work order data",
            details={"field_errors": {"title": "Title is required"}}
        )
    """

    def __init__(self, message: str, details: dict = None, field_errors: dict = None):
        super().__init__(message, details)
        self.field_errors = field_errors or {}


class AtlasRateLimitError(AtlasError):
    """Rate limit exceeded (429).

    Raised when:
    - Too many requests sent to Atlas API
    - Atlas returns 429 status code

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header)

    Example:
        raise AtlasRateLimitError(
            "Rate limit exceeded",
            details={"retry_after": 60}
        )
    """

    def __init__(self, message: str, details: dict = None, retry_after: int = None):
        super().__init__(message, details)
        self.retry_after = retry_after


class AtlasConfigError(AtlasError):
    """Atlas configuration is invalid or missing.

    Raised when:
    - Required environment variables are missing
    - Configuration values are invalid
    - Atlas is disabled but integration attempted

    Example:
        raise AtlasConfigError(
            "ATLAS_BASE_URL not configured",
            details={"required_vars": ["ATLAS_BASE_URL", "ATLAS_EMAIL"]}
        )
    """

    pass
