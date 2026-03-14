import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict, Any
import hashlib

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = "/app/backend/chroma_db"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = None
    
    def get_or_create_collection(self, collection_name: str):
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Machine failure analysis documents"}
            )
            return self.collection
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return None
    
    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]]):
        if not self.collection:
            logger.error("Collection not initialized")
            return False
        
        try:
            ids = [hashlib.md5(doc.encode()).hexdigest()[:16] for doc in documents]
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to vector store")
            return True
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    def query(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        if not self.collection:
            logger.error("Collection not initialized")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            documents = []
            if results and 'documents' in results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    documents.append({
                        "content": doc,
                        "metadata": metadata,
                        "distance": distance
                    })
            
            return documents
        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            return []