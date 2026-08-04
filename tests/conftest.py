from pathlib import Path

import pytest

from evidencegraph.models import ChangeRequest, ContextSnapshot
from evidencegraph.orchestrator import load_change, load_snapshot

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def change() -> ChangeRequest:
    return load_change(ROOT / "fixtures/changes/drop_customer_tier.json")


@pytest.fixture
def snapshot() -> ContextSnapshot:
    return load_snapshot(ROOT / "fixtures/platform.json")
