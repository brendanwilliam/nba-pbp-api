"""
Statistical analysis service with pandas integration.
Provides statistical summaries, correlation analysis, and regression capabilities.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.responses import (
    StatisticalSummary, 
    CorrelationAnalysis, 
    RegressionAnalysis, 
    StatisticalAnalysis
)


class StatsAnalyzer:
    """Statistical analysis service for NBA data"""
    
    def __init__(self):
        self.df = None
    
    def analyze_dataframe(self, 
                         df: pd.DataFrame,
                         about_fields: List[str] = None,
                         correlation_fields: List[str] = None,
                         regression_spec: Dict[str, str] = None) -> StatisticalAnalysis:
        """
        Perform comprehensive statistical analysis on DataFrame
        
        Args:
            df: DataFrame to analyze
            about_fields: Fields to calculate statistical summaries for
            correlation_fields: Fields to calculate correlations between
            regression_spec: Dictionary with 'dependent' and 'independent' variables
            
        Returns:
            StatisticalAnalysis object with all requested analyses
        """
        self.df = df
        
        analysis = StatisticalAnalysis(
            data=df.to_dict('records'),
            total_records=len(df),
            query_metadata={
                "generated_at": datetime.now().isoformat(),
                "analysis_requested": {
                    "summary_stats": bool(about_fields),
                    "correlation": bool(correlation_fields),
                    "regression": bool(regression_spec)
                }
            }
        )
        
        # Calculate summary statistics if requested
        if about_fields:
            analysis.summary_stats = self._calculate_summary_stats(about_fields)
        
        # Calculate correlations if requested
        if correlation_fields:
            analysis.correlation_analysis = self._calculate_correlations(correlation_fields)
        
        # Perform regression if requested
        if regression_spec:
            analysis.regression_analysis = self._perform_regression(regression_spec)
        
        return analysis
    
    def _calculate_summary_stats(self, fields: List[str]) -> List[StatisticalSummary]:
        """Calculate statistical summary for specified fields"""
        summaries = []
        
        for field in fields:
            if field not in self.df.columns:
                continue
                
            # Only analyze numeric fields
            if not pd.api.types.is_numeric_dtype(self.df[field]):
                continue
                
            series = self.df[field].dropna()
            
            if len(series) == 0:
                continue
            
            # Calculate outliers using IQR method
            q1, q3 = series.quantile([0.25, 0.75])
            iqr = q3 - q1
            outliers = series[(series < q1 - 1.5*iqr) | (series > q3 + 1.5*iqr)]
            
            # Calculate mode (most frequent value)
            mode_value = None
            if not series.mode().empty:
                mode_value = float(series.mode().iloc[0])
            
            summary = StatisticalSummary(
                field_name=field,
                count=len(series),
                mean=float(series.mean()) if len(series) > 0 else None,
                median=float(series.median()) if len(series) > 0 else None,
                mode=mode_value,
                std_dev=float(series.std()) if len(series) > 1 else None,
                std_error=float(series.std() / np.sqrt(len(series))) if len(series) > 1 else None,
                min_value=float(series.min()),
                max_value=float(series.max()),
                range_value=float(series.max() - series.min()),
                outliers_count=len(outliers),
                percentile_25=float(q1),
                percentile_75=float(q3)
            )
            summaries.append(summary)
        
        return summaries
    
    def _calculate_correlations(self, fields: List[str]) -> CorrelationAnalysis:
        """Calculate correlation analysis between specified fields"""
        # Filter to only numeric fields that exist in the DataFrame
        available_fields = [f for f in fields if f in self.df.columns and pd.api.types.is_numeric_dtype(self.df[f])]
        
        if len(available_fields) < 2:
            return CorrelationAnalysis(
                field_pairs=[],
                correlation_coefficients=[],
                p_values=[],
                significant_correlations=[]
            )
        
        numeric_df = self.df[available_fields].dropna()
        
        if len(numeric_df) < 3:  # Need at least 3 observations for meaningful correlation
            return CorrelationAnalysis(
                field_pairs=[],
                correlation_coefficients=[],
                p_values=[],
                significant_correlations=[]
            )
        
        corr_matrix = numeric_df.corr()
        
        # Extract unique pairs and their correlations
        field_pairs = []
        correlations = []
        p_values = []
        
        for i, field1 in enumerate(corr_matrix.columns):
            for j, field2 in enumerate(corr_matrix.columns):
                if i < j:  # Only upper triangle to avoid duplicates
                    field_pairs.append((field1, field2))
                    corr_val = corr_matrix.loc[field1, field2]
                    correlations.append(float(corr_val) if not pd.isna(corr_val) else 0.0)
                    
                    # Calculate p-value using scipy if available
                    try:
                        from scipy.stats import pearsonr
                        data1 = numeric_df[field1].dropna()
                        data2 = numeric_df[field2].dropna()
                        # Align the data
                        common_index = data1.index.intersection(data2.index)
                        if len(common_index) > 2:
                            _, p_val = pearsonr(data1.loc[common_index], data2.loc[common_index])
                            p_values.append(float(p_val))
                        else:
                            p_values.append(1.0)  # No correlation possible
                    except ImportError:
                        # If scipy not available, set p-value to 1.0 (no significance)
                        p_values.append(1.0)
        
        # Identify significant correlations (p < 0.05 and |r| > 0.3)
        significant = []
        for i, (pair, corr, p_val) in enumerate(zip(field_pairs, correlations, p_values)):
            if p_val < 0.05 and abs(corr) > 0.3:
                significant.append({
                    "fields": list(pair),
                    "correlation": corr,
                    "p_value": p_val,
                    "strength": self._interpret_correlation_strength(abs(corr))
                })
        
        return CorrelationAnalysis(
            field_pairs=field_pairs,
            correlation_coefficients=correlations,
            p_values=p_values,
            significant_correlations=significant
        )
    
    def _interpret_correlation_strength(self, abs_corr: float) -> str:
        """Interpret correlation strength"""
        if abs_corr >= 0.8:
            return "very strong"
        elif abs_corr >= 0.6:
            return "strong"
        elif abs_corr >= 0.4:
            return "moderate"
        elif abs_corr >= 0.2:
            return "weak"
        else:
            return "very weak"
    
    def _perform_regression(self, regression_spec: Dict[str, str]) -> Optional[RegressionAnalysis]:
        """Perform linear regression analysis"""
        dependent_var = regression_spec.get('dependent')
        independent_vars_str = regression_spec.get('independent', '')
        
        if not dependent_var or not independent_vars_str:
            return None
        
        independent_vars = [var.strip() for var in independent_vars_str.split(',')]
        
        # Check if variables exist and are numeric
        if dependent_var not in self.df.columns or not pd.api.types.is_numeric_dtype(self.df[dependent_var]):
            return None
        
        available_independent = [
            var for var in independent_vars 
            if var in self.df.columns and pd.api.types.is_numeric_dtype(self.df[var])
        ]
        
        if not available_independent:
            return None
        
        # Prepare data for regression
        regression_df = self.df[[dependent_var] + available_independent].dropna()
        
        if len(regression_df) < len(available_independent) + 2:  # Need more observations than variables
            return None
        
        y = regression_df[dependent_var]
        X = regression_df[available_independent]
        
        try:
            # Try using scikit-learn for regression
            from sklearn.linear_model import LinearRegression
            from sklearn.metrics import r2_score
            
            model = LinearRegression()
            model.fit(X, y)
            
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)
            
            # Calculate adjusted R²
            n = len(y)
            p = len(available_independent)
            adjusted_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n > p + 1 else r2
            
            # Build equation string
            equation_parts = [f"{dependent_var} = {model.intercept_:.3f}"]
            for var, coef in zip(available_independent, model.coef_):
                sign = "+" if coef >= 0 else ""
                equation_parts.append(f"{sign}{coef:.3f}*{var}")
            equation = " ".join(equation_parts)
            
            # Create coefficients dictionary
            coefficients = dict(zip(available_independent, model.coef_.tolist()))
            
            return RegressionAnalysis(
                dependent_variable=dependent_var,
                independent_variables=available_independent,
                r_squared=float(r2),
                adjusted_r_squared=float(adjusted_r2),
                coefficients=coefficients,
                p_values={},  # Would need statsmodels for p-values
                significant_predictors=[],  # Would need p-values to determine
                equation=equation
            )
            
        except ImportError:
            # If scikit-learn not available, try simple numpy implementation
            try:
                # Simple linear regression for single variable
                if len(available_independent) == 1:
                    x_vals = X.iloc[:, 0].values
                    y_vals = y.values
                    
                    # Calculate coefficients
                    x_mean = np.mean(x_vals)
                    y_mean = np.mean(y_vals)
                    
                    slope = np.sum((x_vals - x_mean) * (y_vals - y_mean)) / np.sum((x_vals - x_mean) ** 2)
                    intercept = y_mean - slope * x_mean
                    
                    # Calculate R²
                    y_pred = slope * x_vals + intercept
                    ss_res = np.sum((y_vals - y_pred) ** 2)
                    ss_tot = np.sum((y_vals - y_mean) ** 2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                    
                    equation = f"{dependent_var} = {intercept:.3f} + {slope:.3f}*{available_independent[0]}"
                    
                    return RegressionAnalysis(
                        dependent_variable=dependent_var,
                        independent_variables=available_independent,
                        r_squared=float(r2),
                        adjusted_r_squared=float(r2),  # Same as R² for single variable
                        coefficients={available_independent[0]: float(slope)},
                        p_values={},
                        significant_predictors=[],
                        equation=equation
                    )
                
                # For multiple variables, return None if scikit-learn not available
                return None
                
            except Exception:
                return None
        
        except Exception:
            return None
    
    def calculate_on_off_stats(self, on_court_df: pd.DataFrame, off_court_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate on/off court statistics comparison"""
        on_stats = {}
        off_stats = {}
        comparison = {}
        
        # Define key metrics to compare
        metrics = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers', 'field_goals_made', 'field_goals_attempted']
        
        for metric in metrics:
            if metric in on_court_df.columns:
                on_stats[metric] = {
                    'total': float(on_court_df[metric].sum()),
                    'average': float(on_court_df[metric].mean()),
                    'per_minute': float(on_court_df[metric].sum() / on_court_df.get('minutes', 1).sum()) if 'minutes' in on_court_df.columns else None
                }
            
            if metric in off_court_df.columns:
                off_stats[metric] = {
                    'total': float(off_court_df[metric].sum()),
                    'average': float(off_court_df[metric].mean()),
                    'per_minute': float(off_court_df[metric].sum() / off_court_df.get('minutes', 1).sum()) if 'minutes' in off_court_df.columns else None
                }
            
            # Calculate differences
            if metric in on_stats and metric in off_stats:
                comparison[f"{metric}_difference"] = on_stats[metric]['average'] - off_stats[metric]['average']
                if off_stats[metric]['average'] != 0:
                    comparison[f"{metric}_percent_change"] = ((on_stats[metric]['average'] - off_stats[metric]['average']) / off_stats[metric]['average']) * 100
        
        return {
            'on_court_stats': on_stats,
            'off_court_stats': off_stats,
            'comparison': comparison
        }