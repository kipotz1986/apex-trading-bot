import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.risk_manager import RiskManagerAgent
from app.schemas.portfolio import PortfolioState, Position, RiskDecision
from app.services.mode_profile import MODE_PROFILES

@pytest.fixture
def mock_ai_provider():
    return AsyncMock()

@pytest.fixture
def healthy_portfolio():
    return PortfolioState(
        total_balance=10000.0,
        total_equity=10050.0,
        available_margin=9000.0,
        open_positions=[
            Position(
                symbol="BTC/USDT",
                side="LONG",
                size=0.01,
                entry_price=60000.0,
                current_price=61000.0,
                unrealized_pnl=10.0
            )
        ],
        daily_pnl_pct=1.0,
        weekly_pnl_pct=5.0,
        max_drawdown_pct=2.0
    )

@pytest.fixture
def failing_portfolio():
    """Portfolio yang melanggar daily loss limit aggressive (12%)."""
    return PortfolioState(
        total_balance=10000.0,
        total_equity=8000.0,
        available_margin=5000.0,
        open_positions=[],
        daily_pnl_pct=-15.0,  # melampaui limit 12%
        weekly_pnl_pct=-20.0,
        max_drawdown_pct=10.0,
    )

@pytest.fixture
def drawdown_portfolio():
    """Portfolio yang melanggar max drawdown limit (30%)."""
    return PortfolioState(
        total_balance=10000.0,
        total_equity=6500.0,
        available_margin=3000.0,
        open_positions=[],
        daily_pnl_pct=-2.0,
        weekly_pnl_pct=-15.0,
        max_drawdown_pct=35.0,  # melampaui limit 30%
    )


@pytest.mark.asyncio
async def test_critical_override_daily_loss_bypasses_ai(mock_ai_provider, failing_portfolio):
    """Daily loss limit adalah critical override — AI tidak dipanggil."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    decision = await agent.analyze("ETH/USDT", "BUY", 500.0, failing_portfolio)

    assert decision.decision == "REJECT"
    assert "CRITICAL OVERRIDE" in decision.reasoning
    assert "Daily loss limit reached" in decision.reasoning
    mock_ai_provider.analyze.assert_not_called()


@pytest.mark.asyncio
async def test_critical_override_max_drawdown_bypasses_ai(mock_ai_provider, drawdown_portfolio):
    """Max drawdown adalah critical override — AI tidak dipanggil."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    decision = await agent.analyze("ETH/USDT", "BUY", 500.0, drawdown_portfolio)

    assert decision.decision == "REJECT"
    assert "CRITICAL OVERRIDE" in decision.reasoning
    assert "Max drawdown" in decision.reasoning
    mock_ai_provider.analyze.assert_not_called()


@pytest.mark.asyncio
async def test_ai_drives_approve_flow(mock_ai_provider, healthy_portfolio):
    """Trade sehat: AI menjadi pengambil keputusan dan APPROVE."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 500.0, "max_leverage": 5,'
        ' "reasoning": "Portfolio sehat, size kecil.", "risk_metrics": {"is_within_limits": true}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    decision = await agent.analyze("ETH/USDT", "BUY", 500.0, healthy_portfolio)

    assert decision.decision == "APPROVE"
    assert decision.max_position_size_usd == 500.0
    assert decision.risk_metrics.get("ai_driven") is True
    mock_ai_provider.analyze.assert_called_once()


@pytest.mark.asyncio
async def test_ai_receives_hard_rule_context(mock_ai_provider, healthy_portfolio):
    """AI dipanggil dengan Hard Rule Evaluation block sebagai konteks."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 500.0, "max_leverage": 5,'
        ' "reasoning": "OK", "risk_metrics": {}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    await agent.analyze("ETH/USDT", "BUY", 500.0, healthy_portfolio)

    call_kwargs = mock_ai_provider.analyze.call_args.kwargs
    assert "Hard Rule Evaluation" in call_kwargs["data"]
    assert "daily_loss_breached" in call_kwargs["data"]
    assert "exposure_would_breach" in call_kwargs["data"]


@pytest.mark.asyncio
async def test_safety_layer_caps_ai_oversized_approval(mock_ai_provider, healthy_portfolio):
    """AI tidak dapat melampaui hard cap 20% equity — safety layer me-reduce-size."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    # AI mencoba approve $5000 (~50% equity), jauh di atas hard cap 20%
    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 5000.0, "max_leverage": 5,'
        ' "reasoning": "Looks good!", "risk_metrics": {}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    decision = await agent.analyze("ETH/USDT", "BUY", 5000.0, healthy_portfolio)

    # 20% of 10050.0 = 2010.0
    assert decision.decision == "REDUCE_SIZE"
    assert decision.max_position_size_usd <= 2010.0
    assert "capped at 20.0% equity" in decision.reasoning


@pytest.mark.asyncio
async def test_safety_layer_blocks_exposure_breach(mock_ai_provider):
    """Jika total exposure akan melampaui limit, safety layer override AI ke REJECT."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    # Portfolio dengan posisi besar — exposure sudah dekat limit
    heavy_portfolio = PortfolioState(
        total_balance=10000.0,
        total_equity=10000.0,
        available_margin=2000.0,
        open_positions=[
            Position(
                symbol="BTC/USDT", side="LONG", size=0.13,
                entry_price=60000.0, current_price=60000.0, unrealized_pnl=0.0
            )
        ],
        daily_pnl_pct=0.0,
        weekly_pnl_pct=0.0,
        max_drawdown_pct=0.0,
    )

    # AI naively approves; safety layer must catch exposure breach
    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 1500.0, "max_leverage": 5,'
        ' "reasoning": "Optimistic AI", "risk_metrics": {}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    decision = await agent.analyze("ETH/USDT", "BUY", 1500.0, heavy_portfolio)

    # Current exposure ~7800, +1500 = 9300 = 93% > 80% cap
    assert decision.decision == "REJECT"
    assert "Total exposure would exceed" in decision.reasoning


@pytest.mark.asyncio
async def test_system_prompt_includes_active_profile_directive(mock_ai_provider, healthy_portfolio):
    """System prompt sent to AI must contain the active profile directive block."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 500.0, "max_leverage": 5,'
        ' "reasoning": "OK", "risk_metrics": {}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    # No db → falls back to DEFAULT_PROFILE_SLUG (very_aggressive)
    await agent.analyze("ETH/USDT", "BUY", 500.0, healthy_portfolio)

    sp = mock_ai_provider.analyze.call_args.kwargs["system_prompt"]
    assert "ACTIVE TRADING PROFILE" in sp
    assert "very_aggressive" in sp
    assert "Stance:" in sp
    assert "Approval bar:" in sp


@pytest.mark.asyncio
async def test_profile_conservative_uses_its_limits(mock_ai_provider, healthy_portfolio):
    """When active profile is Conservative, hard caps and directive reflect that."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 150.0, "max_leverage": 2,'
        ' "reasoning": "Conservative-friendly trade", "risk_metrics": {}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    conservative = MODE_PROFILES["conservative"]
    with patch.object(agent, "_resolve_profile", return_value=conservative):
        decision = await agent.analyze("ETH/USDT", "BUY", 150.0, healthy_portfolio)

    sp = mock_ai_provider.analyze.call_args.kwargs["system_prompt"]
    assert "conservative" in sp
    assert "VERY CAUTIOUS" in sp
    # Conservative max_position_size is 2% → hard cap on 10050 equity = 201.0
    assert decision.risk_metrics.get("profile") == "conservative"
    assert decision.risk_metrics.get("profile_risk_level") == 1


@pytest.mark.asyncio
async def test_profile_conservative_caps_oversized_ai(mock_ai_provider, healthy_portfolio):
    """AI overshoot on Conservative profile is capped to that profile's 2% size limit."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    # AI tries $1000 (~10% equity) but profile cap is 2% → 201.0
    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 1000.0, "max_leverage": 10,'
        ' "reasoning": "Optimistic but profile is conservative", "risk_metrics": {}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    conservative = MODE_PROFILES["conservative"]
    with patch.object(agent, "_resolve_profile", return_value=conservative):
        decision = await agent.analyze("ETH/USDT", "BUY", 1000.0, healthy_portfolio)

    # 2% of 10050.0 = 201.0
    assert decision.decision == "REDUCE_SIZE"
    assert decision.max_position_size_usd <= 201.0
    assert "capped at 2.0% equity" in decision.reasoning
    # Leverage must also be capped at profile's max (3x)
    assert decision.max_leverage <= 3


@pytest.mark.asyncio
async def test_profile_yolo_allows_aggressive_sizing(mock_ai_provider, healthy_portfolio):
    """YOLO profile permits much larger positions before the safety layer trims."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    # AI approves $3000 (~30% equity) — under YOLO's 35% cap
    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "APPROVE", "max_position_size_usd": 3000.0, "max_leverage": 25,'
        ' "reasoning": "YOLO mode: full send", "risk_metrics": {}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    yolo = MODE_PROFILES["yolo"]
    with patch.object(agent, "_resolve_profile", return_value=yolo):
        decision = await agent.analyze("ETH/USDT", "BUY", 3000.0, healthy_portfolio)

    # YOLO cap is 35% of 10050 = 3517.5 → $3000 fits
    assert decision.decision == "APPROVE"
    assert decision.max_position_size_usd == 3000.0
    assert decision.max_leverage == 25
    assert decision.risk_metrics.get("profile") == "yolo"


@pytest.mark.asyncio
async def test_ai_decides_reduce_size_for_soft_cap(mock_ai_provider, healthy_portfolio):
    """AI dapat memutuskan REDUCE_SIZE saat melihat soft cap di hard rule context."""
    agent = RiskManagerAgent(ai_provider=mock_ai_provider)

    # AI honors the context and reduces voluntarily
    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"decision": "REDUCE_SIZE", "max_position_size_usd": 1800.0, "max_leverage": 10,'
        ' "reasoning": "Size exceeds soft cap per Hard Rule Evaluation; reducing to 18% equity.",'
        ' "risk_metrics": {"is_within_limits": true}}'
    )
    mock_ai_provider.analyze.return_value = mock_ai_response

    decision = await agent.analyze("ETH/USDT", "BUY", 3000.0, healthy_portfolio)

    assert decision.decision == "REDUCE_SIZE"
    assert decision.max_position_size_usd == 1800.0
    mock_ai_provider.analyze.assert_called_once()
