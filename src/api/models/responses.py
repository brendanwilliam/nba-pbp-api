"""
Response models for API endpoints.
Defines the structure of API responses including data and statistical analysis.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple


class StatisticalSummary(BaseModel):
    """Statistical summary for a single field"""
    field_name: str
    count: int
    mean: Optional[float] = None
    median: Optional[float] = None
    mode: Optional[float] = None
    std_dev: Optional[float] = None
    std_error: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    range_value: Optional[float] = None
    outliers_count: int = 0
    percentile_25: Optional[float] = None
    percentile_75: Optional[float] = None


class CorrelationAnalysis(BaseModel):
    """Correlation analysis results"""
    field_pairs: List[Tuple[str, str]]
    correlation_coefficients: List[float]
    p_values: List[float]
    significant_correlations: List[Dict[str, Any]]


class RegressionAnalysis(BaseModel):
    """Regression analysis results"""
    dependent_variable: str
    independent_variables: List[str]
    r_squared: float
    adjusted_r_squared: float
    coefficients: Dict[str, float]
    p_values: Dict[str, float]
    significant_predictors: List[str]
    equation: str


class StatisticalAnalysis(BaseModel):
    """Complete statistical analysis package"""
    data: List[Dict[str, Any]]
    summary_stats: Optional[List[StatisticalSummary]] = None
    correlation_analysis: Optional[CorrelationAnalysis] = None
    regression_analysis: Optional[RegressionAnalysis] = None
    total_records: int
    query_metadata: Dict[str, Any]


class PlayerStatsResponse(BaseModel):
    """Response model for player statistics endpoint"""
    data: List[Dict[str, Any]]
    total_records: int
    query_info: Dict[str, Any]
    statistical_analysis: Optional[StatisticalAnalysis] = None


class TeamStatsResponse(BaseModel):
    """Response model for team statistics endpoint"""
    data: List[Dict[str, Any]]
    total_records: int
    query_info: Dict[str, Any]
    statistical_analysis: Optional[StatisticalAnalysis] = None


class LineupStatsResponse(BaseModel):
    """Response model for lineup statistics endpoint"""
    data: List[Dict[str, Any]]
    total_records: int
    on_court_stats: Optional[Dict[str, Any]] = None
    off_court_stats: Optional[Dict[str, Any]] = None
    comparison: Optional[Dict[str, Any]] = None
    statistical_analysis: Optional[StatisticalAnalysis] = None


class ShotChartResponse(BaseModel):
    """Response model for shot chart endpoint"""
    shots: List[Dict[str, Any]]  # x, y, distance, made, shot_type, etc.
    total_shots: int
    made_shots: int
    shooting_percentage: float
    zones: Dict[str, Dict[str, Any]]  # Shooting stats by zone
    heat_map_data: Optional[List[Dict[str, Any]]] = None


class PlayByPlayResponse(BaseModel):
    """Response model for play-by-play endpoint"""
    plays: List[Dict[str, Any]]
    total_plays: int
    game_context: Optional[Dict[str, Any]] = None
    lineup_data: Optional[List[Dict[str, Any]]] = None
    statistical_analysis: Optional[StatisticalAnalysis] = None


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    detail: Optional[str] = None
    timestamp: str
    request_id: Optional[str] = None