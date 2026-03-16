import pandas as pd
import numpy as np
from typing import Dict, List, Any

class VisualizationGenerator:
    @staticmethod
    def generate_time_series_data(dataframes: List[pd.DataFrame]) -> List[Dict[str, Any]]:
        """Generate time series visualization data with original timestamps preserved"""
        chart_data = []
        
        for df in dataframes:
            if df.empty:
                continue
            
            # Sample data if too large (keep every nth row to get ~50-100 points)
            if len(df) > 100:
                step = len(df) // 100
                df = df.iloc[::step].copy()
            
            # Find timestamp/date column
            timestamp_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if 'time' in col_lower or 'date' in col_lower:
                    timestamp_col = col
                    break
            
            # Get numeric columns (max 5 for clarity)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:5]
            
            if not numeric_cols:
                continue
            
            # Build chart data preserving original timestamps
            for idx, row in df.iterrows():
                data_point = {}
                
                # Use original timestamp value from dataset
                if timestamp_col is not None and timestamp_col in df.columns:
                    try:
                        original_ts = row[timestamp_col]
                        if pd.notna(original_ts):
                            # Keep original format exactly as in uploaded file
                            data_point["time"] = str(original_ts)
                        else:
                            data_point["time"] = f"Row {idx}"
                    except Exception as e:
                        logger.error(f"Error reading timestamp at row {idx}: {e}")
                        data_point["time"] = f"Row {idx}"
                else:
                    # No timestamp column - use row number
                    data_point["time"] = f"Row {idx}"
                
                # Add numeric values
                for col in numeric_cols:
                    if pd.notna(row[col]):
                        data_point[str(col)] = float(row[col])
                
                # Only add if has numeric data
                if len(data_point) > 1:
                    chart_data.append(data_point)
            
            if chart_data:
                break  # Use first dataframe with data
        
        return chart_data[:50]  # Limit to 50 points for performance
    
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
