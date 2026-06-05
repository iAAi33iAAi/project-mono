"""
Tests for Aethel Grid Stewardship Kernel
Laminar Lattice Prime 3.6.9 -- SPEC.md section 2 compliance tests
"""

import pytest

from aethel.stewardship import (
    AethelGrid,
    Domain,
    DomainScore,
    GatewayLayer,
    OrchestrationLayer,
    EffectivenessLedger,
    ExecutionLayer,
    ProcessManifest,
    SubstrateMetrics,
    compute_efficiency_score,
    compute_psi,
    psi_gate,
    validate_efficiency,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TOKEN = "test-stewardship-token"

@pytest.fixture
def metrics_nominal():
    return SubstrateMetrics(v_h=1000.0, omega=0.3)

@pytest.fixture
def metrics_high_entropy():
    return SubstrateMetrics(v_h=1000.0, omega=0.99)

@pytest.fixture
def all_domain_scores_low():
    return [DomainScore(d, 0.05) for d in Domain]

@pytest.fixture
def all_domain_scores_high():
    return [DomainScore(d, 0.9) for d in Domain]

@pytest.fixture
def manifest_valid(all_domain_scores_low):

# ---------------------------------------------------------------------------
# Section 2.1 Architect's Constant
# ---------------------------------------------------------------------------

class TestArchitectsConstant:

    def test_efficiency_score_nominal(self):
        score = compute_efficiency_score(output_capacity=50.0, v_h=1000.0)
        assert score == pytest.approx(5.0)

    def test_efficiency_score_below_one(self):
        score = compute_efficiency_score(output_capacity=0.5, v_h=1000.0)
        assert score < 1.0

    def test_zero_vh_raises(self):
        with pytest.raises(ValueError):
            SubstrateMetrics(v_h=0.0, omega=0.3)

    def test_validate_efficiency_pass(self, metrics_nominal):
        assert validate_efficiency(50.0, metrics_nominal.v_h) is True

    def test_validate_efficiency_fail(self, metrics_nominal):
        assert validate_efficiency(0.001, metrics_nominal.v_h) is False


# ---------------------------------------------------------------------------
# Section 2.2 Psi Coefficient
# ---------------------------------------------------------------------------

class TestPsiCoefficient:

    def test_psi_below_threshold(self, all_domain_scores_low, metrics_nominal):
        psi = compute_psi(all_domain_scores_low, metrics_nominal)
        assert psi < 1.0

    def test_psi_above_threshold(self, all_domain_scores_high, metrics_high_entropy):
        psi = compute_psi(all_domain_scores_high, metrics_high_entropy)
        assert psi > 1.0

    def test_psi_gate_allow(self, all_domain_scores_low, metrics_nominal):
        assert psi_gate(all_domain_scores_low, metrics_nominal) is True

    def test_psi_gate_throttle(self, all_domain_scores_high, metrics_high_entropy):
        assert psi_gate(all_domain_scores_high, metrics_high_entropy) is False

    def test_psi_zero_omega(self, metrics_nominal):
        scores = [DomainScore(d, 0.0) for d in Domain]
        m = SubstrateMetrics(v_h=1000.0, omega=0.0)
        psi = compute_psi(scores, m)
        assert psi == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Gateway Layer
# ---------------------------------------------------------------------------

class TestGatewayLayer:

    def test_loopback_no_token(self):
        gw = GatewayLayer()
        session = gw.open_session(token="", peer="127.0.0.1")
        assert session is not None

    def test_non_loopback_requires_token(self):
        gw = GatewayLayer()
        with pytest.raises(PermissionError):
            gw.open_session(token="bad", peer="10.0.0.1")

    def test_valid_token_admitted(self):

# ---------------------------------------------------------------------------
# Orchestration Layer
# ---------------------------------------------------------------------------

class TestOrchestrationLayer:

    def test_handler_registered_and_dispatched(self):
        ledger = EffectivenessLedger()
        orch = OrchestrationLayer(ledger)
        received = []
        orch.register_handler(Domain.ECONOMIC, lambda pid, ds: received.append(ds))
        scores = [DomainScore(d, 0.1) for d in Domain]
        orch.dispatch("pid-001", scores)
        assert len(received) == 1

    def test_require_all_domains_pass(self):
        ledger = EffectivenessLedger()
        orch = OrchestrationLayer(ledger)
        scores = [DomainScore(d, 0.1) for d in Domain]
        orch.dispatch("pid-002", scores)
        assert orch.require_all_domains("pid-002") is True

    def test_require_all_domains_fail(self):
        ledger = EffectivenessLedger()
        orch = OrchestrationLayer(ledger)
        orch.dispatch("pid-003", [DomainScore(Domain.ECONOMIC, 0.1)])
        assert orch.require_all_domains("pid-003") is False


# ---------------------------------------------------------------------------
# Execution Layer
# ---------------------------------------------------------------------------

class TestExecutionLayer:

    def test_valid_plugin_runs(self, manifest_valid):
        gw = GatewayLayer()
        ledger = EffectivenessLedger()
        orch = OrchestrationLayer(ledger)
        exe = ExecutionLayer(gw, orch)
        exe.register_plugin(manifest_valid)
        sid = gw.open_session("", "127.0.0.1")
        scores = [DomainScore(d, 0.1) for d in Domain]
        result = exe.run(manifest_valid, sid, scores, action=lambda: 42)
        assert result == 42

    def test_unregistered_plugin_raises(self, manifest_valid):
        gw = GatewayLayer()
        ledger = EffectivenessLedger()
        orch = OrchestrationLayer(ledger)
        exe = ExecutionLayer(gw, orch)
        sid = gw.open_session("", "127.0.0.1")
        scores = [DomainScore(d, 0.1) for d in Domain]
        with pytest.raises(PermissionError):
            exe.run(manifest_valid, sid, scores, action=lambda: None)

    def test_expired_session_raises(self, manifest_valid):
        gw = GatewayLayer()
        ledger = EffectivenessLedger()
        orch = OrchestrationLayer(ledger)
        exe = ExecutionLayer(gw, orch)
        exe.register_plugin(manifest_valid)
        sid = gw.open_session("", "127.0.0.1")
        scores = [DomainScore(d, 0.1) for d in Domain]
        with pytest.raises(PermissionError):
            exe.run(manifest_valid, "invalid-session-id", scores, action=lambda: None)


# ---------------------------------------------------------------------------
# Full AethelGrid pipeline
# ---------------------------------------------------------------------------

class TestAethelGrid:

    def test_run_plugin_success(self, metrics_nominal, manifest_valid):
        grid = AethelGrid()
        grid.set_substrate(metrics_nominal)
        token = grid.issue_token()
        sid = grid.open_session(token)
        grid.execution.register_plugin(manifest_valid)
        scores = [DomainScore(d, 0.05) for d in Domain]
        result = grid.run_plugin(manifest_valid, sid, scores, action=lambda: "ok")
        assert result == "ok"

    def test_psi_exceeded_blocks_run(self, metrics_high_entropy, manifest_valid):
        grid = AethelGrid()
        grid.set_substrate(metrics_high_entropy)
        token = grid.issue_token()
        sid = grid.open_session(token)
        grid.execution.register_plugin(manifest_valid)
        scores = [DomainScore(d, 0.9) for d in Domain]
        with pytest.raises(RuntimeError, match="Psi"):
            grid.run_plugin(manifest_valid, sid, scores, action=lambda: None)

    def test_no_substrate_blocks_run(self, manifest_valid):
        grid = AethelGrid()
        token = grid.issue_token()
        sid = grid.open_session(token)
        scores = [DomainScore(d, 0.1) for d in Domain]
        with pytest.raises(RuntimeError, match="substrate"):
            grid.run_plugin(manifest_valid, sid, scores, action=lambda: None)

    def test_ledger_audit_report(self, metrics_nominal, manifest_valid):
        grid = AethelGrid()
        grid.set_substrate(metrics_nominal)
        token = grid.issue_token()
        sid = grid.open_session(token)
        grid.execution.register_plugin(manifest_valid)
        scores = [DomainScore(d, 0.05) for d in Domain]
        grid.run_plugin(manifest_valid, sid, scores, action=lambda: None)
        report = grid.ledger.audit_report()
        assert manifest_valid.process_id in report

        gw = GatewayLayer(allowed_tokens=[TOKEN])
        token = TOKEN
        session = gw.open_session(token=token, peer="192.168.1.1")
        assert session is not None

    def test_session_expires(self):
        gw = GatewayLayer()
        sid = gw.open_session("", "localhost")
        assert gw.validate_session(sid, ttl=0.0) is False

    return ProcessManifest(
        name="test_process",
        permissions=["read:/data"],
    )

@pytest.fixture
def grid():
    gw = GatewayLayer(allowed_tokens=[TOKEN])
    ledger = EffectivenessLedger()
    orch = OrchestrationLayer(ledger)
    exe = ExecutionLayer(gw, orch)
    return gw, ledger, orch, exe
