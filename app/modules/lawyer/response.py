from modules.lawyer.dto import (
    LawyerResponsesDTO,
    LawyerRequestsDTO,
    LawyerRequestCreateResponseDTO,
)

get_lawyer_requests_response = {
    401: {"description": "Неверные учетные данные"},
    200: {"description": "Список заявок юриста", "model": LawyerRequestsDTO},
    403: {"description": "Доступ запрещен. Пользователь не является юристом."},
}

get_lawyer_responses_response = {
    401: {"description": "Неверные учетные данные"},
    200: {"description": "Список заявок юриста", "model": LawyerResponsesDTO},
    403: {"description": "Доступ запрещен. Пользователь не является юристом."},
    404: {"description": "Заявки не найдены"},
}

update_lawyer_request_response = {
    401: {"description": "Неверные учетные данные"},
    202: {"description": "Заявка успешно обновлена"},
    400: {"description": "Неверные параметры запроса"},
    403: {
        "description": "Доступ запрещен. Пользователь не является юристом, или заявка не назначена этому юристу."
    },
    404: {"description": "Заявка не найдена"},
}

get_document_response = {
    401: {"description": "Неверные учетные данные"},
    200: {"description": "Документ в виде файла для скачивания"},
    400: {"description": "Неверные параметры запроса"},
    403: {
        "description": "Доступ запрещен. Недостаточно прав для доступа к этому документу."
    },
    404: {"description": "Документ не найден"},
}

create_lawyer_request_response = {
    401: {"description": "Неверные учетные данные"},
    201: {
        "description": "Заявка успешно создана",
        "model": LawyerRequestCreateResponseDTO,
    },
    400: {"description": "Неверные параметры запроса"},
    500: {"description": "Внутренняя ошибка сервера"},
}
