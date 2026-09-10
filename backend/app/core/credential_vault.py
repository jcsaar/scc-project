from dataclasses import dataclass

from pydantic import SecretStr


class CredentialNotFound(LookupError):
    pass


@dataclass(repr=False)
class _CredentialEntry:
    provider: str
    credential: SecretStr


class CredentialVault:
    def __init__(self) -> None:
        self._entries: dict[str, _CredentialEntry] = {}

    def put(self, session_id: str, provider: str, credential: SecretStr) -> None:
        self._entries[session_id] = _CredentialEntry(provider=provider, credential=credential)

    def resolve_for_session(self, session_id: str) -> SecretStr:
        entry = self._entries.get(session_id)
        if entry is None:
            raise CredentialNotFound("Provider credential not found")
        return entry.credential

    def delete_session(self, session_id: str) -> None:
        self._entries.pop(session_id, None)

    def __repr__(self) -> str:
        return f"CredentialVault(entries={len(self._entries)})"
