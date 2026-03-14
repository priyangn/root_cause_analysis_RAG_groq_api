import pandas as pd
import numpy as np
from typing import Dict, List, Any

class VisualizationGenerator:
    @staticmethod
    def generate_time_series_data(dataframes: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Generate time series visualization data"""
        chart_data = []
        
        for df in dataframes:
            if df.empty or len(df) > 100:
                df = df.head(100)  # Limit to 100 points
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns[:5]  # Max 5 series
            
            for idx, row in df.iterrows():
                data_point = {"index": int(idx) if isinstance(idx, (int, np.integer)) else str(idx)}
                for col in numeric_cols:
                    data_point[str(col)] = float(row[col]) if pd.notna(row[col]) else 0
                chart_data.append(data_point)
                
            if chart_data:
                break
        
        return chart_data[:50]  # Limit to 50 points
    
    @staticmethod
    def generate_correlation_matrix(dataframes: List[pd.DataFrame]) -> Dict[str, Any]:
        """Generate correlation matrix data"""
        for df in dataframes:
            if df.empty:
                continue
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns[:10]
            if len(numeric_cols) < 2:
                continue
            
            corr_matrix = df[numeric_cols].corr()
            
            correlations = []
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols):
                    if i < j:  # Only upper triangle
                        correlations.append({
                            "param1": str(col1),
                            "param2": str(col2),
                            "correlation": float(corr_matrix.loc[col1, col2])
                        })
            
            return {
                "parameters": [str(c) for c in numeric_cols],
                "correlations": correlations
            }
        
        return {"parameters": [], "correlations": []}
    
    @staticmethod
    def generate_feature_importance_chart(ml_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate feature importance visualization data"""
        chart_data = []
        
        if ml_results and len(ml_results) > 0:
            # Use the best performing model
            best_model = max(ml_results, key=lambda x: x.get('accuracy', 0))
            feature_importance = best_model.get('feature_importance', {})
            
            for param, importance in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:8]:
                chart_data.append({
                    "parameter": str(param),
                    "importance": float(importance) * 100
                })
        
        return chart_data
