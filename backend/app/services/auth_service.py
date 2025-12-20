"""
Authentication service for API key verification.

Depends only on:
- TenantRepo Protocol (duck-typed method get_by_api_key_hash)
- Core auth utilities (hash_api_key)

Behavior:
    authenticate(api_key) -> tenant
    - Hashes the incoming API key using HMAC-SHA256 (env-secret based)
    - Looks up tenant by the resulting hash
    - Ensures tenant is active
    - Raises AuthError otherwise
"""

from __future__ import annotations

from typing import Any, Optional

from app.core.auth import hash_api_key
from app.core.contracts import TenantRepo


class AuthError(Exception):
    """Raised when API key authentication fails."""


class AuthService:
    """
    Small service to authenticate requests using an API key.
    """

    def __init__(self, tenant_repo: TenantRepo) -> None:
        self.tenant_repo = tenant_repo

    def _get_by_api_key_hash(self, api_key_hash: str) -> Optional[Any]:
        """
        Lookup tenant by API key hash. Requires the repository to support
        `get_by_api_key_hash`. Duck-typed to avoid hard dependency on concrete repos.
        """
        getter = getattr(self.tenant_repo, "get_by_api_key_hash", None)
        if callable(getter):
            return getter(api_key_hash)  # type: ignore[misc]
        raise NotImplementedError("TenantRepo does not implement get_by_api_key_hash")

    def authenticate(self, api_key: str) -> Any:
        """
        Authenticate a request by API key.

        Args:
            api_key: Raw API key provided by the caller.

        Returns:
            A tenant entity (repo-specific type) when authentication succeeds.

        Raises:
            AuthError: If the key is invalid or the tenant is inactive/missing.
        """
        if not isinstance(api_key, str) or not api_key.strip():
            raise AuthError("API key is required")

        api_key_hash = hash_api_key(api_key)
        tenant = self._get_by_api_key_hash(api_key_hash)

        if tenant is None:
            raise AuthError("Invalid API key")

        # Best-effort check: expect an `is_active` attribute on tenant entities
        is_active = getattr(tenant, "is_active", True)
        if not bool(is_active):
            raise AuthError("Tenant is inactive")

        return tenant
