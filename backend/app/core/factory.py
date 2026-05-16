from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
from app.core.providers.google_provider import GoogleProvider
from app.core.providers.openai_provider import OpenAIProvider
from app.agents.technical import TechnicalAnalystAgent
from app.agents.fundamental import FundamentalAnalystAgent
from app.agents.sentiment import SentimentAnalystAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.orchestrator import MasterOrchestrator
from app.services.consensus import ConsensusEngine
from app.services.regime_detector import RegimeDetector
from app.services.regime_strategy import RegimeStrategy
from app.services.agent_scorer import AgentScorer
from app.services.execution import ExecutionEngine
from app.services.pre_trade_validator import PreTradeValidator
from app.services.learning.state_space import StateSpace
from app.services.learning.pattern_memory import PatternMemory
from app.services.exchange import ExchangeService
from app.services.paper_trading import PaperTradingEngine
from app.services.telegram import TelegramService

class ServiceFactory:
    """Singleton factory to manage service instances."""
    _instance = None
    
    def __init__(self, db: Session):
        # AI Provider Configuration from DB (with environment defaults)
        from app.models.system_settings import SystemSettings
        self._ai_provider_name = SystemSettings.get_value(db, "ai_provider", settings.AI_PROVIDER)
        
        # Intelligent model selection: fallback to provider-specific defaults if DB is empty/invalid
        db_model = SystemSettings.get_value(db, "ai_model")
        if not db_model or db_model == "None":
            if self._ai_provider_name == "nvidia":
                self._ai_model_name = "meta/llama-3.1-70b-instruct"
            elif self._ai_provider_name == "google":
                self._ai_model_name = "gemini-1.5-pro"
            elif self._ai_provider_name == "anthropic":
                self._ai_model_name = "claude-3-5-sonnet-20240620"
            else:
                self._ai_model_name = settings.AI_MODEL
        else:
            self._ai_model_name = db_model
        
        ai_provider = self._ai_provider_name
        ai_model = self._ai_model_name
        
        # Provider-specific API Keys
        from app.core.encryption import decrypt
        
        def safe_decrypt(val):
            if not val: return val
            try:
                # Fernet tokens start with gAAAAA
                if val.startswith("gAAAAA"):
                    return decrypt(val)
            except:
                pass
            return val

        openai_key = safe_decrypt(SystemSettings.get_value(db, "ai_api_key_openai", settings.AI_API_KEY))
        google_key = safe_decrypt(SystemSettings.get_value(db, "ai_api_key_google", settings.AI_API_KEY))
        anthropic_key = safe_decrypt(SystemSettings.get_value(db, "ai_api_key_anthropic", settings.AI_API_KEY))
        nvidia_key = safe_decrypt(SystemSettings.get_value(db, "ai_api_key_nvidia", settings.NVIDIA_API_KEY))

        if ai_provider == "google":
            self.ai = GoogleProvider(api_key=google_key, model=ai_model)
        elif ai_provider == "anthropic":
            from app.core.providers.anthropic_provider import AnthropicProvider
            self.ai = AnthropicProvider(api_key=anthropic_key, model=ai_model)
        elif ai_provider == "nvidia":
            from app.core.providers.nvidia_provider import NvidiaProvider
            self.ai = NvidiaProvider(api_key=nvidia_key, model=ai_model)
        else:
            self.ai = OpenAIProvider(api_key=openai_key, model=ai_model)
            
        # Infrastructure
        from app.models.risk_state import RiskState
        from app.models.exchange_credential import ExchangeCredential
        from app.core.encryption import decrypt
        
        risk_state = db.query(RiskState).first()
        is_live = risk_state.is_live_enabled if risk_state else False
        active_profile = "live" if is_live else "demo"
        
        cred = db.query(ExchangeCredential).filter_by(profile=active_profile).first()
        if cred and cred.api_key and cred.api_secret:
            is_demo_trading = cred.base_url and "api-demo.bybit.com" in cred.base_url
            self.exchange = ExchangeService(
                api_key=decrypt(cred.api_key),
                api_secret=decrypt(cred.api_secret),
                testnet=(active_profile == "demo" and not is_demo_trading),
                base_url=cred.base_url
            )
            if cred.base_url:
                if isinstance(self.exchange.exchange.urls.get('api'), dict):
                    for k in self.exchange.exchange.urls['api']:
                        self.exchange.exchange.urls['api'][k] = cred.base_url
                else:
                    self.exchange.exchange.urls['api'] = cred.base_url
            logger.info("factory_exchange_initialized_from_db", profile=active_profile, base_url=cred.base_url)
        else:
            self.exchange = ExchangeService()
            logger.info("factory_exchange_initialized_from_env")
            
        self.telegram = TelegramService()
        
        # Agents & Logic (Statesless or reused)
        self.technical = TechnicalAnalystAgent(self.ai)
        self.fundamental = FundamentalAnalystAgent(self.ai)
        self.sentiment = SentimentAnalystAgent(self.ai)
        self.risk_manager = RiskManagerAgent(self.ai)
        
        self.consensus = ConsensusEngine()
        self.regime_detector = RegimeDetector()
        self.regime_strategy = RegimeStrategy()
        self.state_space = StateSpace()
        self.pattern_memory = PatternMemory()

        # Load RL Model (PPO) — refuse to load if obs dim doesn't match current StateSpace
        self.rl_model = None
        try:
            import os
            from stable_baselines3 import PPO

            models_dir = os.path.join(os.getcwd(), "models")
            os.makedirs(models_dir, exist_ok=True)

            model_path = os.path.join(models_dir, "apex_ppo_latest.zip")
            if not os.path.exists(model_path):
                logger.warning("rl_model_not_found_skipping_load", path=model_path)
            else:
                expected_dim = self.state_space.feature_dim
                candidate = PPO.load(model_path)
                actual_shape = candidate.observation_space.shape
                if actual_shape == (expected_dim,):
                    self.rl_model = candidate
                    logger.info("rl_model_loaded_successfully", path=model_path, obs_dim=expected_dim)
                else:
                    logger.warning(
                        "rl_model_dim_mismatch_skipping",
                        expected=expected_dim,
                        actual=actual_shape,
                        hint="Run nightly_trainer to retrain with new state space",
                    )
        except Exception as e:
            logger.error("failed_to_load_rl_model", error=str(e))

    async def close(self):
        """Release all owned async resources (ccxt session, telegram client)."""
        # Exchange (ccxt async client → aiohttp session)
        try:
            if getattr(self, "exchange", None) is not None:
                await self.exchange.close()
        except Exception as e:
            logger.warning("factory_exchange_close_failed", error=str(e))
        # Telegram HTTP client
        try:
            if getattr(self, "telegram", None) is not None:
                await self.telegram.close()
        except Exception as e:
            logger.warning("factory_telegram_close_failed", error=str(e))

    @classmethod
    async def shutdown(cls):
        """Close the singleton instance and drop it. Safe to call at app shutdown."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
            logger.info("service_factory_shutdown_complete")

    @classmethod
    async def get_orchestrator(cls, db: Session) -> MasterOrchestrator:
        from app.models.system_settings import SystemSettings

        # Check if AI settings changed in DB
        db_provider = SystemSettings.get_value(db, "ai_provider", settings.AI_PROVIDER)
        db_model_raw = SystemSettings.get_value(db, "ai_model")

        # Determine what the effective model would be
        if not db_model_raw or db_model_raw == "None":
            if db_provider == "nvidia":
                effective_db_model = "meta/llama-3.1-70b-instruct"
            elif db_provider == "google":
                effective_db_model = "gemini-1.5-pro"
            elif db_provider == "anthropic":
                effective_db_model = "claude-3-5-sonnet-20240620"
            else:
                effective_db_model = settings.AI_MODEL
        else:
            effective_db_model = db_model_raw

        if cls._instance is not None:
            if cls._instance._ai_provider_name != db_provider or cls._instance._ai_model_name != effective_db_model:
                logger.info("ai_settings_changed_refreshing_factory",
                            old_p=cls._instance._ai_provider_name, new_p=db_provider,
                            old_m=cls._instance._ai_model_name, new_m=effective_db_model)
                # Await cleanup of the old instance's async resources (ccxt session,
                # telegram client) BEFORE replacing the singleton, so we never leak
                # aiohttp/Bybit connections on AI provider swap.
                old_instance = cls._instance
                cls._instance = None
                try:
                    await old_instance.close()
                except Exception as e:
                    logger.warning("factory_refresh_close_failed", error=str(e))

        if cls._instance is None:
            cls._instance = ServiceFactory(db)
        
        factory = cls._instance
        
        # Database-dependent services (need new instance per session usually, or injected db)
        paper = PaperTradingEngine(db)
        agent_scorer = AgentScorer(db)
        execution = ExecutionEngine(
            factory.exchange, db, paper, factory.telegram,
            pattern_memory=factory.pattern_memory,
            agent_scorer=agent_scorer,
        )
        validator = PreTradeValidator(db) # Fixed: Removed exchange argument
        
        return MasterOrchestrator(
            ai_provider=factory.ai,
            technical_agent=factory.technical,
            fundamental_agent=factory.fundamental,
            sentiment_agent=factory.sentiment,
            risk_manager=factory.risk_manager,
            consensus_engine=factory.consensus,
            regime_detector=factory.regime_detector,
            regime_strategy=factory.regime_strategy,
            agent_scorer=agent_scorer,
            execution_engine=execution,
            pre_trade_validator=validator,
            state_space=factory.state_space,
            pattern_memory=factory.pattern_memory,
            rl_model=factory.rl_model,
            db=db
        )

async def create_orchestrator(db: Session) -> MasterOrchestrator:
    return await ServiceFactory.get_orchestrator(db)
