from typing import Any

from config import NOTIFICATIONS


def render_template(data: Any, context: dict) -> Any:
    """
    Рекурсивная функция, которая проходит по словарю и заменяет все {{ключи}} значениями из context
    """
    if isinstance(data, dict):
        return {k: render_template(v, context) for k, v in data.items()}
    elif isinstance(data, list):
        return [render_template(item, context) for item in data]
    elif isinstance(data, str):
        for key, value in context.items():
            data = data.replace(f"{{{{{key}}}}}", str(value))
        return data
    else:
        return data


def notification(section: str, context: dict = None):
    base = NOTIFICATIONS[section]
    if context:
        return render_template(base, context)
    return base
