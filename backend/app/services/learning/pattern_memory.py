"""
Pattern Memory Service.

Menggunakan ChromaDB sebagai memori jangka panjang untuk menyimpan 
dan mencari pola pasar yang serupa berdasarkan embedding.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

class PatternMemory:
    """Service untuk manajemen memori pola pasar (Vector DB)."""

    def __init__(self, persist_directory: str = "./data/chroma"):
        from app.core.config import settings
        
        if settings.CHROMADB_HOST:
            logger.info("connecting_to_remote_chromadb", host=settings.CHROMADB_HOST, port=settings.CHROMADB_PORT)
            self.client = chromadb.HttpClient(
                host=settings.CHROMADB_HOST,
                port=settings.CHROMADB_PORT,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            logger.info("using_local_chromadb", path=persist_directory)
            self.client = chromadb.PersistentClient(path=persist_directory)
            
        self.collection = self.client.get_or_create_collection(
            name="trade_patterns",
            metadata={"hnsw:space": "cosine"} # Menggunakan cosine similarity
        )

    def store_pattern(
        self, 
        vector: List[float], 
        metadata: Dict[str, Any], 
        pattern_id: str
    ):
        """
        Simpan sidik jari pasar ke memori.
        vector: State vector dari StateSpace service.
        metadata: { "outcome": "WIN" | "LOSS", "pnl": 2.5, "symbol": "BTC/USDT" }
        """
        try:
            # ChromaDB expects a list of embeddings
            self.collection.add(
                embeddings=[vector],
                metadatas=[metadata],
                ids=[pattern_id]
            )
            logger.info("pattern_stored", pattern_id=pattern_id, outcome=metadata.get("outcome"))
        except Exception as e:
            logger.error("pattern_storage_failed", error=str(e))

    def find_similar(
        self,
        vector: List[float],
        n_results: int = 5,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Cari pola paling mirip di masa lalu, optionally filtered by symbol.
        Per-symbol filtering prevents BTC patterns from contaminating ETH/SOL predictions
        (and vice versa) since each coin has different volatility and behavior.
        """
        try:
            query_kwargs: Dict[str, Any] = {
                "query_embeddings": [vector],
                "n_results": n_results,
            }
            if symbol:
                query_kwargs["where"] = {"symbol": symbol}

            results = self.collection.query(**query_kwargs)

            formatted = []
            if results["metadatas"]:
                for meta in results["metadatas"][0]:
                    formatted.append(meta)
            return formatted
        except Exception as e:
            logger.error("pattern_search_failed", error=str(e), symbol=symbol)
            return []

    def get_market_experience(self, vector: List[float], symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Mendapatkan 'pengalaman' pasar berdasarkan kemiripan, optionally per-symbol.
        Return: { "win_rate": 0.6, "average_pnl": 1.2, "sample_size": 5 }
        """
        similars = self.find_similar(vector, symbol=symbol)
        if not similars:
            return {"win_rate": 0.5, "average_pnl": 0.0, "sample_size": 0}

        wins = [1 for s in similars if s.get("outcome") == "WIN"]
        pnls = [float(s.get("pnl", 0)) for s in similars]

        return {
            "win_rate": len(wins) / len(similars),
            "average_pnl": sum(pnls) / len(pnls),
            "sample_size": len(similars)
        }

    def count(self) -> int:
        """Returns total number of stored patterns."""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error("pattern_count_failed", error=str(e))
            return 0
