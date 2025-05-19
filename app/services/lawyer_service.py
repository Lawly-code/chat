from fastapi import Depends
from lawly_db.db_models import LawyerRequest, Lawyer
from lawly_db.db_models.db_session import get_session
from lawly_db.db_models.enum_models import LawyerRequestStatusEnum
from protos.notification_service.client import NotificationServiceClient
from protos.notification_service.dto import PushRequestDTO

from protos.user_service.client import UserServiceClient

from sqlalchemy.ext.asyncio import AsyncSession

from services.gost_cipher_service import GostCipherService
from services.s3_service import S3Service
from services.errors import AccessDeniedError, NotFoundError, ParameterError
from config import settings
from repositories.lawyer_request_repository import LawyerRequestRepository
from repositories.message_repository import MessageRepository
from repositories.lawyer_repository import LawyerRepository
from utils.notfication import notification


class LawyerService:
    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session
        self.lawyer_request_repo = LawyerRequestRepository(session)
        self.message_repo = MessageRepository(session)
        self.lawyer_repo = LawyerRepository(session)
        self.gost_cipher = GostCipherService()
        self.s3_service = S3Service()

    async def create_lawyer_request_from_user(
        self, user_id: int, description: str, document_bytes: list[int] | None = None
    ) -> LawyerRequest:
        """
        Создание заявки к юристу от пользователя

        :param user_id: ID пользователя
        :param description: Описание заявки
        :param document_bytes: Опциональные байты документа
        :return: Созданный объект LawyerRequest
        :raises ServiceError: В случае ошибки при загрузке документа
        """
        document_url = None
        user_service_client = UserServiceClient(
            host=settings.user_service.host, port=settings.user_service.port
        )
        sub_info = await user_service_client.get_user_info(user_id)
        if sub_info.consultations_used + 1 > sub_info.consultations_total:
            raise AccessDeniedError("У вас закончились консультации")
        write_off_consultation = await user_service_client.write_off_consultation(
            user_id=user_id
        )
        if not write_off_consultation:
            raise AccessDeniedError("Не удалось списать консультацию")

        # Если есть документ, шифруем и загружаем его в S3
        if document_bytes:
            key = await self.get_encryption_key()
            document_bytes_obj = bytes(document_bytes)
            encrypted_bytes = await self.gost_cipher.async_encrypt_data(
                document_bytes_obj, key
            )

            document_url = await self.s3_service.upload_file(encrypted_bytes)

        # Создаем заявку к юристу
        lawyer_request = await self.lawyer_request_repo.create_lawyer_request(
            user_id=user_id, message=description, document_url=document_url
        )

        return lawyer_request

    async def check_is_lawyer(self, user_id: int) -> bool:
        """
        Проверка, является ли пользователь юристом

        :param user_id: ID пользователя для проверки
        :return: True если пользователь юрист, False в противном случае
        """
        return await self.lawyer_repo.check_is_lawyer(user_id)

    async def get_lawyer_by_user_id(self, user_id: int) -> Lawyer:
        """
        Получение объекта юриста по ID пользователя

        :param user_id: ID пользователя
        :return: Объект юриста
        :raises AccessDeniedError: Если пользователь не является юристом
        """
        lawyer = await self.lawyer_repo.get_lawyer_by_user_id(user_id)
        if not lawyer:
            raise AccessDeniedError("Пользователь не является юристом")
        return lawyer

    async def get_lawyer_requests_by_status(
        self, user_id: int, status: LawyerRequestStatusEnum
    ) -> tuple[list[LawyerRequest], int]:
        """
        Получение заявок юриста по статусу

        :param user_id: ID текущего пользователя (юриста)
        :param status: Фильтр по статусу
        :return: Кортеж из списка объектов LawyerRequest и общего количества
        :raises AccessDeniedError: Если пользователь не является юристом
        """
        lawyer = await self.get_lawyer_by_user_id(user_id)

        return await self.lawyer_request_repo.get_lawyer_requests_by_status(
            lawyer_id=lawyer.id, status=status
        )

    async def update_lawyer_request(
        self,
        user_id: int,
        request_id: int,
        status: LawyerRequestStatusEnum,
        document_bytes: list[int] | None = None,
        description: str | None = None,
    ) -> LawyerRequest:
        """
        Обновление заявки юриста

        :param user_id: ID текущего пользователя (юриста)
        :param request_id: ID заявки для обновления
        :param status: Новый статус
        :param document_bytes: Опциональные байты документа
        :param description: Опциональное описание
        :return: Обновленный объект LawyerRequest
        :raises AccessDeniedError: Если пользователь не является юристом или заявка не назначена этому юристу
        :raises NotFoundError: Если заявка не найдена
        """
        lawyer = await self.get_lawyer_by_user_id(user_id)

        request = await self.lawyer_request_repo.get_lawyer_request_by_id(request_id)
        if not request:
            raise NotFoundError(f"Заявка с ID {request_id} не найдена")

        if (
            request.lawyer_id != lawyer.id
            and status == LawyerRequestStatusEnum.COMPLETED
        ):
            raise AccessDeniedError("Заявка не назначена этому юристу")

        if status == LawyerRequestStatusEnum.COMPLETED and document_bytes:
            key = await self.get_encryption_key()
            document_bytes_obj = bytes(document_bytes)
            encrypted_bytes = await self.gost_cipher.async_encrypt_data(
                document_bytes_obj, key
            )

            document_url = await self.s3_service.upload_file(encrypted_bytes)
            await self.message_repo.create_user_lawyer_message(
                user_id=request.user_id, content=description, document_url=document_url
            )
            client = NotificationServiceClient(
                host="notification_grpc_service", port=50051
            )
            context = {"lawyer_request_id": request.id, "note": description or ""}
            message = notification("lawyer_checked", context=context)
            await client.send_push_from_users(
                request_data=PushRequestDTO(user_ids=[request.user_id], message=message)
            )

        return await self.lawyer_request_repo.update_lawyer_request_status(
            request_id=request_id, status=status, lawyer_id=lawyer.id, note=description
        )

    async def get_document(
        self,
        user_id: int,
        lawyer_request_id: int | None = None,
        message_id: int | None = None,
    ) -> bytes:
        """
        Получение документа по ID заявки юриста или ID сообщения

        :param user_id: ID текущего пользователя
        :param lawyer_request_id: Опциональный ID заявки юриста
        :param message_id: Опциональный ID сообщения
        :return: Байты документа
        :raises ParameterError: Если не указан ни lawyer_request_id, ни message_id
        :raises NotFoundError: Если заявка, сообщение или документ не найдены
        :raises AccessDeniedError: Если пользователь не имеет доступа к документу
        """
        if not lawyer_request_id and not message_id:
            raise ParameterError(
                "Необходимо указать либо lawyer_request_id, либо message_id"
            )

        document_url = None

        if lawyer_request_id:
            request = await self.lawyer_request_repo.get_lawyer_request_by_id(
                lawyer_request_id
            )
            if not request:
                raise NotFoundError(f"Заявка с ID {lawyer_request_id} не найдена")

            lawyer = await self.get_lawyer_by_user_id(user_id)

            if (
                request.lawyer_id != lawyer.id
                and request.status == LawyerRequestStatusEnum.PROCESSING
            ):
                raise AccessDeniedError("Нет доступа к этой заявке")

            document_url = request.document_url

        elif message_id:
            message = await self.message_repo.get_message_by_id(message_id)
            if not message:
                raise NotFoundError(f"Сообщение с ID {message_id} не найдено")

            if message.user_id != user_id:
                raise AccessDeniedError("Нет доступа к этому сообщению")

            document_url = message.document_url

        if not document_url:
            raise NotFoundError("Документ не найден")

        encrypted_bytes = await self.s3_service.download_file(document_url)

        key = await self.get_encryption_key()
        document_bytes = await self.gost_cipher.async_decrypt_data(encrypted_bytes, key)

        return document_bytes

    async def get_encryption_key(self) -> bytes:
        """
        Получение ключа шифрования из настроек

        :return: Ключ шифрования в виде байтов
        """
        return settings.encryption_settings.key.encode()
