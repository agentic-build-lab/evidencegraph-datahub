"""Endpoint policies for operations that mutate external systems."""

from __future__ import annotations

from urllib.parse import urlsplit

LOCAL_DATAHUB_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class UnsafeEndpointError(ValueError):
    """Raised when a mutating command targets an endpoint without explicit authorization."""


def validate_bootstrap_target(gms_url: str, *, allow_remote: bool) -> None:
    """Require an explicit gate before bootstrapping a non-local DataHub instance."""

    parsed = urlsplit(gms_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise UnsafeEndpointError("DataHub GMS URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeEndpointError("DataHub GMS URL must not contain embedded credentials")
    if parsed.hostname.casefold() not in LOCAL_DATAHUB_HOSTS and not allow_remote:
        raise UnsafeEndpointError(
            "refusing to bootstrap a remote DataHub instance without --allow-remote-bootstrap"
        )
