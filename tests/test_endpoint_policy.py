"""Tests for mutating endpoint authorization policies."""

from __future__ import annotations

import pytest

from evidencegraph.endpoint_policy import UnsafeEndpointError, validate_bootstrap_target


@pytest.mark.parametrize(
    "url",
    (
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://[::1]:8080",
        "https://LOCALHOST/api",
    ),
)
def test_local_bootstrap_targets_do_not_require_remote_authorization(url: str) -> None:
    validate_bootstrap_target(url, allow_remote=False)


def test_remote_bootstrap_requires_an_explicit_gate() -> None:
    with pytest.raises(UnsafeEndpointError, match="--allow-remote-bootstrap"):
        validate_bootstrap_target("https://datahub.example.com", allow_remote=False)

    validate_bootstrap_target("https://datahub.example.com", allow_remote=True)


@pytest.mark.parametrize(
    "url",
    (
        "datahub.example.com:8080",
        "file:///tmp/datahub",
        "https://user:password@datahub.example.com",
    ),
)
def test_invalid_or_credential_bearing_bootstrap_urls_are_always_rejected(url: str) -> None:
    with pytest.raises(UnsafeEndpointError):
        validate_bootstrap_target(url, allow_remote=True)
