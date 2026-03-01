"""Local pairing policy storage for Telegram DM approvals."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from src.core.config import settings


PAIRING_ALPHABET = """ABCDEFGHJKLMNPQRSTUVWXYZ23456789"""
PAIRING_CODE_LENGTH = 8


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PendingRequest:
    code: str
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    requested_at: datetime
    message_preview: Optional[str]

    def to_dict(self) -> Dict[str, str | int | None]:
        data = asdict(self)
        data["requested_at"] = self.requested_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "PendingRequest":
        return cls(
            code=str(payload["code"]),
            user_id=int(payload["user_id"]),
            username=payload.get("username") if payload.get("username") else None,
            first_name=payload.get("first_name") if payload.get("first_name") else None,
            last_name=payload.get("last_name") if payload.get("last_name") else None,
            requested_at=datetime.fromisoformat(str(payload["requested_at"])),
            message_preview=payload.get("message_preview")
            if payload.get("message_preview")
            else None,
        )


@dataclass
class ApprovedUser:
    user_id: int
    approved_at: datetime

    def to_dict(self) -> Dict[str, str | int]:
        return {
            "user_id": self.user_id,
            "approved_at": self.approved_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "ApprovedUser":
        return cls(
            user_id=int(payload["user_id"]),
            approved_at=datetime.fromisoformat(str(payload["approved_at"])),
        )


class PairingLimitReached(Exception):
    """Raised when pending queue has reached the configured limit."""


class PairingCodeNotFound(Exception):
    """Raised when attempting to approve/reject an unknown code."""


class PairingStore:
    """Local JSON-backed pairing queue + allowlist manager."""

    def __init__(
        self,
        *,
        storage_dir: Optional[str] = None,
        code_ttl_seconds: Optional[int] = None,
        pending_limit: Optional[int] = None,
        clock_fn: Callable[[], datetime] = _now,
    ) -> None:
        self._storage_dir = Path(storage_dir or settings.telegram_pairing_storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._pending_path = self._storage_dir / "pending.json"
        self._allowlist_path = self._storage_dir / "allowlist.json"
        self._ttl = code_ttl_seconds or settings.telegram_pairing_code_ttl_seconds
        self._limit = pending_limit or settings.telegram_pairing_pending_limit
        self._clock = clock_fn

    # ----- Public API -------------------------------------------------
    def register_request(
        self,
        *,
        user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        message_preview: Optional[str],
    ) -> Tuple[PendingRequest, bool]:
        pending = self._load_pending()
        pending = self._purge_expired(pending)

        existing = next((req for req in pending if req.user_id == user_id), None)
        if existing:
            return existing, False

        if len(pending) >= self._limit:
            raise PairingLimitReached(
                "Pairing queue is full; wait for an existing request to expire or be approved."
            )

        code = self._generate_code({req.code for req in pending})
        preview = self._trim_preview(message_preview)
        new_request = PendingRequest(
            code=code,
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            requested_at=self._clock(),
            message_preview=preview,
        )
        pending.append(new_request)
        self._write_pending(pending)
        return new_request, True

    def approve(self, code: str) -> PendingRequest:
        pending = self._load_pending()
        remaining: List[PendingRequest] = []
        approved: Optional[PendingRequest] = None

        for req in pending:
            if req.code.lower() == code.lower():
                approved = req
            else:
                remaining.append(req)

        if not approved:
            raise PairingCodeNotFound(f"No pending request matches code {code}")

        self._write_pending(remaining)
        self._add_allowlist_entry(approved.user_id)
        return approved

    def reject(self, code: str) -> PendingRequest:
        pending = self._load_pending()
        remaining: List[PendingRequest] = []
        rejected: Optional[PendingRequest] = None

        for req in pending:
            if req.code.lower() == code.lower():
                rejected = req
            else:
                remaining.append(req)

        if not rejected:
            raise PairingCodeNotFound(f"No pending request matches code {code}")

        self._write_pending(remaining)
        return rejected

    def is_allowed(self, user_id: int) -> bool:
        allowlist = self._load_allowlist()
        return any(entry.user_id == user_id for entry in allowlist)

    def revoke(self, user_id: int) -> None:
        allowlist = self._load_allowlist()
        filtered = [entry for entry in allowlist if entry.user_id != user_id]
        if len(filtered) != len(allowlist):
            self._write_allowlist(filtered)

    def list_pending(self) -> List[PendingRequest]:
        pending = self._purge_expired(self._load_pending())
        return sorted(pending, key=lambda item: item.requested_at)

    # ----- Internal helpers ------------------------------------------
    def _load_pending(self) -> List[PendingRequest]:
        if not self._pending_path.exists():
            return []
        content = self._pending_path.read_text(encoding="utf-8")
        if not content.strip():
            return []
        raw = json.loads(content)
        return [PendingRequest.from_dict(item) for item in raw]

    def _write_pending(self, pending: List[PendingRequest]) -> None:
        payload = [req.to_dict() for req in pending]
        self._pending_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_allowlist(self) -> List[ApprovedUser]:
        if not self._allowlist_path.exists():
            return []
        content = self._allowlist_path.read_text(encoding="utf-8")
        if not content.strip():
            return []
        raw = json.loads(content)
        return [ApprovedUser.from_dict(item) for item in raw]

    def _write_allowlist(self, allowlist: List[ApprovedUser]) -> None:
        payload = [entry.to_dict() for entry in allowlist]
        self._allowlist_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def _add_allowlist_entry(self, user_id: int) -> None:
        allowlist = self._load_allowlist()
        if any(entry.user_id == user_id for entry in allowlist):
            return
        allowlist.append(ApprovedUser(user_id=user_id, approved_at=self._clock()))
        self._write_allowlist(allowlist)

    def _purge_expired(self, pending: List[PendingRequest]) -> List[PendingRequest]:
        cutoff = self._clock() - timedelta(seconds=self._ttl)
        retained = [req for req in pending if req.requested_at >= cutoff]
        if len(retained) != len(pending):
            self._write_pending(retained)
        return retained

    @staticmethod
    def _generate_code(existing: set[str]) -> str:
        while True:
            code = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(PAIRING_CODE_LENGTH))
            if code not in existing:
                return code

    @staticmethod
    def _trim_preview(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        cleaned = " ".join(value.split())
        if len(cleaned) <= 200:
            return cleaned
        return cleaned[:199] + "…"
