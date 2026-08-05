"""Stable, user-safe errors raised by AI providers."""


class AIServiceError(Exception):
    code = "ai_error"
    public_message = "L'analyse IA n'a pas pu aboutir."
    retryable = False

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.public_message)
        self.detail = detail


class AIConfigurationError(AIServiceError):
    code = "configuration_error"
    public_message = "Le fournisseur IA n'est pas configuré."


class AIAuthenticationError(AIServiceError):
    code = "provider_authentication"
    public_message = "Le fournisseur IA a refusé l'authentification."


class AIQuotaError(AIServiceError):
    code = "provider_quota"
    public_message = "Le quota du fournisseur IA est atteint. Réessayez plus tard."


class AIProviderUnavailableError(AIServiceError):
    code = "provider_unavailable"
    public_message = "Le fournisseur IA est momentanément indisponible."
    retryable = True


class AIInvalidResponseError(AIServiceError):
    code = "invalid_provider_response"
    public_message = "Le fournisseur IA a renvoyé une réponse inexploitable."


class AIInvalidInputError(AIServiceError):
    code = "invalid_input"
    public_message = "Le brief ne peut pas être analysé dans son état actuel."
