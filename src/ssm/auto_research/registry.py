from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ssm.auto_research.hashing import canonical_json_bytes, sha256_value, write_canonical_json


class RegistryEntry(BaseModel):
    schema_version: str = "1.0"
    kind: str = "RegistryEntry"
    digest: str
    record_kind: str
    stored_path: str
    signature_algorithm: str | None = None
    signature: str | None = None
    key_id: str | None = None


class ContentAddressedRegistry:
    """Local immutable record registry with optional detached HMAC integrity signatures."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.objects = self.root / "objects" / "sha256"
        self.entries = self.root / "entries"

    def add(
        self,
        payload: dict[str, Any],
        *,
        signing_key: str | bytes | None = None,
        key_id: str | None = None,
    ) -> RegistryEntry:
        digest_hex = sha256_value(payload)
        digest = f"sha256:{digest_hex}"
        object_path = self.objects / digest_hex[:2] / f"{digest_hex}.json"
        object_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = canonical_json_bytes(payload)
        if object_path.exists() and object_path.read_bytes() != encoded:
            raise ValueError("Content-address collision or corrupted registry object.")
        if not object_path.exists():
            object_path.write_bytes(encoded)
        signature = None
        algorithm = None
        if signing_key is not None:
            key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
            signature = hmac.new(key, encoded, hashlib.sha256).hexdigest()
            algorithm = "hmac-sha256"
        entry = RegistryEntry(
            digest=digest,
            record_kind=str(payload.get("kind", "Unknown")),
            stored_path=str(object_path.relative_to(self.root)),
            signature_algorithm=algorithm,
            signature=signature,
            key_id=key_id,
        )
        entry_path = self.entries / f"{digest_hex}.json"
        write_canonical_json(entry_path, entry.model_dump(mode="json"))
        return entry

    def get(self, digest: str) -> dict[str, Any]:
        digest_hex = digest.removeprefix("sha256:")
        path = self.objects / digest_hex[:2] / f"{digest_hex}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if sha256_value(payload) != digest_hex:
            raise ValueError("Registry object digest mismatch.")
        if not isinstance(payload, dict):
            raise ValueError("Registry object must contain a JSON object.")
        return payload

    def verify(self, digest: str, *, signing_key: str | bytes | None = None) -> bool:
        digest_hex = digest.removeprefix("sha256:")
        payload = self.get(digest)
        entry_path = self.entries / f"{digest_hex}.json"
        entry = RegistryEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))
        if entry.signature is None:
            return signing_key is None
        if signing_key is None:
            signing_key = os.getenv("SSM_RESEARCH_REGISTRY_KEY")
        if signing_key is None:
            return False
        key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        expected = hmac.new(key, canonical_json_bytes(payload), hashlib.sha256).hexdigest()
        return hmac.compare_digest(entry.signature, expected)
