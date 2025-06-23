"""
Team statistics endpoint router.
Handles queries for team performance data with win/loss analysis and advanced filtering.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Union, Dict, Any
from datetime import date
import json

from ..models.query_params import TeamStatsQuery
from ..models.responses import TeamStatsResponse, StatisticalAnalysis
from ..services.query_builder import TeamQueryBuilder
from ..services.stats_analyzer import StatsAnalyzer
from ..utils.database import get_db_manager, QueryExecutor, DatabaseManager

router = APIRouter()


@router.post("/team-stats", response_model=Union[TeamStatsResponse, StatisticalAnalysis])
async def query_team_stats(
    # Team filters
    team_id: Optional[Union[int, List[int]]] = Query(None, description="Single team or list of teams"),
    team_name: Optional[str] = Query(None, description="Team name or abbreviation"),
    
    # Time filters
    season: Optional[str] = Query(None, description="'latest', '2023-24', '2022-23,2023-24', or 'all'"),
    game_id: Optional[str] = Query(None, description="'latest', specific game ID, comma-separated list, or 'all'"),
    date_from: Optional[date] = Query(None, description="Start date for filtering"),
    date_to: Optional[date] = Query(None, description="End date for filtering"),
    
    # Game context filters
    home_away: Optional[str] = Query(None, regex="^(home|away|all)$"),
    opponent_team_id: Optional[int] = Query(None),
    game_type: Optional[str] = Query(None, regex="^(regular|playoff|all)$"),
    win_loss: Optional[str] = Query(None, regex="^(win|loss|all)$"),
    
    # Statistical filters
    filters: Optional[str] = Query(None, description="JSON object with column filters"),
    
    # Output options
    fields: Optional[List[str]] = Query(None, description="Specific fields to return"),
    sort: Optional[str] = Query(None, description="Sort specification, e.g., '-points,rebounds'"),
    limit: int = Query(100, le=10000),
    offset: int = Query(0, ge=0),
    
    # Analysis flags
    about: bool = Query(False, description="Include statistical summary"),
    correlation: Optional[List[str]] = Query(None, description="Fields to calculate correlations for"),
    regression: Optional[str] = Query(None, description="Regression analysis specification as JSON"),
    
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Query team statistics with advanced filtering and analysis options.
    Starts from team_game_stats table and joins other tables as needed.
    """
    
    try:
        # Initialize query builder and executor
        query_builder = TeamQueryBuilder()
        query_executor = QueryExecutor(db_manager)
        
        # Apply filters
        query_builder.add_season_filter(season)
        query_builder.add_game_filter(game_id)
        query_builder.add_date_filters(date_from, date_to)
        query_builder.add_team_filters(team_id, team_name, home_away, opponent_team_id)
        query_builder.add_game_type_filter(game_type)
        query_builder.add_win_loss_filter(win_loss)
        
        # Parse and apply dynamic filters
        if filters:
            try:
                filters_dict = json.loads(filters)
                query_builder.add_dynamic_filters(filters_dict)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format in filters parameter")
        
        # Determine fields to select
        default_fields = [
            "tgs.team_id", "t.team_name", "t.team_abbreviation",
            "tgs.game_id", "eg.game_date", "tgs.season",
            "tgs.points", "tgs.rebounds", "tgs.assists", "tgs.steals", "tgs.blocks",
            "tgs.turnovers", "tgs.field_goals_made", "tgs.field_goals_attempted",
            "tgs.three_point_made", "tgs.three_point_attempted",
            "tgs.free_throws_made", "tgs.free_throws_attempted",
            "tgs.home_away", "tgs.win_loss", "tgs.plus_minus"
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
                "team_id": team_id,
                "team_name": team_name,
                "season": season,
                "game_id": game_id,
                "date_range": {"from": date_from, "to": date_to} if date_from or date_to else None,
                "home_away": home_away,
                "opponent_team_id": opponent_team_id,
                "game_type": game_type,
                "win_loss": win_loss,
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
        
        response_data = TeamStatsResponse(
            data=result["data"],
            total_records=result["total_records"],
            query_info=query_info
        )
        
        # Perform statistical analysis if requested
        if about or correlation or regression:
            # Execute query without pagination for analysis
            analysis_query = base_query.replace(f"LIMIT {limit} OFFSET {offset}", "")
            df = await query_executor.execute_for_analysis(analysis_query, params)
            
            # Parse regression specification
            regression_spec = None
            if regression:
                try:
                    regression_spec = json.loads(regression)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON format in regression parameter")
            
            # Determine fields for analysis
            numeric_fields = [
                "points", "rebounds", "assists", "steals", "blocks", "turnovers",
                "field_goals_made", "field_goals_attempted", "three_point_made", 
                "three_point_attempted", "free_throws_made", "free_throws_attempted",
                "plus_minus"
            ]
            
            about_fields = numeric_fields if about else None
            
            # Perform analysis
            analyzer = StatsAnalyzer()
            statistical_analysis = analyzer.analyze_dataframe(
                df, about_fields, correlation, regression_spec
            )
            
            response_data.statistical_analysis = statistical_analysis
            
            # Return statistical analysis if that's the primary request
            if about or correlation or regression:
                return statistical_analysis
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing team stats query: {str(e)}")


@router.get("/teams/{team_id}/stats")
async def get_team_stats_by_id(
    team_id: int,
    season: Optional[str] = Query("latest", description="Season to query"),
    game_type: Optional[str] = Query("all", description="Game type filter"),
    home_away: Optional[str] = Query("all", description="Home/away filter"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get statistics for a specific team"""
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        # Validate team exists
        team_exists = await query_executor.validate_team_exists(team_id)
        if not team_exists:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")
        
        # Get team info
        team_info = await query_executor.get_team_info(team_id)
        
        # Build query for team stats
        query = """
        SELECT 
            tgs.*, 
            t.team_name,
            t.team_abbreviation,
            eg.game_date,
            eg.home_team_id,
            eg.away_team_id,
            ot.team_name as opponent_name
        FROM team_game_stats tgs
        JOIN teams t ON tgs.team_id = t.team_id
        JOIN enhanced_games eg ON tgs.game_id = eg.game_id
        LEFT JOIN teams ot ON tgs.opponent_team_id = ot.team_id
        WHERE tgs.team_id = $1
        """
        
        params = [team_id]
        param_count = 1
        
        # Add season filter
        if season and season != "all":
            if season == "latest":
                latest_season = await query_executor.get_latest_season()
                if latest_season:
                    param_count += 1
                    query += f" AND tgs.season = ${param_count}"
                    params.append(latest_season)
            else:
                param_count += 1
                query += f" AND tgs.season = ${param_count}"
                params.append(season)
        
        # Add game type filter
        if game_type and game_type != "all":
            param_count += 1
            query += f" AND eg.game_type = ${param_count}"
            params.append(game_type)
        
        # Add home/away filter
        if home_away and home_away != "all":
            param_count += 1
            query += f" AND tgs.home_away = ${param_count}"
            params.append(home_away)
        
        query += " ORDER BY eg.game_date DESC"
        
        # Count query
        count_query = query.replace(
            "SELECT tgs.*, t.team_name, t.team_abbreviation, eg.game_date, eg.home_team_id, eg.away_team_id, ot.team_name as opponent_name", 
            "SELECT COUNT(*)"
        )
        
        # Execute with pagination
        result = await query_executor.execute_with_pagination(
            query, count_query, params, limit, offset
        )
        
        # Calculate season averages if we have data
        season_averages = None
        if result["data"]:
            # Query for season averages
            avg_query = """
            SELECT 
                AVG(points) as avg_points,
                AVG(rebounds) as avg_rebounds,
                AVG(assists) as avg_assists,
                AVG(steals) as avg_steals,
                AVG(blocks) as avg_blocks,
                AVG(turnovers) as avg_turnovers,
                AVG(field_goals_made) as avg_fg_made,
                AVG(field_goals_attempted) as avg_fg_attempted,
                AVG(three_point_made) as avg_3pt_made,
                AVG(three_point_attempted) as avg_3pt_attempted,
                AVG(free_throws_made) as avg_ft_made,
                AVG(free_throws_attempted) as avg_ft_attempted,
                COUNT(*) as games_played,
                SUM(CASE WHEN win_loss = 'W' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN win_loss = 'L' THEN 1 ELSE 0 END) as losses
            FROM team_game_stats tgs
            JOIN enhanced_games eg ON tgs.game_id = eg.game_id
            WHERE tgs.team_id = $1
            """
            
            avg_params = [team_id]
            avg_param_count = 1
            
            # Add same filters to averages query
            if season and season != "all":
                if season == "latest":
                    latest_season = await query_executor.get_latest_season()
                    if latest_season:
                        avg_param_count += 1
                        avg_query += f" AND tgs.season = ${avg_param_count}"
                        avg_params.append(latest_season)
                else:
                    avg_param_count += 1
                    avg_query += f" AND tgs.season = ${avg_param_count}"
                    avg_params.append(season)
            
            if game_type and game_type != "all":
                avg_param_count += 1
                avg_query += f" AND eg.game_type = ${avg_param_count}"
                avg_params.append(game_type)
            
            if home_away and home_away != "all":
                avg_param_count += 1
                avg_query += f" AND tgs.home_away = ${avg_param_count}"
                avg_params.append(home_away)
            
            avg_results = await query_executor.db_manager.execute_query(avg_query, *avg_params)
            if avg_results:
                season_averages = avg_results[0]
        
        return {
            "team_info": team_info,
            "stats": result["data"],
            "season_averages": season_averages,
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
        raise HTTPException(status_code=500, detail=f"Error retrieving team stats: {str(e)}")


@router.get("/teams/search")
async def search_teams(
    query: str = Query(..., min_length=1, description="Team name or abbreviation search query"),
    limit: int = Query(30, le=50),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Search for teams by name or abbreviation"""
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        search_query = """
        SELECT team_id, team_name, team_abbreviation, team_city
        FROM teams
        WHERE team_name ILIKE $1
           OR team_abbreviation ILIKE $1
           OR team_city ILIKE $1
        ORDER BY team_name
        LIMIT $2
        """
        
        search_term = f"%{query}%"
        results = await query_executor.db_manager.execute_query(search_query, search_term, limit)
        
        return {
            "query": query,
            "teams": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching teams: {str(e)}")


@router.get("/teams/{team_id}/head-to-head/{opponent_team_id}")
async def get_head_to_head_stats(
    team_id: int,
    opponent_team_id: int,
    season: Optional[str] = Query("all", description="Season to analyze"),
    game_type: Optional[str] = Query("all", description="Game type filter"),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get head-to-head statistics between two teams"""
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        # Validate both teams exist
        team1_exists = await query_executor.validate_team_exists(team_id)
        team2_exists = await query_executor.validate_team_exists(opponent_team_id)
        
        if not team1_exists:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")
        if not team2_exists:
            raise HTTPException(status_code=404, detail=f"Team with ID {opponent_team_id} not found")
        
        # Get team info
        team1_info = await query_executor.get_team_info(team_id)
        team2_info = await query_executor.get_team_info(opponent_team_id)
        
        # Build head-to-head query
        query = """
        SELECT 
            tgs1.team_id,
            tgs1.points as team1_points,
            tgs2.points as team2_points,
            tgs1.win_loss as team1_result,
            tgs2.win_loss as team2_result,
            eg.game_date,
            eg.season,
            tgs1.home_away as team1_home_away,
            eg.game_id
        FROM team_game_stats tgs1
        JOIN team_game_stats tgs2 ON tgs1.game_id = tgs2.game_id
        JOIN enhanced_games eg ON tgs1.game_id = eg.game_id
        WHERE tgs1.team_id = $1 
          AND tgs2.team_id = $2
        """
        
        params = [team_id, opponent_team_id]
        param_count = 2
        
        # Add season filter
        if season and season != "all":
            param_count += 1
            query += f" AND eg.season = ${param_count}"
            params.append(season)
        
        # Add game type filter
        if game_type and game_type != "all":
            param_count += 1
            query += f" AND eg.game_type = ${param_count}"
            params.append(game_type)
        
        query += " ORDER BY eg.game_date DESC"
        
        games = await query_executor.db_manager.execute_query(query, *params)
        
        # Calculate summary statistics
        total_games = len(games)
        team1_wins = sum(1 for game in games if game['team1_result'] == 'W')
        team2_wins = total_games - team1_wins
        
        # Calculate average scores
        avg_team1_points = sum(game['team1_points'] for game in games) / total_games if total_games > 0 else 0
        avg_team2_points = sum(game['team2_points'] for game in games) / total_games if total_games > 0 else 0
        
        summary = {
            "total_games": total_games,
            "team1_record": {"wins": team1_wins, "losses": team2_wins},
            "team2_record": {"wins": team2_wins, "losses": team1_wins},
            "avg_scores": {
                "team1": round(avg_team1_points, 1),
                "team2": round(avg_team2_points, 1)
            }
        }
        
        return {
            "team1_info": team1_info,
            "team2_info": team2_info,
            "summary": summary,
            "games": games,
            "filters": {
                "season": season,
                "game_type": game_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving head-to-head stats: {str(e)}")