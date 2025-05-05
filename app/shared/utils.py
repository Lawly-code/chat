from fastapi import Request


async def ip_address_getter(request: Request) -> str:
    """
    Получение IP-адреса клиента из запроса
    
    :param request: Запрос
    :return: IP-адрес
    """
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"]
    elif request.client:
        return request.client.host
    return "127.0.0.1"
