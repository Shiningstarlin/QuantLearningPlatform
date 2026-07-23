from datetime import datetime, timezone
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import InvitationCode


class InvitationService:
    CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    def __init__(self, db: Session):
        self.db = db

    def generate_codes(self, count: int) -> list[InvitationCode]:
        if count <= 0:
            return []

        codes: list[InvitationCode] = []
        while len(codes) < count:
            code_value = self.generate_code_value()
            if self.db.scalar(select(InvitationCode).where(InvitationCode.code == code_value)):
                continue
            invitation = InvitationCode(code=code_value)
            self.db.add(invitation)
            codes.append(invitation)
        self.db.commit()
        return codes

    def consume_code(self, raw_code: str, user_id: int) -> None:
        code_value = self.normalize(raw_code)
        invitation = self.db.scalar(select(InvitationCode).where(InvitationCode.code == code_value))
        if invitation is None or invitation.used_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码无效或已被使用")

        invitation.used_at = datetime.now(timezone.utc)
        invitation.used_by_user_id = user_id

    @classmethod
    def generate_code_value(cls) -> str:
        first = "".join(secrets.choice(cls.CODE_ALPHABET) for _ in range(4))
        second = "".join(secrets.choice(cls.CODE_ALPHABET) for _ in range(4))
        third = "".join(secrets.choice(cls.CODE_ALPHABET) for _ in range(4))
        return f"QLS-{first}-{second}-{third}"

    @staticmethod
    def normalize(raw_code: str) -> str:
        return raw_code.strip().upper()
