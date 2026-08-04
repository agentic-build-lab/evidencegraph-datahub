from pathlib import Path

import pytest

from scripts.freeze_examples import _assert_publishable_tree


def test_publishable_tree_accepts_synthetic_evidence(tmp_path: Path) -> None:
    (tmp_path / "ledger.json").write_text(
        '{"run_id":"EG-AAAAAAAAAAAA","asset":"commerce.raw_orders"}',
        encoding="utf-8",
    )

    _assert_publishable_tree(tmp_path)


@pytest.mark.parametrize(
    "leak",
    [
        'Authorization: Bearer super-secret-token',
        '"password": "customer-password-123"',
        r'C:\\Users\\analyst\\private.json',
        "owner@example.com",
    ],
)
def test_publishable_tree_rejects_sensitive_material(tmp_path: Path, leak: str) -> None:
    (tmp_path / "ledger.json").write_text(leak, encoding="utf-8")

    with pytest.raises(ValueError, match="public evidence safety scan failed"):
        _assert_publishable_tree(tmp_path)
