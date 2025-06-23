"""
Lineup statistics endpoint router.
Handles queries for lineup performance data with on/off court analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Union, Dict, Any
from datetime import date
import json

from ..models.query_params import LineupStatsQuery
from ..models.responses import LineupStatsResponse, StatisticalAnalysis
from ..services.query_builder import LineupQueryBuilder
from ..services.stats_analyzer import StatsAnalyzer
from ..utils.database import get_db_manager, QueryExecutor, DatabaseManager

router = APIRouter()


@router.post("/lineup-stats", response_model=Union[LineupStatsResponse, StatisticalAnalysis])
async def query_lineup_stats(
    # Lineup composition filters
    player_ids: Optional[List[int]] = Query(None, description="Players that must be in the lineup"),
    exclude_player_ids: Optional[List[int]] = Query(None, description="Players that must NOT be in the lineup"),
    lineup_size: Optional[int] = Query(None, ge=1, le=5, description="Number of players in lineup"),
    
    # Team and time filters
    team_id: Optional[int] = Query(None),
    season: Optional[str] = Query(None, description="'latest', '2023-24', or 'all'"),
    game_id: Optional[str] = Query(None, description="'latest', specific game ID, or 'all'"),
    date_from: Optional[date] = Query(None, description="Start date for filtering"),
    date_to: Optional[date] = Query(None, description="End date for filtering"),
    
    # Performance filters
    min_minutes: Optional[float] = Query(None, description="Minimum minutes played together"),
    filters: Optional[str] = Query(None, description="JSON object with column filters"),
    
    # On/Off analysis
    compare_mode: Optional[str] = Query(None, regex="^(on|off|both)$", description="Compare when lineup is on vs off court"),
    
    # Output options
    fields: Optional[List[str]] = Query(None, description="Specific fields to return"),
    sort: Optional[str] = Query(None, description="Sort specification"),
    limit: int = Query(100, le=10000),
    offset: int = Query(0, ge=0),
    
    # Analysis flags
    about: bool = Query(False, description="Include statistical summary"),
    correlation: Optional[List[str]] = Query(None, description="Fields to calculate correlations for"),
    regression: Optional[str] = Query(None, description="Regression analysis specification as JSON"),
    
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """
    Query lineup statistics and on/off numbers.
    Starts from lineup_states table and aggregates performance metrics.
    """
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        # For this implementation, we'll use a simplified approach
        # In a real implementation, this would query the lineup_states table
        # For now, we'll aggregate from player_game_stats based on lineup composition
        
        # Validate player IDs if provided
        if player_ids:
            for player_id in player_ids:
                player_exists = await query_executor.validate_player_exists(player_id)
                if not player_exists:
                    raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        
        # Build a query to find games where specified players played together
        if player_ids and len(player_ids) >= 2:
            # Complex query to find lineups containing specified players
            lineup_query = """
            WITH lineup_games AS (
                SELECT 
                    pgs.game_id,
                    pgs.team_id,
                    eg.game_date,
                    eg.season,
                    ARRAY_AGG(pgs.player_id ORDER BY pgs.player_id) as lineup_players,
                    SUM(pgs.points) as total_points,
                    SUM(pgs.rebounds) as total_rebounds,
                    SUM(pgs.assists) as total_assists,
                    SUM(pgs.steals) as total_steals,
                    SUM(pgs.blocks) as total_blocks,
                    SUM(pgs.turnovers) as total_turnovers,
                    AVG(pgs.plus_minus) as avg_plus_minus,
                    COUNT(*) as players_in_lineup
                FROM player_game_stats pgs
                JOIN enhanced_games eg ON pgs.game_id = eg.game_id
                WHERE pgs.minutes > 0
            """
            
            params = []
            param_count = 0
            
            # Add team filter
            if team_id:
                param_count += 1
                lineup_query += f" AND pgs.team_id = ${param_count}"
                params.append(team_id)
            
            # Add season filter
            if season and season != "all":
                if season == "latest":
                    latest_season = await query_executor.get_latest_season()
                    if latest_season:
                        param_count += 1
                        lineup_query += f" AND eg.season = ${param_count}"
                        params.append(latest_season)
                else:
                    param_count += 1
                    lineup_query += f" AND eg.season = ${param_count}"
                    params.append(season)
            
            # Add date filters
            if date_from:
                param_count += 1
                lineup_query += f" AND eg.game_date >= ${param_count}"
                params.append(date_from)
                
            if date_to:
                param_count += 1
                lineup_query += f" AND eg.game_date <= ${param_count}"
                params.append(date_to)
            
            lineup_query += """
                GROUP BY pgs.game_id, pgs.team_id, eg.game_date, eg.season
            )
            SELECT 
                lg.*,
                t.team_name,
                t.team_abbreviation
            FROM lineup_games lg
            JOIN teams t ON lg.team_id = t.team_id
            WHERE 1=1
            """
            
            # Filter for lineups containing specified players
            for player_id in player_ids:
                param_count += 1
                lineup_query += f" AND ${param_count} = ANY(lg.lineup_players)"
                params.append(player_id)
            
            # Filter for lineup size if specified
            if lineup_size:
                param_count += 1
                lineup_query += f" AND lg.players_in_lineup = ${param_count}"
                params.append(lineup_size)
            
            # Add sorting
            sort_clause = " ORDER BY lg.game_date DESC"
            if sort:
                # Parse sort parameter and apply
                sort_fields = []
                for field in sort.split(","):
                    field = field.strip()
                    if field.startswith("-"):
                        sort_fields.append(f"lg.{field[1:]} DESC")
                    else:
                        sort_fields.append(f"lg.{field} ASC")
                sort_clause = f" ORDER BY {', '.join(sort_fields)}"
            
            lineup_query += sort_clause
            
            # Execute query with pagination
            paginated_query = f"{lineup_query} LIMIT {limit} OFFSET {offset}"
            count_query = lineup_query.replace("SELECT lg.*, t.team_name, t.team_abbreviation", "SELECT COUNT(*)")
            
            data = await query_executor.db_manager.execute_query(paginated_query, *params)
            total_count = await query_executor.db_manager.execute_count_query(count_query, *params)
            
        else:
            # If no specific players specified, return general lineup statistics
            # This would typically query the lineup_states table
            raise HTTPException(
                status_code=400, 
                detail="At least 2 player IDs must be specified for lineup analysis"
            )
        
        # Calculate on/off court statistics if requested
        on_court_stats = None
        off_court_stats = None
        comparison = None
        
        if compare_mode in ["on", "both"] and data:
            # Calculate stats when this lineup is on court
            on_court_stats = {
                "total_games": len(data),
                "avg_points": sum(row['total_points'] for row in data) / len(data),
                "avg_rebounds": sum(row['total_rebounds'] for row in data) / len(data),
                "avg_assists": sum(row['total_assists'] for row in data) / len(data),
                "avg_plus_minus": sum(row['avg_plus_minus'] for row in data) / len(data)
            }
        
        if compare_mode in ["off", "both"] and team_id and player_ids:
            # Calculate stats when these players are NOT all on court together
            # This is a complex calculation that would require detailed lineup tracking
            # For now, provide a placeholder
            off_court_stats = {
                "note": "Off-court statistics require detailed lineup tracking data",
                "implementation": "This would calculate team performance when specified players are not all on court"
            }
        
        if compare_mode == "both" and on_court_stats and off_court_stats:
            comparison = {
                "points_difference": "Would show difference in scoring when lineup is on vs off",
                "plus_minus_difference": "Would show plus/minus difference"
            }
        
        # Prepare query info
        query_info = {
            "filters_applied": {
                "player_ids": player_ids,
                "exclude_player_ids": exclude_player_ids,
                "lineup_size": lineup_size,
                "team_id": team_id,
                "season": season,
                "date_range": {"from": date_from, "to": date_to} if date_from or date_to else None,
                "min_minutes": min_minutes,
                "compare_mode": compare_mode
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_next": offset + limit < total_count,
                "has_prev": offset > 0
            },
            "sort": sort
        }
        
        response_data = LineupStatsResponse(
            data=data,
            total_records=total_count,
            on_court_stats=on_court_stats,
            off_court_stats=off_court_stats,
            comparison=comparison
        )
        
        # Perform statistical analysis if requested
        if about or correlation or regression:
            # Convert data to DataFrame for analysis
            import pandas as pd
            df = pd.DataFrame(data)
            
            # Parse regression specification
            regression_spec = None
            if regression:
                try:
                    regression_spec = json.loads(regression)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON format in regression parameter")
            
            # Determine fields for analysis
            numeric_fields = [
                "total_points", "total_rebounds", "total_assists", "total_steals", 
                "total_blocks", "total_turnovers", "avg_plus_minus", "players_in_lineup"
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing lineup stats query: {str(e)}")


@router.get("/lineups/common/{team_id}")
async def get_common_lineups(
    team_id: int,
    season: Optional[str] = Query("latest", description="Season to analyze"),
    min_games: int = Query(5, description="Minimum games played together"),
    lineup_size: int = Query(5, description="Number of players in lineup"),
    limit: int = Query(20, le=100),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Get most common lineups for a team"""
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        # Validate team exists
        team_exists = await query_executor.validate_team_exists(team_id)
        if not team_exists:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")
        
        team_info = await query_executor.get_team_info(team_id)
        
        # Query for common lineups
        # This is a simplified version - in reality would use lineup_states table
        query = """
        WITH game_lineups AS (
            SELECT 
                pgs.game_id,
                ARRAY_AGG(pgs.player_id ORDER BY pgs.player_id) as lineup_players,
                ARRAY_AGG(p.player_name ORDER BY pgs.player_id) as lineup_names,
                SUM(pgs.points) as total_points,
                AVG(pgs.plus_minus) as avg_plus_minus
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.player_id
            JOIN enhanced_games eg ON pgs.game_id = eg.game_id
            WHERE pgs.team_id = $1
              AND pgs.minutes > 0
        """
        
        params = [team_id]
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
        
        query += f"""
            GROUP BY pgs.game_id
            HAVING COUNT(*) = {lineup_size}
        ),
        lineup_frequency AS (
            SELECT 
                lineup_players,
                lineup_names,
                COUNT(*) as games_played,
                AVG(total_points) as avg_points_per_game,
                AVG(avg_plus_minus) as avg_plus_minus
            FROM game_lineups
            GROUP BY lineup_players, lineup_names
            HAVING COUNT(*) >= {min_games}
        )
        SELECT *
        FROM lineup_frequency
        ORDER BY games_played DESC, avg_plus_minus DESC
        LIMIT {limit}
        """
        
        results = await query_executor.db_manager.execute_query(query, *params)
        
        return {
            "team_info": team_info,
            "common_lineups": results,
            "filters": {
                "season": season,
                "min_games": min_games,
                "lineup_size": lineup_size
            },
            "total_found": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving common lineups: {str(e)}")


@router.get("/lineups/player-combinations")
async def get_player_combinations(
    player_ids: List[int] = Query(..., description="List of player IDs to analyze"),
    team_id: Optional[int] = Query(None, description="Filter by team"),
    season: Optional[str] = Query("latest", description="Season to analyze"),
    min_minutes: float = Query(10.0, description="Minimum minutes played together"),
    db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Analyze how well specific players perform together"""
    
    try:
        query_executor = QueryExecutor(db_manager)
        
        if len(player_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 player IDs required for combination analysis")
        
        # Validate all players exist
        for player_id in player_ids:
            player_exists = await query_executor.validate_player_exists(player_id)
            if not player_exists:
                raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        
        # Get player info
        player_info = []
        for player_id in player_ids:
            info = await query_executor.get_player_info(player_id)
            if info:
                player_info.append(info)
        
        # Query for games where these players played together
        query = """
        WITH player_game_minutes AS (
            SELECT 
                pgs.game_id,
                pgs.team_id,
                pgs.player_id,
                pgs.minutes,
                pgs.plus_minus,
                eg.game_date,
                eg.season
            FROM player_game_stats pgs
            JOIN enhanced_games eg ON pgs.game_id = eg.game_id
            WHERE pgs.player_id = ANY($1)
              AND pgs.minutes >= $2
        """
        
        params = [player_ids, min_minutes]
        param_count = 2
        
        # Add team filter
        if team_id:
            param_count += 1
            query += f" AND pgs.team_id = ${param_count}"
            params.append(team_id)
        
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
        
        query += """
        ),
        games_together AS (
            SELECT 
                game_id,
                team_id,
                game_date,
                season,
                COUNT(*) as players_present,
                AVG(minutes) as avg_minutes,
                AVG(plus_minus) as avg_plus_minus
            FROM player_game_minutes
            GROUP BY game_id, team_id, game_date, season
            HAVING COUNT(*) = $1
        )
        SELECT *
        FROM games_together
        ORDER BY game_date DESC
        """
        
        # Update the first parameter to be the count of players
        params[0] = len(player_ids)
        
        results = await query_executor.db_manager.execute_query(query, *params)
        
        # Calculate summary statistics
        total_games = len(results)
        avg_plus_minus = sum(game['avg_plus_minus'] for game in results) / total_games if total_games > 0 else 0
        avg_minutes = sum(game['avg_minutes'] for game in results) / total_games if total_games > 0 else 0
        
        summary = {
            "total_games_together": total_games,
            "average_plus_minus": round(avg_plus_minus, 2),
            "average_minutes": round(avg_minutes, 1)
        }
        
        return {
            "player_info": player_info,
            "summary": summary,
            "games_together": results,
            "filters": {
                "team_id": team_id,
                "season": season,
                "min_minutes": min_minutes
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing player combinations: {str(e)}")