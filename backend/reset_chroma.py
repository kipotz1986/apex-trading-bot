import chromadb
from app.core.config import settings

def reset_chroma():
    print(f"Connecting to ChromaDB at {settings.CHROMADB_HOST}:{settings.CHROMADB_PORT}...")
    client = chromadb.HttpClient(host=settings.CHROMADB_HOST, port=settings.CHROMADB_PORT)
    
    try:
        print("Deleting collection 'trade_patterns' due to dimension mismatch...")
        client.delete_collection("trade_patterns")
        print("Successfully deleted. It will be recreated with correct dimensions (28) on next bot run.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_chroma()
