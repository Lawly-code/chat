import uuid
import logging
import aioboto3
from botocore.exceptions import ClientError
from botocore.config import Config

from config import settings
from services.errors import NotFoundError, ServiceError


class S3Service:
    def __init__(self):
        # Создаем конфигурацию без прокси и с отключенной верификацией SSL
        self.boto_config = Config(
            retries={'max_attempts': 3, 'mode': 'standard'},
            connect_timeout=20,
            read_timeout=60
        )
        
        self.session = aioboto3.Session(
            aws_access_key_id=settings.s3_settings.access_key,
            aws_secret_access_key=settings.s3_settings.secret_key
        )
        self.bucket_name = settings.s3_settings.bucket_name
        self.endpoint_url = settings.s3_settings.endpoint_url
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Настройка логгера"""
        logger = logging.getLogger("S3Service")
        return logger
        
    def _get_client_config(self):
        """Создает базовую конфигурацию для boto3 клиентов"""
        return {
            'endpoint_url': self.endpoint_url,
            'config': self.boto_config,
            'verify': False
        }
        
    async def get_file_url(self, object_key: str) -> str:
        """
        Получает URL для доступа к объекту в S3
        
        :param object_key: Ключ (путь) объекта в S3
        :return: URL для доступа к объекту
        """
        try:
            client_params = self._get_client_config()
            async with self.session.client('s3', **client_params) as s3:
                presigned_url = await s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_key},
                    ExpiresIn=604800  # URL будет действителен 7 дней
                )
                self.logger.info(f"Сгенерирован presigned URL для {object_key}")
                return presigned_url
        except Exception as e:
            self.logger.warning(f"Ошибка при создании presigned URL: {e}, возвращаем стандартный URL")
            # Если presigned URL не работает, вернем path-style URL как наиболее совместимый
            return f"{self.endpoint_url}/{self.bucket_name}/{object_key}"

    async def upload_file(self, file_bytes: bytes, file_name: str | None = None, 
                          content_type: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document") -> str:
        """
        Загрузка файла на S3 хранилище
        
        :param file_bytes: Байты файла для загрузки
        :param file_name: Опциональное имя файла, если не предоставлено, будет сгенерирован UUID
        :param content_type: Тип содержимого файла
        :return: URL загруженного файла
        :raises ServiceError: В случае ошибки загрузки файла
        """
        if not file_name:
            file_extension = "doc"  # Default extension for lawyer documents
            file_name = f"{uuid.uuid4()}.{file_extension}"
        
        try:
            client_params = self._get_client_config()
            async with self.session.client('s3', **client_params) as s3:
                self.logger.info(f"Начинаем загрузку файла {file_name}")
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=file_bytes,
                    ContentType=content_type
                )
                self.logger.info(f"Файл {file_name} успешно загружен")
                
            # Получаем URL файла
            file_url = await self.get_file_url(file_name)
            return file_url
        
        except ClientError as e:
            self.logger.error(f"Ошибка при загрузке файла {file_name}: {e}")
            raise ServiceError(f"Ошибка при загрузке файла в S3: {str(e)}")
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при загрузке файла {file_name}: {e}")
            raise ServiceError(f"Неожиданная ошибка при загрузке файла в S3: {str(e)}")
            
    async def download_file(self, file_url: str) -> bytes:
        """
        Скачивание файла из S3 хранилища
        
        :param file_url: URL файла в S3
        :return: Байты файла
        :raises ServiceError: В случае ошибки скачивания файла
        :raises NotFoundError: Если файл не найден
        """
        try:
            # Извлекаем ключ файла из URL
            if self.endpoint_url in file_url:
                # Для presigned URL или path-style URL
                file_key = file_url.split(f"{self.bucket_name}/")[1]
                # Убираем параметры запроса, если они есть
                if '?' in file_key:
                    file_key = file_key.split('?')[0]
            else:
                # Для virtual-hosted style URL
                file_key = file_url.split(f"{self.bucket_name}.s3.amazonaws.com/")[1]
            
            self.logger.info(f"Скачивание файла с ключом: {file_key}")
            
            client_params = self._get_client_config()
            async with self.session.client('s3', **client_params) as s3:
                response = await s3.get_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                
                async with response['Body'] as stream:
                    data = await stream.read()
                    self.logger.info(f"Файл {file_key} успешно скачан, размер: {len(data)} байт")
                    return data
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            self.logger.error(f"Ошибка при скачивании файла: {e}")
            
            if error_code == '404':
                raise NotFoundError(f"Файл не найден в S3: {file_url}")
            else:
                raise ServiceError(f"Ошибка при скачивании файла из S3: {str(e)}")
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при скачивании файла: {e}")
            raise ServiceError(f"Неожиданная ошибка при скачивании файла из S3: {str(e)}")
            
    async def check_bucket_exists(self) -> bool:
        """
        Проверяет существование бакета
        
        :return: True если бакет существует, иначе False
        """
        try:
            client_params = self._get_client_config()
            async with self.session.client('s3', **client_params) as s3:
                self.logger.info(f"Проверяем существование бакета {self.bucket_name}")
                await s3.head_bucket(Bucket=self.bucket_name)
                self.logger.info(f"Бакет {self.bucket_name} существует")
                return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                self.logger.error(f"Бакет {self.bucket_name} не существует")
            elif error_code == '403':
                self.logger.error(f"Нет доступа к бакету {self.bucket_name}")
            else:
                self.logger.error(f"Ошибка при проверке бакета: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при проверке бакета: {e}")
            return False
