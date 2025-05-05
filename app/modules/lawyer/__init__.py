from .descriptions import create_lawyer_request_description, get_lawyer_messages_description
from .dto import LawyerRequestDTO, MessageResponseDTO, MessagesResponseDTO
from .response import create_lawyer_request_response, get_lawyer_messages_response
from .route import router

__all__ = [
    "router",
    "get_lawyer_messages_description",
    "create_lawyer_request_description",
    "LawyerRequestDTO",
    "MessageResponseDTO",
    "MessagesResponseDTO",
    "get_lawyer_messages_response",
    "create_lawyer_request_response"
]
