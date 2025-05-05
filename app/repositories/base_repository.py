from lawly_db.db_models.db_session import Base
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: Base, session: AsyncSession):
        session.add(entity)
        await session.commit()
