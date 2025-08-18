"""
Unified query building utilities for NBA database operations.
Provides common SQL generation patterns used across API and MCP servers.
"""

from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re


class QueryType(Enum):
    """Types of queries supported by the query builder"""
    PLAY_BY_PLAY = "play_by_play"
    SHOT_CHART = "shot_chart"
    PLAYER_PLAYS = "player_plays"
    TEAM_PLAYS = "team_plays"
    CLUTCH_PLAYS = "clutch_plays"
    SHOT_ANALYSIS = "shot_analysis"
    ASSIST_ANALYSIS = "assist_analysis"
    DEFENSIVE_PLAYS = "defensive_plays"
    GAME_FLOW = "game_flow"
    TIME_SITUATION = "time_situation"
    GAME_COUNT = "game_count"
    PLAYER_STATS = "player_stats"
    TEAM_STATS = "team_stats"
    GAME_ANALYSIS = "game_analysis"
    PLAYER_COMPARISON = "player_comparison"
    TEAM_COMPARISON = "team_comparison"
    HISTORICAL_QUERY = "historical_query"
    SEASON_QUERY = "season_query"
    PLAYOFF_QUERY = "playoff_query"
    UNKNOWN = "unknown"


@dataclass
class QueryFilter:
    """Represents a filter condition for database queries"""
    column: str
    operator: str
    value: Any
    table_alias: Optional[str] = None

    def to_sql(self, param_name: str) -> str:
        """Convert filter to SQL condition"""
        column_ref = f"{self.table_alias}.{self.column}" if self.table_alias else self.column

        if self.operator == "IN":
            return f"{column_ref} = ANY(${param_name})"
        elif self.operator == "BETWEEN":
            return f"{column_ref} BETWEEN ${param_name}_min AND ${param_name}_max"
        elif self.operator == "LIKE":
            return f"{column_ref} ILIKE ${param_name}"
        elif self.operator == "IS NULL":
            return f"{column_ref} IS NULL"
        elif self.operator == "IS NOT NULL":
            return f"{column_ref} IS NOT NULL"
        else:
            return f"{column_ref} {self.operator} ${param_name}"


@dataclass
class JoinClause:
    """Represents a JOIN clause for database queries"""
    join_type: str  # "INNER", "LEFT", "RIGHT", "FULL"
    table: str
    alias: str
    on_condition: str

    def to_sql(self) -> str:
        """Convert join to SQL clause"""
        return f"{self.join_type} JOIN {self.table} {self.alias} ON {self.on_condition}"


class UnifiedQueryBuilder:
    """Unified query builder for constructing SQL queries with filters and joins"""

    def __init__(self, base_table: str, table_alias: Optional[str] = None):
        self.base_table = base_table
        self.table_alias = table_alias or base_table.split()[0]
        self.joins: List[JoinClause] = []
        self.filters: List[QueryFilter] = []
        self.parameters: Dict[str, Any] = {}
        self.param_counter = 1
        self.select_columns: List[str] = []
        self.group_by_columns: List[str] = []
        self.having_conditions: List[str] = []
        self.order_by_columns: List[str] = []
        self.limit_value: Optional[int] = None
        self.offset_value: Optional[int] = None

    def _get_param_name(self) -> str:
        """Generate unique parameter name"""
        name = f"param_{self.param_counter}"
        self.param_counter += 1
        return name

    def add_select(self, columns: Union[str, List[str]]) -> 'UnifiedQueryBuilder':
        """Add SELECT columns to query"""
        if isinstance(columns, str):
            columns = [columns]
        self.select_columns.extend(columns)
        return self

    def add_join(self, join_type: str, table: str, alias: str, on_condition: str) -> 'UnifiedQueryBuilder':
        """Add JOIN clause to query"""
        self.joins.append(JoinClause(join_type, table, alias, on_condition))
        return self

    def add_filter(self, column: str, operator: str, value: Any, table_alias: Optional[str] = None) -> 'UnifiedQueryBuilder':
        """Add WHERE filter to query"""
        self.filters.append(QueryFilter(column, operator, value, table_alias))
        return self

    def add_season_filter(self, season: str, table_alias: Optional[str] = None) -> 'UnifiedQueryBuilder':
        """Add season filter to query"""
        if not season:
            return self

        season_alias = table_alias or self.table_alias

        if season == "latest":
            # Get most recent season from database
            subquery = "SELECT MAX(season) FROM enhanced_games"
            self.filters.append(QueryFilter("season", "=", f"({subquery})", season_alias))
        elif season == "all":
            pass  # No filter
        elif "," in season:
            seasons = [s.strip() for s in season.split(",")]
            self.add_filter("season", "IN", seasons, season_alias)
        else:
            self.add_filter("season", "=", season, season_alias)

        return self

    def add_team_filter(self, team_id: Union[int, str], table_alias: Optional[str] = None) -> 'UnifiedQueryBuilder':
        """Add team filter to query"""
        if not team_id:
            return self

        team_alias = table_alias or self.table_alias

        if isinstance(team_id, str) and "," in team_id:
            team_ids = [int(t.strip()) for t in team_id.split(",")]
            self.add_filter("team_id", "IN", team_ids, team_alias)
        else:
            self.add_filter("team_id", "=", int(team_id), team_alias)

        return self

    def add_player_filter(self, player_id: Union[int, str], table_alias: Optional[str] = None) -> 'UnifiedQueryBuilder':
        """Add player filter to query"""
        if not player_id:
            return self

        player_alias = table_alias or self.table_alias

        if isinstance(player_id, str) and "," in player_id:
            player_ids = [int(p.strip()) for p in player_id.split(",")]
            self.add_filter("player_id", "IN", player_ids, player_alias)
        else:
            self.add_filter("player_id", "=", int(player_id), player_alias)

        return self

    def add_date_range_filter(self, start_date: str, end_date: str, table_alias: Optional[str] = None) -> 'UnifiedQueryBuilder':
        """Add date range filter to query"""
        date_alias = table_alias or self.table_alias

        if start_date:
            self.add_filter("game_date", ">=", start_date, date_alias)
        if end_date:
            self.add_filter("game_date", "<=", end_date, date_alias)

        return self

    def add_group_by(self, columns: Union[str, List[str]]) -> 'UnifiedQueryBuilder':
        """Add GROUP BY columns to query"""
        if isinstance(columns, str):
            columns = [columns]
        self.group_by_columns.extend(columns)
        return self

    def add_having(self, condition: str) -> 'UnifiedQueryBuilder':
        """Add HAVING condition to query"""
        self.having_conditions.append(condition)
        return self

    def add_order_by(self, columns: Union[str, List[str]]) -> 'UnifiedQueryBuilder':
        """Add ORDER BY columns to query"""
        if isinstance(columns, str):
            columns = [columns]
        self.order_by_columns.extend(columns)
        return self

    def add_limit(self, limit: int) -> 'UnifiedQueryBuilder':
        """Add LIMIT to query"""
        self.limit_value = limit
        return self

    def add_offset(self, offset: int) -> 'UnifiedQueryBuilder':
        """Add OFFSET to query"""
        self.offset_value = offset
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """Build the complete SQL query and return query string and parameters"""

        # Build SELECT clause
        if self.select_columns:
            select_clause = f"SELECT {', '.join(self.select_columns)}"
        else:
            select_clause = f"SELECT {self.table_alias}.*"

        # Build FROM clause
        from_clause = f"FROM {self.base_table}"
        if self.table_alias != self.base_table:
            from_clause += f" {self.table_alias}"

        # Build JOIN clauses
        join_clauses = []
        for join in self.joins:
            join_clauses.append(join.to_sql())

        # Build WHERE clause
        where_conditions = []
        param_values = []

        for filter_obj in self.filters:
            param_name = self._get_param_name()

            if filter_obj.operator == "BETWEEN":
                # Handle BETWEEN operator specially
                where_conditions.append(filter_obj.to_sql(param_name))
                param_values.extend([filter_obj.value[0], filter_obj.value[1]])
            elif filter_obj.operator in ["IS NULL", "IS NOT NULL"]:
                # Handle NULL operators without parameters
                where_conditions.append(filter_obj.to_sql(param_name))
            elif "(" in str(filter_obj.value) and ")" in str(filter_obj.value):
                # Handle subqueries
                column_ref = f"{filter_obj.table_alias}.{filter_obj.column}" if filter_obj.table_alias else filter_obj.column
                where_conditions.append(f"{column_ref} {filter_obj.operator} {filter_obj.value}")
            else:
                where_conditions.append(filter_obj.to_sql(param_name))
                param_values.append(filter_obj.value)

        # Build the complete query
        query_parts = [select_clause, from_clause]

        if join_clauses:
            query_parts.extend(join_clauses)

        if where_conditions:
            query_parts.append(f"WHERE {' AND '.join(where_conditions)}")

        if self.group_by_columns:
            query_parts.append(f"GROUP BY {', '.join(self.group_by_columns)}")

        if self.having_conditions:
            query_parts.append(f"HAVING {' AND '.join(self.having_conditions)}")

        if self.order_by_columns:
            query_parts.append(f"ORDER BY {', '.join(self.order_by_columns)}")

        if self.limit_value is not None:
            query_parts.append(f"LIMIT {self.limit_value}")

        if self.offset_value is not None:
            query_parts.append(f"OFFSET {self.offset_value}")

        query = " ".join(query_parts)

        return query, param_values

    def build_count_query(self) -> Tuple[str, List[Any]]:
        """Build a COUNT query version of the current query"""

        # Build FROM clause
        from_clause = f"FROM {self.base_table}"
        if self.table_alias != self.base_table:
            from_clause += f" {self.table_alias}"

        # Build JOIN clauses
        join_clauses = []
        for join in self.joins:
            join_clauses.append(join.to_sql())

        # Build WHERE clause (same as main query)
        where_conditions = []
        param_values = []

        for filter_obj in self.filters:
            param_name = self._get_param_name()

            if filter_obj.operator == "BETWEEN":
                where_conditions.append(filter_obj.to_sql(param_name))
                param_values.extend([filter_obj.value[0], filter_obj.value[1]])
            elif filter_obj.operator in ["IS NULL", "IS NOT NULL"]:
                where_conditions.append(filter_obj.to_sql(param_name))
            elif "(" in str(filter_obj.value) and ")" in str(filter_obj.value):
                column_ref = f"{filter_obj.table_alias}.{filter_obj.column}" if filter_obj.table_alias else filter_obj.column
                where_conditions.append(f"{column_ref} {filter_obj.operator} {filter_obj.value}")
            else:
                where_conditions.append(filter_obj.to_sql(param_name))
                param_values.append(filter_obj.value)

        # Build the count query
        query_parts = ["SELECT COUNT(*)", from_clause]

        if join_clauses:
            query_parts.extend(join_clauses)

        if where_conditions:
            query_parts.append(f"WHERE {' AND '.join(where_conditions)}")

        query = " ".join(query_parts)

        return query, param_values


class PlayerQueryBuilder(UnifiedQueryBuilder):
    """Specialized query builder for player-related queries"""

    def __init__(self):
        super().__init__("players", "p")

    def add_player_name_filter(self, player_name: str) -> 'PlayerQueryBuilder':
        """Add player name filter with fuzzy matching"""
        if not player_name:
            return self

        # Use ILIKE for case-insensitive partial matching
        self.add_filter("player_name", "LIKE", f"%{player_name}%", "p")
        return self

    def add_team_filter(self, team_id: Union[int, str]) -> 'PlayerQueryBuilder':
        """Add team filter for players"""
        if not team_id:
            return self

        if isinstance(team_id, str) and "," in team_id:
            team_ids = [int(t.strip()) for t in team_id.split(",")]
            self.add_filter("team_id", "IN", team_ids, "p")
        else:
            self.add_filter("team_id", "=", int(team_id), "p")

        return self


class GameQueryBuilder(UnifiedQueryBuilder):
    """Specialized query builder for game-related queries"""

    def __init__(self):
        super().__init__("enhanced_games", "eg")

    def add_playoff_filter(self, playoffs_only: bool = False) -> 'GameQueryBuilder':
        """Add playoff filter"""
        if playoffs_only:
            self.add_filter("game_type", "=", "playoff", "eg")
        return self

    def add_matchup_filter(self, home_team_id: int, away_team_id: int) -> 'GameQueryBuilder':
        """Add specific matchup filter"""
        # Match games where teams played each other (home/away)
        matchup_condition = f"(eg.home_team_id = {home_team_id} AND eg.away_team_id = {away_team_id}) OR (eg.home_team_id = {away_team_id} AND eg.away_team_id = {home_team_id})"
        self.filters.append(QueryFilter("matchup", "CUSTOM", matchup_condition))
        return self


class PlayQueryBuilder(UnifiedQueryBuilder):
    """Specialized query builder for play-by-play queries"""

    def __init__(self):
        super().__init__("play_events", "pe")

    def add_event_type_filter(self, event_types: Union[str, List[str]]) -> 'PlayQueryBuilder':
        """Add event type filter"""
        if not event_types:
            return self

        if isinstance(event_types, str):
            if "," in event_types:
                event_types = [et.strip() for et in event_types.split(",")]
            else:
                event_types = [event_types]

        self.add_filter("event_type", "IN", event_types, "pe")
        return self

    def add_quarter_filter(self, quarter: Union[int, str]) -> 'PlayQueryBuilder':
        """Add quarter/period filter"""
        if not quarter:
            return self

        if isinstance(quarter, str) and "," in quarter:
            quarters = [int(q.strip()) for q in quarter.split(",")]
            self.add_filter("quarter", "IN", quarters, "pe")
        else:
            self.add_filter("quarter", "=", int(quarter), "pe")

        return self

    def add_clutch_time_filter(self, clutch_only: bool = False) -> 'PlayQueryBuilder':
        """Add clutch time filter (last 5 minutes, score within 5)"""
        if clutch_only:
            # This would need to be customized based on your specific clutch time definition
            clutch_condition = "pe.time_remaining_seconds <= 300 AND ABS(pe.score_home - pe.score_away) <= 5"
            self.filters.append(QueryFilter("clutch", "CUSTOM", clutch_condition))
        return self