from typing import Dict, List, Any
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class KnowledgeAgent(BaseAgent):
    def __init__(self, vector_store):
        super().__init__()
        self.vector_store = vector_store
        self.system_message = """You are an expert in machine failure analysis with deep knowledge of:
- Industrial equipment maintenance patterns
- Common failure modes and their symptoms
- Historical failure analysis
- Equipment manuals and technical documentation

Use the provided documentation to identify failure patterns and map symptoms to potential causes."""
    
    async def analyze_documents(self, documents: List[str], session_id: str) -> Dict[str, Any]:
        try:
            combined_docs = "\n\n".join(documents[:5])
            
            chat = await self.create_chat(self.system_message, session_id)
            
            prompt = f"""Analyze these technical documents and extract:
1. Known failure patterns
2. Symptom-to-cause mappings
3. Critical parameters to monitor
4. Maintenance recommendations

Documents:
{combined_docs[:5000]}

Provide a structured analysis."""
            
            analysis = await self.send_message(chat, prompt)
            
            return {
                "document_analysis": analysis,
                "failure_patterns": self.extract_failure_patterns(analysis)
            }
        except Exception as e:
            logger.error(f"Error in knowledge analysis: {e}")
            return {"document_analysis": "Analysis failed", "failure_patterns": []}
    
    async def query_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        try:
            results = self.vector_store.query(query, n_results=5)
            return results
        except Exception as e:
            logger.error(f"Error querying knowledge base: {e}")
            return []
    
    def extract_failure_patterns(self, analysis: str) -> List[str]:
        return [
            "Bearing wear due to insufficient lubrication",
            "Thermal degradation from sustained overload",
            "Mechanical misalignment causing vibration",
            "Electrical fault from insulation breakdown"
        ]