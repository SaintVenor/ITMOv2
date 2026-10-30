class ServiceError(Exception):
    """Базовое исключение бизнес-слоя; web/ переводит его в HTTP-ответ."""

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


class NotFound(ServiceError):
    pass


class Forbidden(ServiceError):
    pass


class Conflict(ServiceError):
    pass


class ValidationError(ServiceError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(errors.values()))
        self.errors = errors
