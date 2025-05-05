from modules.ai.dto import MessageResponseDTO, MessagesResponseDTO

get_ai_messages_response = {
    200: {"description": "История сообщений", "model": MessagesResponseDTO},
    409: {"description": "Нет активной подписки с такими функциями"},
    403: {"description": "Доступ запрещен"}
}

send_ai_message_response = {
    202: {"description": "Сообщение успешно отправлено"},
    400: {"description": "Что-то пошло не так при добавлении в очередь"},
    409: {"description": "Нет активной подписки с такими функциями"},
    403: {"description": "Доступ запрещен"}
}
