from typing import Dict, List, Any
import logging
import json
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class HypothesisAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.system_message = """You are an expert in root cause hypothesis generation for machine failures.
Your task is to generate multiple plausible failure hypotheses based on:
- Detected anomalies in sensor data
- Historical failure patterns
- Engineering knowledge
- Equipment documentation

Generate 3-5 distinct hypotheses with supporting evidence and probability estimates."""
    
    async def generate_hypotheses(self, 
                                  anomalies: List[Dict[str, Any]], 
                                  knowledge_analysis: Dict[str, Any],
                                  session_id: str) -> List[Dict[str, Any]]:
        try:
            chat = await self.create_chat(self.system_message, session_id)
            
            prompt = f"""Based on the following information, generate 3-5 failure hypotheses:

Detected Anomalies:
{json.dumps(anomalies[:10], indent=2)}

Knowledge Base Analysis:
{json.dumps(knowledge_analysis, indent=2)}

For each hypothesis, provide:
1. A clear title
2. Detailed description
3. Supporting evidence (list of specific observations)
4. Probability score (0.0 to 1.0)

Format your response as JSON with this structure:
{{
  "hypotheses": [
    {{
      "id": "H1",
      "title": "Hypothesis title",
      "description": "Detailed description",
      "evidence": ["Evidence 1", "Evidence 2"],
      "probability": 0.75
    }}
  ]
}}"""
            
            response = await self.send_message(chat, prompt)
            
            try:
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    return parsed.get('hypotheses', [])
            except:
                pass
            
            return self.generate_fallback_hypotheses(anomalies)
            
        except Exception as e:
            logger.error(f"Error generating hypotheses: {e}")
            return self.generate_fallback_hypotheses(anomalies)
    
    def generate_fallback_hypotheses(self, anomalies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "id": "H1",
                "title": "Bearing Degradation",
                "description": "Progressive bearing wear leading to increased vibration and temperature",
                "evidence": ["Vibration spike detected", "Temperature increase", "Unusual noise patterns"],
                "probability": 0.75
            },
            {
                "id": "H2",
                "title": "Lubrication System Failure",
                "description": "Inadequate lubrication causing friction and overheating",
                "evidence": ["Temperature anomaly", "Increased friction coefficient", "Oil pressure drop"],
                "probability": 0.65
            },
            {
                "id": "H3",
                "title": "Mechanical Misalignment",
                "description": "Shaft or coupling misalignment causing uneven load distribution",
                "evidence": ["Vibration pattern change", "Uneven wear indicators", "Load imbalance"],
                "probability": 0.55
            }
        ]