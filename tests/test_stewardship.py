import pytest

from aethel.stewardship import (
    AethelGrid,
    Domain,
    DomainScore,
    EffectivenessLedger,
    ExecutionLayer,
    GatewayLayer,
    OrchestrationLayer,
    ProcessManifest,
    SubstrateMetrics,
    compute_efficiency_score,
    compute_psi,
    psi_gate,
    validate_efficiency,
)


TOKEN = "test-stewardship-token"


@pytest.fixture
def metrics_nominal():
    return SubstrateMetrics(v_h=1000.0, omega=0.3)


@pytest.fixture
def metrics_high_entropy():
    return SubstrateMetrics(v_h=100.0, omega=0.99)


@pytest.fixture
def all_domain_scores_low():
    return [DomainScore(domain, 0.05) for domain in Domain]


@pytest.fixture
def all_domain_scores_high():
    return [DomainScore(domain, 0.9) for domain in Domain]


@pytest.fixture
def manifest_valid(all_domain_scores_low):
    del all_domain_scores_low
    return ProcessManifest(name="test_process", permissions=["read:/data"])


class TestArchitectsConstant:
    def test_efficiency_score_nominal(self):
        assert compute_efficiency_score(50.0, 1000.0) == pytest.approx(5.0)

    def test_efficiency_score_below_one(self):
        assert compute_efficiency_score(0.5, 1000.0) < 1.0

    def test_zero_vh_raises(self):
        with pytest.raises(ValueError):
            SubstrateMetrics(v_h=0.0, omega=0.3)

    def test_validate_efficiency_pass(self, metrics_nominal):
        assert validate_efficiency(50.0, metrics_nominal.v_h) is True

    def test_validate_efficiency_fail(self, metrics_nominal):
        assert validate_efficiency(0.001, metrics_nominal.v_h) is False


class TestPsiCoefficient:
    def test_psi_below_threshold(self, all_domain_scores_low, metrics_nominal):
        assert compute_psi(all_domain_scores_low, metrics_nominal) < 1.0

    def test_psi_above_threshold(self, all_domain_scores_high, metrics_high_entropy):
        assert compute_psi(all_domain_scores_high, metrics_high_entropy) > 1.0

    def test_psi_gate_allow(self, all_domain_scores_low, metrics_nominal):
        assert psi_gate(all_domain_scores_low, metrics_nominal) is True

    def test_psi_gate_throttle(self, all_domain_scores_high, metrics_high_entropy):
        assert psi_gate(all_domain_scores_high, metrics_high_entropy) is False

    def test_psi_zero_omega(self):
        scores = [DomainScore(domain, 0.0) for domain in Domain]
        substrate = SubstrateMetrics(v_h=1000.0, omega=0.0)
        assert compute_psi(scores, substrate) == pytest.approx(0.0)


class TestGatewayLayer:
    def test_loopback_no_token(self):
        gateway = GatewayLayer()
        assert gateway.open_session("", "127.0.0.1")

    def test_non_loopback_requires_token(self):
        gateway = GatewayLayer()
        with pytest.raises(PermissionError):
            gateway.open_session("bad", "10.0.0.1")

    def test_valid_token_admitted(self):
        gateway = GatewayLayer(allowed_tokens=[TOKEN])
        assert gateway.open_session(TOKEN, "192.168.1.1")

    def test_session_expires(self):
        gateway = GatewayLayer()
        session = gateway.open_session("", "localhost")
        assert gateway.validate_session(session, ttl=0.0) is False


class TestOrchestrationLayer:
    def test_handler_registered_and_dispatched(self):
        ledger = EffectivenessLedger()
        orchestration = OrchestrationLayer(ledger)
        received = []
        orchestration.register_handler(
            Domain.ECONOMIC,
            lambda process_id, score: received.append(score),
        )
        scores = [DomainScore(domain, 0.1) for domain in Domain]
        orchestration.dispatch("pid-001", scores)
        assert len(received) == 1

    def test_require_all_domains_pass(self):
        ledger = EffectivenessLedger()
        orchestration = OrchestrationLayer(ledger)
        scores = [DomainScore(domain, 0.1) for domain in Domain]
        orchestration.dispatch("pid-002", scores)
        assert orchestration.require_all_domains("pid-002") is True

    def test_require_all_domains_fail(self):
        ledger = EffectivenessLedger()
        orchestration = OrchestrationLayer(ledger)
        orchestration.dispatch("pid-003", [DomainScore(Domain.ECONOMIC, 0.1)])
        assert orchestration.require_all_domains("pid-003") is False


class TestExecutionLayer:
    def test_valid_plugin_runs(self, manifest_valid):
        gateway = GatewayLayer()
        ledger = EffectivenessLedger()
        orchestration = OrchestrationLayer(ledger)
        execution = ExecutionLayer(gateway, orchestration)
        execution.register_plugin(manifest_valid)
        session = gateway.open_session("", "127.0.0.1")
        scores = [DomainScore(domain, 0.1) for domain in Domain]
        assert execution.run(manifest_valid, session, scores, lambda: 42) == 42

    def test_unregistered_plugin_raises(self, manifest_valid):
        gateway = GatewayLayer()
        ledger = EffectivenessLedger()
        orchestration = OrchestrationLayer(ledger)
        execution = ExecutionLayer(gateway, orchestration)
        session = gateway.open_session("", "127.0.0.1")
        scores = [DomainScore(domain, 0.1) for domain in Domain]
        with pytest.raises(PermissionError):
            execution.run(manifest_valid, session, scores, lambda: None)

    def test_expired_session_raises(self, manifest_valid):
        gateway = GatewayLayer()
        ledger = EffectivenessLedger()
        orchestration = OrchestrationLayer(ledger)
        execution = ExecutionLayer(gateway, orchestration)
        execution.register_plugin(manifest_valid)
        scores = [DomainScore(domain, 0.1) for domain in Domain]
        with pytest.raises(PermissionError):
            execution.run(manifest_valid, "invalid-session-id", scores, lambda: None)


class TestAethelGrid:
    def test_run_plugin_success(self, metrics_nominal, manifest_valid):
        grid = AethelGrid()
        grid.set_substrate(metrics_nominal)
        session = grid.open_session("")
        grid.execution.register_plugin(manifest_valid)
        scores = [DomainScore(domain, 0.05) for domain in Domain]
        assert grid.run_plugin(manifest_valid, session, scores, lambda: "ok") == "ok"

    def test_psi_exceeded_blocks_run(self, metrics_high_entropy, manifest_valid):
        grid = AethelGrid()
        grid.set_substrate(metrics_high_entropy)
        session = grid.open_session("")
        grid.execution.register_plugin(manifest_valid)
        scores = [DomainScore(domain, 0.9) for domain in Domain]
        with pytest.raises(RuntimeError, match="Psi"):
            grid.run_plugin(manifest_valid, session, scores, lambda: None)

    def test_no_substrate_blocks_run(self, manifest_valid):
        grid = AethelGrid()
        session = grid.open_session("")
        scores = [DomainScore(domain, 0.1) for domain in Domain]
        with pytest.raises(RuntimeError, match="substrate"):
            grid.run_plugin(manifest_valid, session, scores, lambda: None)

    def test_ledger_audit_report(self, metrics_nominal, manifest_valid):
        grid = AethelGrid()
        grid.set_substrate(metrics_nominal)
        session = grid.open_session("")
        grid.execution.register_plugin(manifest_valid)
        scores = [DomainScore(domain, 0.05) for domain in Domain]
        grid.run_plugin(manifest_valid, session, scores, lambda: None)
        assert manifest_valid.process_id in grid.ledger.audit_report()
