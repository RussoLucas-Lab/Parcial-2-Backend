from datetime import datetime, timezone

from sqlmodel import Session, select

from app.modules.Auth.model import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, usuario_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(
            usuario_id=usuario_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        self.session.flush()
        self.session.refresh(token)
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).first()

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        self.session.add(token)
        self.session.flush()

    def delete_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired = self.session.exec(
            select(RefreshToken).where(RefreshToken.expires_at < now)
        ).all()
        for token in expired:
            self.session.delete(token)
        self.session.flush()
