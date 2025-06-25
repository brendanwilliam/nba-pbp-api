"""
Player statistics endpoint router.
Handles queries for player performance data with advanced filtering and analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Union, Dict, Any
from datetime import date
import json

from ..models.query_params import PlayerStatsQuery
from ..models.responses import PlayerStatsResponse, StatisticalAnalysis
from ..services.query_builder import PlayerQueryBuilder
from ..services.stats_analyzer import StatsAnalyzer
from ..utils.database import get_db_manager, QueryExecutor, DatabaseManager

router = APIRouter()


@router.get("/player-stats", response_model=PlayerStatsResponse)
async def get_player_stats(
    # Player filters
    player_id: Optional[Union[int, List[int]]] = Query(None, description="Single player or list of players"),
    player_name: Optional[str] = Query(None, description="Player name (partial match supported)"),
    
    # Time filters
    season: Optional[str] = Query(None, description="'latest', '2023-24', '2022-23,2023-24', or 'all'"),
    game_id: Optional[str] = Query(None, description="'latest', specific game ID, comma-separated list, or 'all'"),
    date_from: Optional[date] = Query(None, description="Start date for filtering"),
    date_to: Optional[date] = Query(None, description="End date for filtering"),
    
    # Game context filters
    team_id: Optional[int] = Query(None, description="Team ID"),
    home_away: Optional[str] = Query(None, regex="^(home|away|all)$"),
    opponent_team_id: Optional[int] = Query(None),
    game_type: Optional[str] = Query(None, regex="^(regular|playoff|all)$"),
    
    # Statistical filters (JSON object)
    filters: Optional[str] = Query(None, description="JSON object with column filters, e.g., {'points': {'gte': 20}, 'assists': {'gte': 5}}"),
    
    # Output options
    fields: Optional[List[str]] = Query(None, description="Specific fields to return"),
    sort: Optional[str] = Query(None, description="Sort specification, e.g., '-points,assists'"),
    limit: int = Query(100, le=10000),
    offset: int = Query(0, ge=0),
    
    # Simple analysis flag
    include_summary: bool = Query(False, description="Include basic statistical summary"),
    
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Query player statistics with advanced filtering and analysis options.
    Starts from player_game_stats table and joins other tables as needed.
    """
    
    try:
        # Initialize query builder and executor
        query_builder = PlayerQueryBuilder()
        query_executor = QueryExecutor(db_manager)
        
        # Apply filters
        query_builder.add_season_filter(season)
        query_builder.add_game_filter(game_id)
        query_builder.add_date_filters(date_from, date_to)
        query_builder.add_player_filters(player_id, player_name)
        query_builder.add_team_filters(team_id, None, home_away, opponent_team_id)
        query_builder.add_game_type_filter(game_type)
        
        # Parse and apply dynamic filters
        if filters:
            try:
                filters_dict = json.loads(filters)
                query_builder.add_dynamic_filters(filters_dict)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format in filters parameter")
        
        # Determine fields to select
        default_fields = [
            "pgs.player_id", "p.player_name", "pgs.team_id", "t.full_name as team_name",
            "pgs.game_id", "eg.game_date", "eg.season",
            "pgs.points", "pgs.rebounds_total as rebounds", "pgs.assists", "pgs.steals", "pgs.blocks",
            "pgs.turnovers", "pgs.field_goals_made", "pgs.field_goals_attempted",
            "pgs.three_pointers_made as three_point_made", "pgs.three_pointers_attempted as three_point_attempted",
            "pgs.free_throws_made", "pgs.free_throws_attempted",
            "pgs.minutes_played as minutes", "pgs.plus_minus"
        ]
        
        select_fields = fields if fields else default_fields
        
        # Add sort clause
        sort_clause = query_builder.add_sort_clause(sort or "-points")
        
        # Build queries
        base_query, params = query_builder.build_query(select_fields)
        base_query += f" {sort_clause}"
        
        count_query, _ = query_builder.build_count_query()
        
        # Execute query with pagination
        result = await query_executor.execute_with_pagination(
            base_query, count_query, params, limit, offset
        )
        
        # Prepare response data
        query_info = {
            "filters_applied": {
                "player_id": player_id,
                "player_name": player_name,
                "season": season,
                "game_id": game_id,
                "date_range": {"from": date_from, "to": date_to} if date_from or date_to else None,
                "team_id": team_id,
                "home_away": home_away,
                "opponent_team_id": opponent_team_id,
                "game_type": game_type,
                "custom_filters": json.loads(filters) if filters else None
            },
            "pagination": {
                "limit": result["limit"],
                "offset": result["offset"],
                "has_next": result["has_next"],
                "has_prev": result["has_prev"]
            },
            "sort": sort
        }
        
        response_data = PlayerStatsResponse(
            data=result["data"],
            total_records=result["total_records"],
            query_info=query_info
        )
        
        # Perform basic statistical summary if requested
        if include_summary:
            # Execute query without pagination for analysis
            analysis_query = base_query.replace(f"LIMIT {limit} OFFSET {offset}", "")
            df = await query_executor.execute_for_analysis(analysis_query, params)
            
            # Determine fields for basic summary
            numeric_fields = [
                "points", "rebounds_total", "assists", "steals", "blocks", "turnovers",
                "field_goals_made", "field_goals_attempted", "three_pointers_made", 
                "three_pointers_attempted", "free_throws_made", "free_throws_attempted",
                "minutes_played", "plus_minus"
            ]
            
            # Perform basic statistical summary
            analyzer = StatsAnalyzer()
            statistical_analysis = analyzer.analyze_dataframe(
                df, numeric_fields, None, None
            )
            
            response_data.statistical_analysis = statistical_analysis
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing player stats query: {str(e)}")


@router.post("/player-stats/analyze", response_model=StatisticalAnalysis)
async def analyze_player_stats(
    # Player filters
    player_id: Optional[Union[int, List[int]]] = Query(None, description="Single player or list of players"),
    player_name: Optional[str] = Query(None, description="Player name (partial match supported)"),
    
    # Time filters
    season: Optional[str] = Query(None, description="'latest', '2023-24', '2022-23,2023-24', or 'all'"),
    game_id: Optional[str] = Query(None, description="'latest', specific game ID, comma-separated list, or 'all'"),
    date_from: Optional[date] = Query(None, description="Start date for filtering"),
    date_to: Optional[date] = Query(None, description="End date for filtering"),
    
    # Game context filters
    team_id: Optional[int] = Query(None, description="Team ID"),
    home_away: Optional[str] = Query(None, regex="^(home|away|all)$"),
    opponent_team_id: Optional[int] = Query(None),
    game_type: Optional[str] = Query(None, regex="^(regular|playoff|all)$"),
    
    # Statistical filters (JSON object)
    filters: Optional[str] = Query(None, description="JSON object with column filters"),
    
    # Advanced analysis options
    correlation: Optional[List[str]] = Query(None, description="Fields to calculate correlations for"),
    regression: Optional[str] = Query(None, description="Regression analysis specification as JSON"),
    include_summary: bool = Query(True, description="Include comprehensive statistical summary"),
    
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Perform advanced statistical analysis on player statistics.
    Supports correlation analysis, regression modeling, and comprehensive summaries.
    """
    
    try:
        # Initialize query builder and executor
        query_builder = PlayerQueryBuilder()
        query_executor = QueryExecutor(db_manager)
        
        # Apply filters (same as basic query)
        query_builder.add_season_filter(season)
        query_builder.add_game_filter(game_id)
        query_builder.add_date_filters(date_from, date_to)
        query_builder.add_player_filters(player_id, player_name)
        query_builder.add_team_filters(team_id, None, home_away, opponent_team_id)
        query_builder.add_game_type_filter(game_type)
        
        # Parse and apply dynamic filters
        if filters:
            try:
                filters_dict = json.loads(filters)
                query_builder.add_dynamic_filters(filters_dict)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format in filters parameter")
        
        # Build query for analysis
        default_fields = [
            "pgs.player_id", "p.player_name", "pgs.team_id", "t.full_name as team_name",
            "pgs.game_id", "eg.game_date", "eg.season",
            "pgs.points", "pgs.rebounds_total as rebounds", "pgs.assists", "pgs.steals", "pgs.blocks",
            "pgs.turnovers", "pgs.field_goals_made", "pgs.field_goals_attempted",
            "pgs.three_pointers_made as three_point_made", "pgs.three_pointers_attempted as three_point_attempted",
            "pgs.free_throws_made", "pgs.free_throws_attempted",
            "pgs.minutes_played as minutes", "pgs.plus_minus"
        ]
        
        base_query, params = query_builder.build_query(default_fields)
        
        # Execute query for analysis (no pagination for analysis)
        df = await query_executor.execute_for_analysis(base_query, params)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="No data found matching the specified criteria")
        
        # Parse regression specification
        regression_spec = None
        if regression:
            try:
                regression_spec = json.loads(regression)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format in regression parameter")
        
        # Determine fields for analysis
        numeric_fields = [
            "points", "rebounds_total", "assists", "steals", "blocks", "turnovers",
            "field_goals_made", "field_goals_attempted", "three_pointers_made", 
            "three_pointers_attempted", "free_throws_made", "free_throws_attempted",
            "minutes_played", "plus_minus"
        ] if include_summary else None
        
        # Perform comprehensive analysis
        analyzer = StatsAnalyzer()
        statistical_analysis = analyzer.analyze_dataframe(
            df, numeric_fields, correlation, regression_spec
        )
        
        return statistical_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing player stats analysis: {str(e)}")


@router.get("/players/{player_id}/stats")
async def get_player_stats_by_id(
    player_id: int,
    season: Optional[str] = Query("latest", description="Season to query"),
    game_type: Optional[str] = Query("all", description="Game type filter"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get statistics for a specific player"""
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        # Validate player exists
        player_exists = await query_executor.validate_player_exists(player_id)
        if not player_exists:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        
        # Get player info
        player_info = await query_executor.get_player_info(player_id)
        
        # Build query for player stats
        query = """
        SELECT 
            pgs.*, 
            p.player_name,
            t.full_name as team_name,
            t.tricode as team_abbreviation,
            eg.game_date,
            eg.home_team_id,
            eg.away_team_id
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN teams t ON pgs.team_id = t.team_id
        JOIN enhanced_games eg ON pgs.game_id = eg.game_id
        WHERE pgs.player_id = $1
        """
        
        params = [player_id]
        param_count = 1
        
        # Add season filter
        if season and season != "all":
            if season == "latest":
                latest_season = await query_executor.get_latest_season()
                if latest_season:
                    param_count += 1
                    query += f" AND eg.season = ${param_count}"
                    params.append(latest_season)
            else:
                param_count += 1
                query += f" AND eg.season = ${param_count}"
                params.append(season)
        
        # Add game type filter
        if game_type and game_type != "all":
            param_count += 1
            query += f" AND eg.game_type = ${param_count}"
            params.append(game_type)
        
        query += " ORDER BY eg.game_date DESC"
        
        # Count query
        count_query = query.replace("SELECT pgs.*, p.player_name, t.team_name, t.team_abbreviation, eg.game_date, eg.home_team_id, eg.away_team_id", "SELECT COUNT(*)")
        
        # Execute with pagination
        result = await query_executor.execute_with_pagination(
            query, count_query, params, limit, offset
        )
        
        return {
            "player_info": player_info,
            "stats": result["data"],
            "total_records": result["total_records"],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_next": result["has_next"],
                "has_prev": result["has_prev"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving player stats: {str(e)}")


@router.get("/players/search")
async def search_players(
    query: str = Query(..., min_length=2, description="Player name search query"),
    limit: int = Query(20, le=100),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Search for players by name"""
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        search_query = """
        SELECT id as player_id, player_name, first_name, last_name, team_id
        FROM players
        WHERE player_name ILIKE $1
           OR first_name ILIKE $1
           OR last_name ILIKE $1
        ORDER BY player_name
        LIMIT $2
        """
        
        search_term = f"%{query}%"
        results = await query_executor.db_manager.execute_query(search_query, search_term, limit)
        
        return {
            "query": query,
            "players": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching players: {str(e)}")