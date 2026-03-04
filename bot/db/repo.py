from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Download, Favorite, User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, tg_user_id: int, default_language: str = "en") -> User:
        query = select(User).where(User.tg_user_id == tg_user_id)
        user = await self.session.scalar(query)
        if user:
            return user

        user = User(tg_user_id=tg_user_id, language=default_language)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def set_language(self, tg_user_id: int, language: str) -> None:
        user = await self.get_or_create(tg_user_id=tg_user_id)
        user.language = language
        await self.session.commit()

    async def get_language(self, tg_user_id: int, default_language: str = "en") -> str:
        user = await self.get_or_create(tg_user_id=tg_user_id, default_language=default_language)
        return user.language

    async def get_stats(self) -> dict[str, int]:
        users_count = await self.session.scalar(select(func.count()).select_from(User)) or 0
        downloads_count = await self.session.scalar(select(func.count()).select_from(Download)) or 0
        favorites_count = await self.session.scalar(select(func.count()).select_from(Favorite)) or 0
        return {
            "users": int(users_count),
            "downloads": int(downloads_count),
            "favorites": int(favorites_count),
        }


class DownloadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_download(
        self,
        tg_user_id: int,
        platform: str,
        url: str,
        title: str,
        selected_format: str,
        duration_sec: int | None,
    ) -> Download:
        user_repo = UserRepository(self.session)
        user = await user_repo.get_or_create(tg_user_id=tg_user_id)
        download = Download(
            user_id=user.id,
            platform=platform,
            url=url,
            title=title,
            selected_format=selected_format,
            duration_sec=duration_sec,
        )
        self.session.add(download)
        await self.session.commit()
        await self.session.refresh(download)
        return download

    async def list_recent(self, tg_user_id: int, limit: int = 10) -> list[Download]:
        user = await self.session.scalar(select(User).where(User.tg_user_id == tg_user_id))
        if not user:
            return []
        query = (
            select(Download)
            .where(Download.user_id == user.id)
            .order_by(Download.created_at.desc())
            .limit(limit)
        )
        rows = await self.session.scalars(query)
        return list(rows)


class FavoriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_favorite(self, tg_user_id: int, platform: str, url: str, title: str) -> Favorite:
        user_repo = UserRepository(self.session)
        user = await user_repo.get_or_create(tg_user_id=tg_user_id)

        exists_query = select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.url == url,
        )
        exists = await self.session.scalar(exists_query)
        if exists:
            return exists

        item = Favorite(user_id=user.id, platform=platform, url=url, title=title)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def list_recent(self, tg_user_id: int, limit: int = 10) -> list[Favorite]:
        user = await self.session.scalar(select(User).where(User.tg_user_id == tg_user_id))
        if not user:
            return []

        query = (
            select(Favorite)
            .where(Favorite.user_id == user.id)
            .order_by(Favorite.created_at.desc())
            .limit(limit)
        )
        rows = await self.session.scalars(query)
        return list(rows)

