from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.providers.google_provider import GoogleProvider
from app.core.providers.openai_provider import OpenAIProvider
from app.agents.technical import TechnicalAnalystAgent
from app.agents.fundamental import FundamentalAnalystAgent
from app.agents.sentiment import SentimentAnalystAgent
from app.agents.risk_manager import RiskManagerAgent
from app.agents.copy_trader import CopyTradingAgent
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
        # AI Provider
        if settings.AI_PROVIDER == "google":
            self.ai = GoogleProvider(api_key=settings.AI_API_KEY)
        else:
            self.ai = OpenAIProvider(api_key=settings.AI_API_KEY, model=settings.AI_MODEL)
            
        # Infrastructure
        self.exchange = ExchangeService()
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

    @classmethod
    def get_orchestrator(cls, db: Session) -> MasterOrchestrator:
        if cls._instance is None:
            cls._instance = ServiceFactory(db)
        
        factory = cls._instance
        
        # Database-dependent services (need new instance per session usually, or injected db)
        paper = PaperTradingEngine(db)
        execution = ExecutionEngine(factory.exchange, db, paper, factory.telegram)
        copy_trader = CopyTradingAgent(db)
        agent_scorer = AgentScorer(db)
        validator = PreTradeValidator(db) # Fixed: Removed exchange argument
        
        return MasterOrchestrator(
            ai_provider=factory.ai,
            technical_agent=factory.technical,
            fundamental_agent=factory.fundamental,
            sentiment_agent=factory.sentiment,
            risk_manager=factory.risk_manager,
            copy_trader=copy_trader,
            consensus_engine=factory.consensus,
            regime_detector=factory.regime_detector,
            regime_strategy=factory.regime_strategy,
            agent_scorer=agent_scorer,
            execution_engine=execution,
            pre_trade_validator=validator,
            state_space=factory.state_space,
            pattern_memory=factory.pattern_memory
        )

def create_orchestrator(db: Session) -> MasterOrchestrator:
    return ServiceFactory.get_orchestrator(db)
