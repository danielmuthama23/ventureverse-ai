class BandIntegrationError(RuntimeError):
    """Base error for BAND integration operations."""


class BandAuthenticationError(BandIntegrationError):
    """Raised when BAND credentials are missing or rejected."""


class BandConnectionError(BandIntegrationError):
    """Raised when BAND cannot be reached."""
