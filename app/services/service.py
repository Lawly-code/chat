from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from lawly_db.db_models.lawyer_request import LawyerRequest
from lawly_db.db_models.enum_models import LawyerRequestStatusEnum
from lawly_db.db_models.lawyer import Lawyer
from lawly_db.db_models.message import Message

from services.gost_cipher_service import GostCipherService
from services.s3_service import S3Service


class LawyerService:
    def __init__(self):
        self.gost_cipher = GostCipherService()
        self.s3_service = S3Service()
        
    async def check_is_lawyer(self, session: AsyncSession, user_id: int) -> bool:
        """
        Check if the user is a lawyer
        
        Args:
            session: Database session
            user_id: User ID to check
            
        Returns:
            True if the user is a lawyer, False otherwise
        """
        query = select(Lawyer).where(Lawyer.user_id == user_id)
        result = await session.execute(query)
        lawyer = result.scalar_one_or_none()
        
        return lawyer is not None
        
    async def get_lawyer_requests_by_status(
        self, 
        session: AsyncSession,
        user_id: int,
        status: LawyerRequestStatusEnum
    ) -> List[LawyerRequest]:
        """
        Get lawyer requests by status
        
        Args:
            session: Database session
            user_id: ID of the current user (lawyer)
            status: Status filter
            
        Returns:
            List of LawyerRequest objects
        """
        # First check if user is a lawyer
        is_lawyer = await self.check_is_lawyer(session, user_id)
        if not is_lawyer:
            raise HTTPException(status_code=403, detail="Access denied. User is not a lawyer.")
        
        # Get the lawyer's ID
        query = select(Lawyer).where(Lawyer.user_id == user_id)
        result = await session.execute(query)
        lawyer = result.scalar_one()
        
        # Get requests with the specified status assigned to this lawyer
        query = select(LawyerRequest).where(
            LawyerRequest.lawyer_id == lawyer.id,
            LawyerRequest.status == status
        )
        
        result = await session.execute(query)
        requests = result.scalars().all()
        
        return requests
        
    async def update_lawyer_request(
        self,
        session: AsyncSession,
        user_id: int,
        request_id: int,
        status: LawyerRequestStatusEnum,
        document_bytes: Optional[bytes] = None,
        description: Optional[str] = None
    ) -> LawyerRequest:
        """
        Update a lawyer request
        
        Args:
            session: Database session
            user_id: ID of the current user (lawyer)
            request_id: ID of the request to update
            status: New status
            document_bytes: Optional document bytes
            description: Optional description
            
        Returns:
            Updated LawyerRequest object
        """
        # First check if user is a lawyer
        is_lawyer = await self.check_is_lawyer(session, user_id)
        if not is_lawyer:
            raise HTTPException(status_code=403, detail="Access denied. User is not a lawyer.")
        
        # Get the request
        query = select(LawyerRequest).where(LawyerRequest.id == request_id)
        result = await session.execute(query)
        request = result.scalar_one_or_none()
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Get the lawyer's ID
        query = select(Lawyer).where(Lawyer.user_id == user_id)
        result = await session.execute(query)
        lawyer = result.scalar_one()
        
        # Check if the request belongs to this lawyer
        if request.lawyer_id != lawyer.id:
            raise HTTPException(status_code=403, detail="Access denied. This request is not assigned to you.")
        
        # Update the request
        request.status = status
        
        # If status is completed, document and description are required
        if status == LawyerRequestStatusEnum.COMPLETED:
            if document_bytes:
                # Encrypt the document
                key = await self.get_encryption_key()
                encrypted_bytes = await self.gost_cipher.async_encrypt_data(document_bytes, key)
                
                # Upload to S3
                file_url = await self.s3_service.upload_file(encrypted_bytes)
                
                # Save the URL to the request
                request.document_url = file_url
            
            if description:
                request.note = description
        
        await session.commit()
        await session.refresh(request)
        
        return request
    
    async def get_document(
        self,
        session: AsyncSession,
        user_id: int,
        lawyer_request_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> bytes:
        """
        Get a document by either lawyer_request_id or message_id
        
        Args:
            session: Database session
            user_id: ID of the current user
            lawyer_request_id: Optional ID of the lawyer request
            message_id: Optional ID of the message
            
        Returns:
            Document bytes
        """
        if lawyer_request_id:
            # Get document by lawyer request ID
            query = select(LawyerRequest).where(LawyerRequest.id == lawyer_request_id)
            result = await session.execute(query)
            request = result.scalar_one_or_none()
            
            if not request:
                raise HTTPException(status_code=404, detail="Request not found")
            
            # Check if user is a lawyer
            is_lawyer = await self.check_is_lawyer(session, user_id)
            if not is_lawyer:
                raise HTTPException(status_code=403, detail="Access denied. User is not a lawyer.")
            
            # Get the lawyer's ID
            query = select(Lawyer).where(Lawyer.user_id == user_id)
            result = await session.execute(query)
            lawyer = result.scalar_one()
            
            # Check if the request belongs to this lawyer
            if request.lawyer_id != lawyer.id:
                raise HTTPException(status_code=403, detail="Access denied. This request is not assigned to you.")
            
            document_url = request.document_url
            
        elif message_id:
            # Get document by message ID
            query = select(Message).where(Message.id == message_id)
            result = await session.execute(query)
            message = result.scalar_one_or_none()
            
            if not message:
                raise HTTPException(status_code=404, detail="Message not found")
            
            # Check if the message belongs to this user
            if message.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied. This message does not belong to you.")
            
            document_url = message.document_url
            
        else:
            raise HTTPException(status_code=400, detail="Either lawyer_request_id or message_id must be provided")
        
        if not document_url:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Download the document from S3
        encrypted_bytes = await self.s3_service.download_file(document_url)
        
        # Decrypt the document
        key = await self.get_encryption_key()
        document_bytes = await self.gost_cipher.async_decrypt_data(encrypted_bytes, key)
        
        return document_bytes
    
    async def get_encryption_key(self) -> bytes:
        """
        Get the encryption key from environment variables or other secure source
        
        Returns:
            Encryption key as bytes
        """
        # This would typically come from environment variables or a secure key management service
        # For now, we'll use a placeholder key (32 bytes for GOST)
        from config import settings
        return settings.encryption_settings.key.encode()
