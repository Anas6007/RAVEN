from sqlalchemy import func, select

from database.models.participant import Participant
from repositories.base_repository import BaseRepository


class ParticipantRepository(BaseRepository):

    async def create(self, **kwargs):
        participant = Participant(**kwargs)
        return await self.add(participant)

    async def get_by_user(self, giveaway_id: int, user_id: int):
        result = await self.session.execute(
            select(Participant).where(
                Participant.giveaway_id == giveaway_id,
                Participant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, participant_id: int):
        result = await self.session.execute(
            select(Participant).where(Participant.id == participant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, giveaway_id: int):
        result = await self.session.execute(
            select(Participant).where(Participant.giveaway_id == giveaway_id)
        )
        return result.scalars().all()

    async def count(self, giveaway_id: int):
        result = await self.session.execute(
            select(func.count()).select_from(Participant).where(
                Participant.giveaway_id == giveaway_id
            )
        )
        return result.scalar_one()

    async def get_top_by_votes(self, giveaway_id: int, limit: int = 1):
        result = await self.session.execute(
            select(Participant)
            .where(Participant.giveaway_id == giveaway_id)
            .order_by(Participant.votes_count.desc(), Participant.joined_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_votes_count(self, participant, count: int):
        participant.votes_count = count
        await self.save()
        await self.refresh(participant)
        return participant

    async def delete(self, participant):
        await super().delete(participant)

    async def get_available(self, giveaway_id: int):
        result = await self.session.execute(
            select(Participant).where(
                Participant.giveaway_id == giveaway_id,
                Participant.is_winner.is_(False),
            )
        )
        return result.scalars().all()

    async def mark_winner(self, participant):
        participant.is_winner = True
        await self.save()
        await self.refresh(participant)
        return participant
