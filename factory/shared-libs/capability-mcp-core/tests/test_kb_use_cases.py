"""KBUseCases tests — read / list / diff with a tmp factory_dir + fake k8s."""
from __future__ import annotations

from src.application.kb_use_cases import KBUseCases
from src.infrastructure.kb_loader import KBLoader


def test_read_returns_entry(factory_dir, fake_k8s):
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    entry = uc.read("nats-jetstream")
    assert entry is not None
    assert entry["technology"] == "nats-jetstream"
    assert entry["provisioning"]["kind"] == "helm-chart"
    assert entry["provisioning"]["requires_cluster_permissions"] is True


def test_read_missing(factory_dir, fake_k8s):
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    assert uc.read("does-not-exist") is None


def test_list_filters(factory_dir, fake_k8s):
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    assert {e["technology"] for e in uc.list()} == {"kafka", "nats-jetstream"}
    assert [e["technology"] for e in uc.list(maturity="published")] == ["nats-jetstream"]
    assert [e["technology"] for e in uc.list(maturity="kb")] == ["kafka"]
    assert [e["technology"] for e in uc.list(category="messaging")] == ["kafka", "nats-jetstream"]


def test_diff_none(factory_dir, fake_k8s):
    """KB published + cluster has CD → gap_kind=none."""
    fake_k8s.add("nats-jetstream")
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    d = uc.diff("nats-jetstream")
    assert d["gap_kind"] == "none"
    assert d["kb_present"] is True
    assert d["oam_present"] is True


def test_diff_needs_oam(factory_dir, fake_k8s):
    """KB kb-maturity + no CD → gap_kind=needs_oam (also covers the synthesise branch)."""
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    d = uc.diff("kafka")
    assert d["gap_kind"] == "needs_oam"
    assert d["provisioning_kind"] == "operator-backed"


def test_diff_drift(factory_dir, fake_k8s):
    """KB kb-maturity + cluster HAS the CD → drift (someone deployed without promoting KB)."""
    fake_k8s.add("kafka")
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    d = uc.diff("kafka")
    assert d["gap_kind"] == "drift"


def test_diff_oam_orphan(factory_dir, fake_k8s):
    """Cluster has CD but KB has no row → orphan (architect should backfill KB)."""
    fake_k8s.add("some-tech")
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    d = uc.diff("some-tech")
    assert d["gap_kind"] == "oam_orphan"


def test_diff_unknown(factory_dir, fake_k8s):
    """Neither side knows."""
    uc = KBUseCases(KBLoader(str(factory_dir)), fake_k8s)
    d = uc.diff("nothing-here")
    assert d["gap_kind"] == "unknown"
