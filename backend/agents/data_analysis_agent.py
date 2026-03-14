import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging
import json
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class DataAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.system_message = """You are a data analysis expert specializing in industrial machine failure analysis.
Your task is to analyze sensor data, detect anomalies, and generate statistical summaries.
Provide precise, technical analysis based on the data provided."""
    
    async def analyze_data(self, dataframes: List[pd.DataFrame], session_id: str) -> Dict[str, Any]:
        try:
            anomalies = self.detect_anomalies(dataframes)
            summary = self.generate_summary(dataframes)
            
            chat = await self.create_chat(self.system_message, session_id)
            
            analysis_prompt = f"""Analyze the following machine data:

Data Summary:
{summary}

Detected Anomalies:
{json.dumps(anomalies, indent=2)}

Provide a technical analysis of these findings and identify potential failure indicators."""
            
            ai_analysis = await self.send_message(chat, analysis_prompt)
            
            return {
                "anomalies": anomalies,
                "summary": summary,
                "ai_analysis": ai_analysis
            }
        except Exception as e:
            logger.error(f"Error in data analysis: {e}")
            return {"anomalies": [], "summary": {}, "ai_analysis": "Analysis failed"}
    
    def detect_anomalies(self, dataframes: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        anomalies = []
        
        for df in dataframes:
            if df.empty:
                continue
            
            # Check for timestamp column
            timestamp_col = None
            for col in df.columns:
                if 'time' in str(col).lower() or 'date' in str(col).lower():
                    timestamp_col = col
                    break
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                if col in df.columns:
                    mean = df[col].mean()
                    std = df[col].std()
                    
                    if std > 0:
                        z_scores = np.abs((df[col] - mean) / std)
                        anomaly_indices = np.where(z_scores > 3)[0]
                        
                        for idx in anomaly_indices[:10]:
                            anomaly_data = {
                                "parameter": col,
                                "value": float(df[col].iloc[idx]),
                                "threshold": float(mean + 3 * std),
                                "severity": "high" if z_scores.iloc[idx] > 4 else "medium",
                                "row_index": int(idx)
                            }
                            
                            # Add timestamp if available
                            if timestamp_col and timestamp_col in df.columns:
                                try:
                                    anomaly_data["timestamp"] = str(df[timestamp_col].iloc[idx])
                                except:
                                    anomaly_data["timestamp"] = f"Row {idx}"
                            else:
                                anomaly_data["timestamp"] = str(df.index[idx]) if hasattr(df.index, '__getitem__') else f"Row {idx}"
                            
                            anomalies.append(anomaly_data)
        
        return anomalies[:20]
    
    def generate_summary(self, dataframes: List[pd.DataFrame]) -> Dict[str, Any]:
        summary = {
            "total_records": 0,
            "parameters": [],
            "statistics": {}
        }
        
        for df in dataframes:
            if df.empty:
                continue
            
            summary["total_records"] += len(df)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                if col not in summary["parameters"]:
                    summary["parameters"].append(col)
                
                summary["statistics"][col] = {
                    "mean": float(df[col].mean()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max())
                }
        
        return summary