import pandas as pd
import numpy as np
from typing import Dict, List, Any

class VisualizationGenerator:
    @staticmethod
    def generate_time_series_data(dataframes: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Generate time series visualization data with proper timestamps"""
        chart_data = []
        
        for df in dataframes:
            if df.empty:
                continue
            
            # Limit data points for performance
            if len(df) > 100:
                df = df.iloc[::len(df)//100]  # Sample evenly
            
            # Find timestamp column
            timestamp_col = None
            for col in df.columns:
                if 'time' in str(col).lower() or 'date' in str(col).lower():
                    timestamp_col = col
                    break
            
            # Get numeric columns (max 5 for clarity)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:5]
            
            if not numeric_cols:
                continue
            
            for idx, row in df.iterrows():
                data_point = {}
                
                # Add timestamp if available, otherwise use index
                if timestamp_col and timestamp_col in df.columns:
                    try:
                        # Try to format timestamp nicely
                        ts_value = row[timestamp_col]
                        if pd.notna(ts_value):
                            data_point["time"] = str(ts_value)
                        else:
                            data_point["time"] = str(idx)
                    except:
                        data_point["time"] = str(idx)
                else:
                    data_point["time"] = str(idx)
                
                # Add numeric values
                for col in numeric_cols:
                    if pd.notna(row[col]):
                        data_point[str(col)] = float(row[col])
                
                if len(data_point) > 1:  # Only add if has data beyond timestamp
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
