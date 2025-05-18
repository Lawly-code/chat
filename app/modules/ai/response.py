from modules.ai.dto import MessagesResponseDTO

get_ai_messages_response = {
    401: {"description": "Неверные учетные данные"},
    200: {"description": "История сообщений", "model": MessagesResponseDTO},
    409: {"description": "Нет активной подписки с такими функциями"},
    403: {"description": "Доступ запрещен"},
}

send_ai_message_response = {
    401: {"description": "Неверные учетные данные"},
    202: {"description": "Сообщение успешно отправлено"},
    400: {"description": "Что-то пошло не так при добавлении в очередь"},
    409: {"description": "Нет активной подписки с такими функциями"},
    403: {"description": "Доступ запрещен"},
}
