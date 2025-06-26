"""
Query Processor for NBA MCP Server

Processes structured query contexts and generates appropriate database queries.
"""

import sys
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.query_builder import QueryBuilder, PlayerQueryBuilder, TeamQueryBuilder
from .query_translator import QueryContext, QueryType, ExtractedEntity


@dataclass
class ProcessedQuery:
    sql: str
    params: List[Any]
    query_type: str
    description: str
    entities_used: List[str]


class NBAQueryProcessor:
    """Processes structured query contexts into database queries."""
    
    def __init__(self):
        self.query_builder = QueryBuilder("player_game_stats pgs")
        self.player_query_builder = PlayerQueryBuilder()
        self.team_query_builder = TeamQueryBuilder()
    
    async def process_query_context(self, context: QueryContext) -> ProcessedQuery:
        """Process a query context into a database query."""
        
        if context.query_type == QueryType.PLAYER_STATS:
            return await self._process_player_stats_query(context)
        elif context.query_type == QueryType.PLAYER_COMPARISON:
            return await self._process_player_comparison_query(context)
        elif context.query_type == QueryType.TEAM_STATS:
            return await self._process_team_stats_query(context)
        elif context.query_type == QueryType.GAME_ANALYSIS:
            return await self._process_game_analysis_query(context)
        elif context.query_type == QueryType.HISTORICAL_QUERY:
            return await self._process_historical_query(context)
        else:
            return await self._process_fallback_query(context)
    
    async def _process_player_stats_query(self, context: QueryContext) -> ProcessedQuery:
        """Process player statistics queries."""
        # Extract player entity
        player_entities = [e for e in context.entities if e.entity_type == "player"]
        if not player_entities:
            raise ValueError("No player found in query")
        
        player_name = player_entities[0].value
        
        # Extract statistical categories
        stat_entities = [e for e in context.entities if e.entity_type == "statistic"]
        requested_stats = [e.value for e in stat_entities] if stat_entities else None
        
        # Build query based on intent
        if context.intent == "career_stats":
            sql, params = await self._build_career_stats_query(player_name, requested_stats)
            description = f"Career statistics for {player_name}"
        elif context.intent == "season_stats" and context.season:
            sql, params = await self._build_season_stats_query(player_name, context.season, requested_stats)
            description = f"{context.season} season statistics for {player_name}"
        else:
            sql, params = await self._build_basic_player_stats_query(player_name, context.season, requested_stats)
            description = f"Statistics for {player_name}" + (f" ({context.season})" if context.season else "")
        
        return ProcessedQuery(
            sql=sql,
            params=params,
            query_type="player_stats",
            description=description,
            entities_used=[player_name]
        )
    
    async def _process_player_comparison_query(self, context: QueryContext) -> ProcessedQuery:
        """Process player comparison queries."""
        player_entities = [e for e in context.entities if e.entity_type == "player"]
        if len(player_entities) < 2:
            raise ValueError("Need at least 2 players for comparison")
        
        players = [e.value for e in player_entities]
        stat_entities = [e for e in context.entities if e.entity_type == "statistic"]
        requested_stats = [e.value for e in stat_entities] if stat_entities else None
        
        sql, params = await self._build_player_comparison_query(players, context.season, requested_stats)
        description = f"Comparison between {' vs '.join(players)}"
        
        return ProcessedQuery(
            sql=sql,
            params=params,
            query_type="player_comparison",
            description=description,
            entities_used=players
        )
    
    async def _process_team_stats_query(self, context: QueryContext) -> ProcessedQuery:
        """Process team statistics queries."""
        team_entities = [e for e in context.entities if e.entity_type == "team"]
        if not team_entities:
            raise ValueError("No team found in query")
        
        team_name = team_entities[0].value
        
        if context.intent == "team_record":
            sql, params = await self._build_team_record_query(team_name, context.season)
            description = f"Record for {team_name}"
        elif context.intent == "team_performance":
            sql, params = await self._build_team_performance_query(team_name, context.season)
            description = f"Performance statistics for {team_name}"
        else:
            sql, params = await self._build_basic_team_stats_query(team_name, context.season)
            description = f"Statistics for {team_name}"
        
        return ProcessedQuery(
            sql=sql,
            params=params,
            query_type="team_stats",
            description=description,
            entities_used=[team_name]
        )
    
    async def _process_game_analysis_query(self, context: QueryContext) -> ProcessedQuery:
        """Process game analysis queries."""
        # Look for game ID in the query (would need to be extracted)
        # For now, use a placeholder approach
        
        # Extract team entities for game lookup
        team_entities = [e for e in context.entities if e.entity_type == "team"]
        
        if len(team_entities) >= 2:
            # Game between two teams
            home_team = team_entities[0].value
            away_team = team_entities[1].value
            sql, params = await self._build_team_matchup_query(home_team, away_team, context.season)
            description = f"Games between {away_team} and {home_team}"
        else:
            # Generic game analysis
            sql, params = await self._build_recent_games_query(context.season)
            description = "Recent game analysis"
        
        return ProcessedQuery(
            sql=sql,
            params=params,
            query_type="game_analysis",
            description=description,
            entities_used=[e.value for e in team_entities]
        )
    
    async def _process_historical_query(self, context: QueryContext) -> ProcessedQuery:
        """Process historical/record queries."""
        player_entities = [e for e in context.entities if e.entity_type == "player"]
        team_entities = [e for e in context.entities if e.entity_type == "team"]
        stat_entities = [e for e in context.entities if e.entity_type == "statistic"]
        
        if player_entities and stat_entities:
            # Historical player records
            player_name = player_entities[0].value
            stat_name = stat_entities[0].value
            sql, params = await self._build_player_records_query(player_name, stat_name)
            description = f"Historical {stat_name} records for {player_name}"
            entities_used = [player_name, stat_name]
        elif team_entities:
            # Historical team records
            team_name = team_entities[0].value
            sql, params = await self._build_team_history_query(team_name)
            description = f"Historical records for {team_name}"
            entities_used = [team_name]
        else:
            # General historical query
            sql, params = await self._build_general_records_query()
            description = "Historical NBA records"
            entities_used = []
        
        return ProcessedQuery(
            sql=sql,
            params=params,
            query_type="historical_query",
            description=description,
            entities_used=entities_used
        )
    
    async def _process_fallback_query(self, context: QueryContext) -> ProcessedQuery:
        """Process unknown or unclear queries."""
        # Try to determine most likely intent based on entities
        player_entities = [e for e in context.entities if e.entity_type == "player"]
        team_entities = [e for e in context.entities if e.entity_type == "team"]
        
        if player_entities:
            # Default to basic player stats
            player_name = player_entities[0].value
            sql, params = await self._build_basic_player_stats_query(player_name, context.season)
            description = f"Basic statistics for {player_name}"
            entities_used = [player_name]
        elif team_entities:
            # Default to basic team stats
            team_name = team_entities[0].value
            sql, params = await self._build_basic_team_stats_query(team_name, context.season)
            description = f"Basic statistics for {team_name}"
            entities_used = [team_name]
        else:
            # Very generic fallback
            sql, params = await self._build_general_stats_query()
            description = "General NBA statistics"
            entities_used = []
        
        return ProcessedQuery(
            sql=sql,
            params=params,
            query_type="fallback",
            description=description,
            entities_used=entities_used
        )
    
    # Query building methods
    async def _build_basic_player_stats_query(self, player_name: str, season: Optional[str] = None, 
                                            requested_stats: Optional[List[str]] = None) -> Tuple[str, List]:
        """Build basic player statistics query."""
        base_query = """
        SELECT 
            p.player_name,
            COUNT(pgs.game_id) as games_played,
            ROUND(AVG(pgs.points)::numeric, 1) as points_per_game,
            ROUND(AVG(pgs.rebounds_total)::numeric, 1) as rebounds_per_game,
            ROUND(AVG(pgs.assists)::numeric, 1) as assists_per_game,
            ROUND(AVG(pgs.field_goals_made::float / NULLIF(pgs.field_goals_attempted, 0))::numeric, 3) as field_goal_percentage,
            ROUND(AVG(pgs.three_pointers_made::float / NULLIF(pgs.three_pointers_attempted, 0))::numeric, 3) as three_point_percentage,
            ROUND(AVG(pgs.free_throws_made::float / NULLIF(pgs.free_throws_attempted, 0))::numeric, 3) as free_throw_percentage
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN enhanced_games g ON pgs.game_id = g.game_id
        WHERE p.player_name ILIKE $1
        """
        
        params = [f"%{player_name}%"]
        
        if season:
            base_query += " AND g.season = $2"
            params.append(season)
        
        base_query += " GROUP BY p.id, p.player_name"
        
        return base_query, params
    
    async def _build_career_stats_query(self, player_name: str, requested_stats: Optional[List[str]] = None) -> Tuple[str, List]:
        """Build career statistics query."""
        query = """
        SELECT 
            p.player_name,
            COUNT(pgs.game_id) as total_games,
            SUM(pgs.points) as total_points,
            SUM(pgs.rebounds_total) as total_rebounds,
            SUM(pgs.assists) as total_assists,
            ROUND(AVG(pgs.points)::numeric, 1) as career_ppg,
            ROUND(AVG(pgs.rebounds_total)::numeric, 1) as career_rpg,
            ROUND(AVG(pgs.assists)::numeric, 1) as career_apg,
            MIN(g.game_date) as first_game,
            MAX(g.game_date) as last_game,
            COUNT(DISTINCT g.season) as seasons_played
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN enhanced_games g ON pgs.game_id = g.game_id
        WHERE p.player_name ILIKE $1
        GROUP BY p.id, p.player_name
        """
        
        return query, [f"%{player_name}%"]
    
    async def _build_season_stats_query(self, player_name: str, season: str, 
                                      requested_stats: Optional[List[str]] = None) -> Tuple[str, List]:
        """Build season-specific statistics query."""
        return await self._build_basic_player_stats_query(player_name, season, requested_stats)
    
    async def _build_player_comparison_query(self, players: List[str], season: Optional[str] = None,
                                           requested_stats: Optional[List[str]] = None) -> Tuple[str, List]:
        """Build player comparison query."""
        placeholders = ", ".join([f"${i+1}" for i in range(len(players))])
        
        query = f"""
        SELECT 
            p.player_name,
            COUNT(pgs.game_id) as games_played,
            ROUND(AVG(pgs.points)::numeric, 1) as points_per_game,
            ROUND(AVG(pgs.rebounds_total)::numeric, 1) as rebounds_per_game,
            ROUND(AVG(pgs.assists)::numeric, 1) as assists_per_game,
            ROUND(AVG(pgs.steals)::numeric, 1) as steals_per_game,
            ROUND(AVG(pgs.blocks)::numeric, 1) as blocks_per_game,
            ROUND(AVG(pgs.field_goals_made::float / NULLIF(pgs.field_goals_attempted, 0))::numeric, 3) as field_goal_percentage,
            ROUND(AVG(pgs.three_pointers_made::float / NULLIF(pgs.three_pointers_attempted, 0))::numeric, 3) as three_point_percentage
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN enhanced_games g ON pgs.game_id = g.game_id
        WHERE p.player_name = ANY(ARRAY[{placeholders}])
        """
        
        params = players.copy()
        
        if season:
            query += f" AND g.season = ${len(params) + 1}"
            params.append(season)
        
        query += " GROUP BY p.id, p.player_name ORDER BY p.player_name"
        
        return query, params
    
    async def _build_basic_team_stats_query(self, team_name: str, season: Optional[str] = None) -> Tuple[str, List]:
        """Build basic team statistics query."""
        query = """
        SELECT 
            t.full_name as team_name,
            COUNT(g.game_id) as games_played,
            SUM(CASE WHEN g.home_team_id = t.id AND g.home_score > g.away_score THEN 1
                     WHEN g.away_team_id = t.id AND g.away_score > g.home_score THEN 1
                     ELSE 0 END) as wins,
            SUM(CASE WHEN g.home_team_id = t.id AND g.home_score < g.away_score THEN 1
                     WHEN g.away_team_id = t.id AND g.away_score < g.home_score THEN 1
                     ELSE 0 END) as losses,
            ROUND(AVG(CASE WHEN g.home_team_id = t.id THEN g.home_score
                          ELSE g.away_score END)::numeric, 1) as points_per_game,
            ROUND(AVG(CASE WHEN g.home_team_id = t.id THEN g.away_score
                          ELSE g.home_score END)::numeric, 1) as points_allowed_per_game
        FROM teams t
        JOIN enhanced_games g ON (g.home_team_id = t.id OR g.away_team_id = t.id)
        WHERE t.full_name ILIKE $1
        """
        
        params = [f"%{team_name}%"]
        
        if season:
            query += " AND g.season = $2"
            params.append(season)
        
        query += " GROUP BY t.id, t.full_name"
        
        return query, params
    
    async def _build_team_record_query(self, team_name: str, season: Optional[str] = None) -> Tuple[str, List]:
        """Build team record query."""
        return await self._build_basic_team_stats_query(team_name, season)
    
    async def _build_team_performance_query(self, team_name: str, season: Optional[str] = None) -> Tuple[str, List]:
        """Build team performance query."""
        return await self._build_basic_team_stats_query(team_name, season)
    
    async def _build_team_matchup_query(self, home_team: str, away_team: str, season: Optional[str] = None) -> Tuple[str, List]:
        """Build team matchup query."""
        query = """
        SELECT 
            g.game_id,
            g.game_date,
            g.season,
            ht.full_name as home_team,
            at.full_name as away_team,
            g.home_score,
            g.away_score,
            CASE WHEN g.home_score > g.away_score THEN ht.full_name
                 ELSE at.full_name END as winner
        FROM enhanced_games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE (ht.full_name ILIKE $1 AND at.full_name ILIKE $2)
           OR (ht.full_name ILIKE $2 AND at.full_name ILIKE $1)
        """
        
        params = [f"%{home_team}%", f"%{away_team}%"]
        
        if season:
            query += " AND g.season = $3"
            params.append(season)
        
        query += " ORDER BY g.game_date DESC LIMIT 10"
        
        return query, params
    
    async def _build_recent_games_query(self, season: Optional[str] = None) -> Tuple[str, List]:
        """Build recent games query."""
        query = """
        SELECT 
            g.game_id,
            g.game_date,
            g.season,
            ht.full_name as home_team,
            at.full_name as away_team,
            g.home_score,
            g.away_score
        FROM enhanced_games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE 1=1
        """
        
        params = []
        
        if season:
            query += " AND g.season = $1"
            params.append(season)
        
        query += " ORDER BY g.game_date DESC LIMIT 20"
        
        return query, params
    
    async def _build_player_records_query(self, player_name: str, stat_name: str) -> Tuple[str, List]:
        """Build player records query."""
        # Map stat names to database columns
        stat_column_map = {
            "points": "points",
            "rebounds": "rebounds_total", 
            "assists": "assists",
            "steals": "steals",
            "blocks": "blocks"
        }
        
        column = stat_column_map.get(stat_name, "points")
        
        query = f"""
        SELECT 
            p.player_name,
            MAX(pgs.{column}) as highest_{stat_name},
            g.game_date,
            ht.full_name as vs_team
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN enhanced_games g ON pgs.game_id = g.game_id
        JOIN teams ht ON g.home_team_id = ht.id
        WHERE p.player_name ILIKE $1
        GROUP BY p.id, p.player_name, g.game_date, ht.full_name
        ORDER BY pgs.{column} DESC
        LIMIT 5
        """
        
        return query, [f"%{player_name}%"]
    
    async def _build_team_history_query(self, team_name: str) -> Tuple[str, List]:
        """Build team history query."""
        query = """
        SELECT 
            t.full_name as team_name,
            g.season,
            COUNT(g.game_id) as games_played,
            SUM(CASE WHEN g.home_team_id = t.id AND g.home_score > g.away_score THEN 1
                     WHEN g.away_team_id = t.id AND g.away_score > g.home_score THEN 1
                     ELSE 0 END) as wins,
            SUM(CASE WHEN g.home_team_id = t.id AND g.home_score < g.away_score THEN 1
                     WHEN g.away_team_id = t.id AND g.away_score < g.home_score THEN 1
                     ELSE 0 END) as losses
        FROM teams t
        JOIN enhanced_games g ON (g.home_team_id = t.id OR g.away_team_id = t.id)
        WHERE t.full_name ILIKE $1
        GROUP BY t.id, t.full_name, g.season
        ORDER BY g.season DESC
        LIMIT 10
        """
        
        return query, [f"%{team_name}%"]
    
    async def _build_general_records_query(self) -> Tuple[str, List]:
        """Build general records query."""
        query = """
        SELECT 
            'Highest Single Game Points' as record_type,
            p.player_name,
            MAX(pgs.points) as value,
            g.game_date
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.id
        JOIN enhanced_games g ON pgs.game_id = g.game_id
        GROUP BY p.id, p.player_name, g.game_date
        ORDER BY MAX(pgs.points) DESC
        LIMIT 1
        """
        
        return query, []
    
    async def _build_general_stats_query(self) -> Tuple[str, List]:
        """Build general statistics query."""
        query = """
        SELECT 
            COUNT(*) as total_games,
            COUNT(DISTINCT season) as total_seasons,
            MIN(game_date) as earliest_game,
            MAX(game_date) as latest_game
        FROM enhanced_games
        LIMIT 1
        """
        
        return query, []