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
                "visualizations": {}
            }
            
            if progress_callback:
                await progress_callback(10, "Parsing documents...", 30)
            
            parsed_files = []
            documents = []
            dataframes = []
            
            for file_path in file_paths:
                parsed = DocumentParser.parse_file(file_path)
                parsed_files.append(parsed)
                
                if parsed.get('content'):
                    documents.append(parsed['content'])
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
            
            if progress_callback:
                await progress_callback(45, "Analyzing knowledge base...", 15)
            
            knowledge_analysis = await self.knowledge_agent.analyze_documents(documents, self.session_id)
            
            if progress_callback:
                await progress_callback(55, "Generating hypotheses...", 12)
            
            result['hypotheses'] = await self.hypothesis_agent.generate_hypotheses(
                result['anomalies'],
                knowledge_analysis,
                self.session_id
            )
            
            if progress_callback:
                await progress_callback(65, "Training ML models...", 10)
            
            result['ml_results'] = await self.ml_agent.train_and_validate(dataframes)
            
            if progress_callback:
                await progress_callback(80, "Performing causal analysis...", 7)
            
            result['causal_analysis'] = await self.causal_agent.perform_causal_analysis(
                dataframes,
                result['ml_results']
            )
            
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
                await progress_callback(100, "Analysis complete", 0)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in analysis pipeline: {e}")
            raise