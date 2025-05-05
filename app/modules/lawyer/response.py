from modules.lawyer.dto import MessageResponseDTO, MessagesResponseDTO

get_lawyer_messages_response = {
    200: {"description": "История сообщений", "model": MessagesResponseDTO},
    401: {"description": "Не авторизован"}
}

create_lawyer_request_response = {
    201: {"description": "Обращение успешно создано", "model": MessageResponseDTO},
    401: {"description": "Не авторизован"},
    403: {"description": "Доступ запрещен (нет подписки или исчерпан лимит консультаций)"}
}
