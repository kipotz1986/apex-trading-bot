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
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Cari pola paling mirip di masa lalu.
        """
        try:
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=n_results
            )
            
            # Reformat results
            formatted = []
            if results["metadatas"]:
                for meta in results["metadatas"][0]:
                    formatted.append(meta)
            return formatted
        except Exception as e:
            logger.error("pattern_search_failed", error=str(e))
            return []

    def get_market_experience(self, vector: List[float]) -> Dict[str, Any]:
        """
        Mendapatkan 'pengalaman' pasar berdasarkan kemiripan.
        Return: { "win_rate": 0.6, "average_pnl": 1.2, "sample_size": 5 }
        """
        similars = self.find_similar(vector)
        if not similars:
            return {"win_rate": 0.5, "average_pnl": 0.0, "sample_size": 0}
            
        wins = [1 for s in similars if s.get("outcome") == "WIN"]
        pnls = [float(s.get("pnl", 0)) for s in similars]
        
        return {
            "win_rate": len(wins) / len(similars),
            "average_pnl": sum(pnls) / len(pnls),
            "sample_size": len(similars)
        }
