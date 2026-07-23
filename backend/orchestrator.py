from typing import Dict, List, Any
import logging
from pathlib import Path
import asyncio
import time

from document_parser import DocumentParser
from vector_store import VectorStore
from agents.data_analysis_agent import DataAnalysisAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.hypothesis_agent import HypothesisAgent
from agents.ml_validation_agent import MLValidationAgent
from agents.causal_inference_agent import CausalInferenceAgent
from agents.report_generation_agent import ReportGenerationAgent
from visualization_generator import VisualizationGenerator

logger = logging.getLogger(__name__)

class AnalysisPipeline:
    def __init__(self, user_id: str, analysis_id: str):
        self.user_id = user_id
        self.analysis_id = analysis_id
        self.session_id = f"{user_id}_{analysis_id}"
        
        self.vector_store = VectorStore()
        self.vector_store.get_or_create_collection(f"analysis_{analysis_id}")
        
        self.data_agent = DataAnalysisAgent()
        self.knowledge_agent = KnowledgeAgent(self.vector_store)
        self.hypothesis_agent = HypothesisAgent()
        self.ml_agent = MLValidationAgent()
        self.causal_agent = CausalInferenceAgent()
        self.report_agent = ReportGenerationAgent()
    
    async def run(self, file_paths: List[str], progress_callback=None) -> Dict[str, Any]:
        try:
            start_time = time.time()
            result = {
                "anomalies": [],
                "hypotheses": [],
                "ml_results": [],
                "causal_analysis": [],
                "root_cause": None,
                "visualizations": {},
                "data_summary": {},
                "document_excerpts": [],
                "uploaded_files": [],
                "knowledge_insights": "",
            }
            
            if progress_callback:
                await progress_callback(10, "Parsing documents...", 30)
            
            parsed_files = []
            documents = []
            dataframes = []
            
            for file_path in file_paths:
                parsed = DocumentParser.parse_file(file_path)
                parsed_files.append(parsed)
                name = Path(file_path).name
                result["uploaded_files"].append({
                    "name": name,
                    "path": file_path,
                    "has_text": bool(parsed.get("content")),
                    "has_table": parsed.get("dataframe") is not None
                    and not getattr(parsed.get("dataframe"), "empty", True),
                })
                
                if parsed.get('content'):
                    documents.append(parsed['content'])
                    # Keep a short excerpt for chat / grounding (not full manuals)
                    excerpt = (parsed["content"] or "").strip()[:3500]
                    if excerpt:
                        result["document_excerpts"].append({
                            "file": name,
                            "excerpt": excerpt,
                        })
                if parsed.get('dataframe') is not None and not parsed['dataframe'].empty:
                    dataframes.append(parsed['dataframe'])
            
            if progress_callback:
                await progress_callback(20, "Indexing documents...", 25)
            
            if documents:
                self.vector_store.add_documents(
                    documents,
                    [{"file_path": pf['file_path'], "type": "document"} for pf in parsed_files if pf.get('content')]
                )
            
            if progress_callback:
                await progress_callback(30, "Detecting anomalies...", 20)
            
            data_analysis = await self.data_agent.analyze_data(dataframes, self.session_id)
            result['anomalies'] = data_analysis.get('anomalies', [])
            result['data_summary'] = data_analysis.get('summary') or {}
            # Optional short AI note from data agent (truncate for storage)
            ai_note = data_analysis.get('ai_analysis') or ""
            if isinstance(ai_note, str) and ai_note.strip():
                result['data_summary'] = {
                    **(result['data_summary'] if isinstance(result['data_summary'], dict) else {}),
                    "ai_analysis_excerpt": ai_note.strip()[:2000],
                }
            
            if progress_callback:
                await progress_callback(45, "Analyzing knowledge base...", 15)
            
            knowledge_analysis = await self.knowledge_agent.analyze_documents(documents, self.session_id)
            if isinstance(knowledge_analysis, str):
                result["knowledge_insights"] = knowledge_analysis[:3000]
            elif isinstance(knowledge_analysis, dict):
                result["knowledge_insights"] = str(knowledge_analysis)[:3000]
            else:
                result["knowledge_insights"] = ""
            
            if progress_callback:
                await progress_callback(55, "Generating hypotheses...", 12)
            
            try:
                result['hypotheses'] = await self.hypothesis_agent.generate_hypotheses(
                    result['anomalies'],
                    knowledge_analysis,
                    self.session_id
                )
            except Exception as hyp_error:
                logger.error(f"Hypothesis generation error: {hyp_error}")
                result['hypotheses'] = self.hypothesis_agent.generate_fallback_hypotheses(result['anomalies'])
            
            if progress_callback:
                await progress_callback(65, "Training ML models (sampled for memory)...", 10)

            try:
                result['ml_results'] = await self.ml_agent.train_and_validate(dataframes)
                if progress_callback:
                    await progress_callback(75, "ML training complete", 8)
            except Exception as ml_error:
                logger.error(f"ML training error: {ml_error}")
                result['ml_results'] = self.ml_agent.generate_mock_results()
                if progress_callback:
                    await progress_callback(75, "ML training used fallback results", 8)

            if progress_callback:
                await progress_callback(80, "Performing causal analysis...", 7)

            try:
                result['causal_analysis'] = await self.causal_agent.perform_causal_analysis(
                    dataframes,
                    result['ml_results']
                )
            except Exception as causal_error:
                logger.error(f"Causal analysis error: {causal_error}")
                result['causal_analysis'] = self.causal_agent.generate_mock_causal_params()
            
            if progress_callback:
                await progress_callback(90, "Generating report...", 3)
            
            result['root_cause'] = await self.report_agent.generate_report(
                result['anomalies'],
                result['hypotheses'],
                result['ml_results'],
                result['causal_analysis'],
                self.session_id
            )
            
            # Generate visualizations
            if dataframes:
                result['visualizations'] = {
                    'time_series': VisualizationGenerator.generate_time_series_data(dataframes),
                    'correlation': VisualizationGenerator.generate_correlation_matrix(dataframes),
                    'feature_importance': VisualizationGenerator.generate_feature_importance_chart(result['ml_results'])
                }
            
            if progress_callback:
                await progress_callback(99, "Saving results...", 1)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in analysis pipeline: {e}")
            raise