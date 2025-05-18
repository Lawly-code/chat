class ServiceError(Exception):
    """Базовый класс для всех ошибок сервиса"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AccessDeniedError(ServiceError):
    """Ошибка доступа"""

    pass


class NotFoundError(ServiceError):
    """Ошибка, когда запрашиваемый объект не найден"""

    pass


class ValidationError(ServiceError):
    """Ошибка валидации данных"""

    pass


class ParameterError(ServiceError):
    """Ошибка параметров запроса"""

    pass
