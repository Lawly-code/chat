import io

from fastapi import APIRouter, Depends, HTTPException, Body, Query, Response, status
from datetime import datetime

from starlette.responses import StreamingResponse

from api.auth.auth_bearer import JWTBearer, JWTHeader
from lawly_db.db_models.enum_models import LawyerRequestStatusEnum
from services.errors import (
    AccessDeniedError,
    NotFoundError,
    ParameterError,
)

from services.lawyer_service import LawyerService

from modules.lawyer.descriptions import (
    get_lawyer_requests_description,
    update_lawyer_request_description,
    get_document_description,
    create_lawyer_request_description,
    get_lawyer_responses_description,
)

from modules.lawyer.dto import (
    LawyerRequestStatus,
    LawyerRequestDTO,
    LawyerRequestsDTO,
    LawyerRequestUpdateDTO,
    LawyerRequestCreateDTO,
    LawyerRequestCreateResponseDTO,
    LawyerResponsesDTO,
)
from modules.lawyer.response import (
    get_lawyer_requests_response,
    update_lawyer_request_response,
    get_document_response,
    create_lawyer_request_response,
    get_lawyer_responses_response,
)

router = APIRouter(tags=["Юрист"])


@router.post(
    "/requests",
    summary="Создание заявки к юристу",
    description=create_lawyer_request_description,
    responses=create_lawyer_request_response,
    response_model=LawyerRequestCreateResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_lawyer_request(
    request_data: LawyerRequestCreateDTO = Body(...),
    current_user: JWTHeader = Depends(JWTBearer()),
    lawyer_service: LawyerService = Depends(),
):
    """
    Создание заявки к юристу от пользователя
    """
    try:
        lawyer_request = await lawyer_service.create_lawyer_request_from_user(
            user_id=current_user.user_id,
            description=request_data.description,
            document_bytes=request_data.document_bytes,
        )

        return LawyerRequestCreateResponseDTO(
            id=lawyer_request.id,
            status=LawyerRequestStatus(lawyer_request.status.value),
            created_at=lawyer_request.created_at,
        )
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/requests",
    summary="Получение заявок юристом",
    description=get_lawyer_requests_description,
    responses=get_lawyer_requests_response,
    response_model=LawyerRequestsDTO,
)
async def get_lawyer_requests(
    status: LawyerRequestStatus = Query(
        ..., description="Статус заявок для фильтрации"
    ),
    current_user: JWTHeader = Depends(JWTBearer()),
    lawyer_service: LawyerService = Depends(),
):
    """
    Получение заявок юриста с фильтрацией по статусу
    """
    if status == LawyerRequestStatus.COMPLETED:
        return LawyerRequestsDTO(requests=[], total=0)

    try:
        is_lawyer = await lawyer_service.check_is_lawyer(current_user.user_id)
        if not is_lawyer:
            raise HTTPException(
                status_code=403, detail="Access denied. User is not a lawyer."
            )

        requests, total = await lawyer_service.get_lawyer_requests_by_status(
            user_id=current_user.user_id, status=LawyerRequestStatusEnum(status.value)
        )

        response_requests = []
        for request in requests:
            response_requests.append(
                LawyerRequestDTO(
                    id=request.id,
                    title=f"Заявка #{request.id}",
                    description=request.note
                    or f"Проверка документов для заявки #{request.id}",
                    status=LawyerRequestStatus(request.status.value),
                    file_url=request.document_url,
                    created_at=request.created_at,
                    updated_at=request.updated_at,
                )
            )

        return LawyerRequestsDTO(requests=response_requests, total=total)

    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/requests/update",
    summary="Обновление заявки юриста",
    description=update_lawyer_request_description,
    responses=update_lawyer_request_response,
    response_class=Response,
)
async def update_lawyer_request(
    request_data: LawyerRequestUpdateDTO = Body(...),
    current_user: JWTHeader = Depends(JWTBearer()),
    lawyer_service: LawyerService = Depends(),
):
    """
    Обновление заявки юриста
    """
    status = LawyerRequestStatusEnum(request_data.status.value)

    if status == LawyerRequestStatusEnum.COMPLETED:
        if not request_data.document_bytes:
            raise HTTPException(
                status_code=400,
                detail="Document is required when status is 'completed'",
            )
        if not request_data.description:
            raise HTTPException(
                status_code=400,
                detail="Description is required when status is 'completed'",
            )

    try:
        await lawyer_service.update_lawyer_request(
            user_id=current_user.user_id,
            request_id=request_data.request_id,
            status=status,
            document_bytes=request_data.document_bytes,
            description=request_data.description,
        )

        return Response(status_code=202)

    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/document",
    summary="Получение документа",
    response_class=StreamingResponse,
    description=get_document_description,
    responses=get_document_response,
)
async def get_document(
    lawyer_request_id: int | None = Query(None, description="ID заявки юриста"),
    message_id: int | None = Query(None, description="ID сообщения"),
    current_user: JWTHeader = Depends(JWTBearer()),
    lawyer_service: LawyerService = Depends(),
):
    """
    Получение документа по ID заявки юриста или ID сообщения
    """
    try:
        document_bytes = await lawyer_service.get_document(
            user_id=current_user.user_id,
            lawyer_request_id=lawyer_request_id,
            message_id=message_id,
        )

        return StreamingResponse(
            content=io.BytesIO(document_bytes),
            media_type="application/msword",
            headers={
                "Content-Disposition": f"attachment; filename=document_{datetime.now().strftime('%Y%m%d%H%M%S')}.doc"
            },
        )

    except ParameterError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/messages",
    summary="Получение ответов юриста",
    description=get_lawyer_responses_description,
    responses=get_lawyer_responses_response,
    response_model=LawyerResponsesDTO,
)
async def get_lawyer_messages(
    start_date: datetime = Query(..., description="Дата начала периода"),
    end_date: datetime = Query(..., description="Дата окончания периода"),
    current_user: JWTHeader = Depends(JWTBearer()),
    lawyer_service: LawyerService = Depends(),
):
    """
    Получение всех ответов юриста за указанный период времени
    """
    try:
        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be earlier than end date",
            )

        responses = await lawyer_service.get_lawyer_responses(
            user_id=current_user.user_id,
            from_date=start_date,
            to_date=end_date,
        )

        return responses
    except AccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
