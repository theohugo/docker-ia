"""Public API for structured AI analysis."""

from .analysis import AnalysisOutput, analyse_brief
from .exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidInputError,
    AIInvalidResponseError,
    AIProviderUnavailableError,
    AIQuotaError,
    AIServiceError,
)

__all__ = (
    "AIAuthenticationError",
    "AIConfigurationError",
    "AIInvalidInputError",
    "AIInvalidResponseError",
    "AIProviderUnavailableError",
    "AIQuotaError",
    "AIServiceError",
    "AnalysisOutput",
    "analyse_brief",
)
