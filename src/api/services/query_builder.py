"""
Dynamic SQL query builder for NBA API endpoints.
Constructs complex SQL queries based on user parameters and filters.
"""

from typing import Dict, List, Any, Tuple, Optional
import json


class QueryBuilder:
    """Dynamic query builder for constructing SQL queries with filters and joins"""
    
    def __init__(self, base_table: str):
        self.base_table = base_table
        self.joins = []
        self.where_conditions = []
        self.parameters = {}
        self.param_counter = 1
    
    def _get_param_name(self) -> str:
        """Generate unique parameter name"""
        name = f"param_{self.param_counter}"
        self.param_counter += 1
        return name
    
    def add_season_filter(self, season: str) -> None:
        """Add season filter to query"""
        if not season:
            return
            
        # Determine the correct table alias for season column
        season_column = "eg.season"  # Default to enhanced_games
        if self.base_table.startswith("enhanced_games"):
            season_column = f"{self.base_table.split()[0]}.season"
            
        if season == "latest":
            # Get most recent season from database
            subquery = "SELECT MAX(season) FROM enhanced_games"
            self.where_conditions.append(f"{season_column} = ({subquery})")
        elif season == "all":
            pass  # No filter
        elif "," in season:
            seasons = [s.strip() for s in season.split(",")]
            param_name = self._get_param_name()
            self.where_conditions.append(f"{season_column} = ANY(${len(self.parameters) + 1})")
            self.parameters[param_name] = seasons
        else:
            param_name = self._get_param_name()
            self.where_conditions.append(f"{season_column} = ${len(self.parameters) + 1}")
            self.parameters[param_name] = season
    
    def add_game_filter(self, game_id: str) -> None:
        """Add game ID filter to query"""
        if not game_id:
            return
            
        # Determine the correct table alias for game columns
        game_date_column = "eg.game_date"  # Default to enhanced_games
        game_id_column = f"{self.base_table.split()[0]}.game_id"  # Base table has game_id
        
        if game_id == "latest":
            # Get most recent game date
            subquery = "SELECT MAX(game_date) FROM enhanced_games"
            self.where_conditions.append(f"{game_date_column} = ({subquery})")
        elif game_id == "all":
            pass
        elif "," in game_id:
            game_ids = [g.strip() for g in game_id.split(",")]
            param_name = self._get_param_name()
            self.where_conditions.append(f"{game_id_column} = ANY(${len(self.parameters) + 1})")
            self.parameters[param_name] = game_ids
        else:
            param_name = self._get_param_name()
            self.where_conditions.append(f"{game_id_column} = ${len(self.parameters) + 1}")
            self.parameters[param_name] = game_id
    
    def add_date_filters(self, date_from=None, date_to=None) -> None:
        """Add date range filters"""
        # Date filters always use enhanced_games table
        game_date_column = "eg.game_date"
        
        if date_from:
            param_name = self._get_param_name()
            self.where_conditions.append(f"{game_date_column} >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = date_from
        
        if date_to:
            param_name = self._get_param_name()
            self.where_conditions.append(f"{game_date_column} <= ${len(self.parameters) + 1}")
            self.parameters[param_name] = date_to
    
    def add_player_filters(self, player_id=None, player_name=None) -> None:
        """Add player-specific filters"""
        # Get the correct table alias
        base_table_alias = self.base_table.split()[1] if len(self.base_table.split()) > 1 else self.base_table.split()[0]
        
        if player_id:
            if isinstance(player_id, list):
                param_name = self._get_param_name()
                self.where_conditions.append(f"{base_table_alias}.player_id = ANY(${len(self.parameters) + 1})")
                self.parameters[param_name] = player_id
            else:
                param_name = self._get_param_name()
                self.where_conditions.append(f"{base_table_alias}.player_id = ${len(self.parameters) + 1}")
                self.parameters[param_name] = player_id
        
        if player_name:
            # Add join to players table if needed
            if "players p" not in " ".join(self.joins):
                self.joins.append(f"JOIN players p ON {base_table_alias}.player_id = p.id")
            param_name = self._get_param_name()
            self.where_conditions.append(f"p.player_name ILIKE ${len(self.parameters) + 1}")
            self.parameters[param_name] = f"%{player_name}%"
    
    def add_team_filters(self, team_id=None, team_name=None, home_away=None, opponent_team_id=None) -> None:
        """Add team-specific filters"""
        # Get the correct table alias
        base_table_alias = self.base_table.split()[1] if len(self.base_table.split()) > 1 else self.base_table.split()[0]
        
        if team_id:
            if isinstance(team_id, list):
                param_name = self._get_param_name()
                self.where_conditions.append(f"{base_table_alias}.team_id = ANY(${len(self.parameters) + 1})")
                self.parameters[param_name] = team_id
            else:
                param_name = self._get_param_name()
                self.where_conditions.append(f"{base_table_alias}.team_id = ${len(self.parameters) + 1}")
                self.parameters[param_name] = team_id
        
        if team_name:
            # Handle comma-separated team names
            if "," in team_name:
                team_names = [t.strip() for t in team_name.split(",")]
                # Add join to teams table if needed
                if "teams t" not in " ".join(self.joins):
                    self.joins.append(f"JOIN teams t ON {base_table_alias}.team_id = t.id")
                param_name = self._get_param_name()
                name_conditions = []
                for name in team_names:
                    name_param = self._get_param_name()
                    name_conditions.append(f"(t.full_name ILIKE ${len(self.parameters) + 1} OR t.tricode ILIKE ${len(self.parameters) + 1})")
                    self.parameters[name_param] = f"%{name}%"
                self.where_conditions.append(f"({' OR '.join(name_conditions)})")
            else:
                # Add join to teams table if needed
                if "teams t" not in " ".join(self.joins):
                    self.joins.append(f"JOIN teams t ON {base_table_alias}.team_id = t.id")
                param_name = self._get_param_name()
                self.where_conditions.append(f"(t.full_name ILIKE ${len(self.parameters) + 1} OR t.tricode ILIKE ${len(self.parameters) + 1})")
                self.parameters[param_name] = f"%{team_name}%"
        
        if home_away and home_away != "all":
            # Determine home/away status from enhanced_games table
            base_table_alias = self.base_table.split()[1] if len(self.base_table.split()) > 1 else self.base_table.split()[0]
            if home_away == "home":
                self.where_conditions.append(f"{base_table_alias}.team_id = eg.home_team_id")
            elif home_away == "away":
                self.where_conditions.append(f"{base_table_alias}.team_id = eg.away_team_id")
        
        if opponent_team_id:
            # Determine opponent team by checking if it's home or away opponent
            base_table_alias = self.base_table.split()[1] if len(self.base_table.split()) > 1 else self.base_table.split()[0]
            param_name = self._get_param_name()
            self.where_conditions.append(f"""
                (({base_table_alias}.team_id = eg.home_team_id AND eg.away_team_id = ${len(self.parameters) + 1}) OR 
                 ({base_table_alias}.team_id = eg.away_team_id AND eg.home_team_id = ${len(self.parameters) + 1}))
            """)
            self.parameters[param_name] = opponent_team_id
    
    def add_game_type_filter(self, game_type: str) -> None:
        """Add game type filter (regular/playoff)"""
        if game_type and game_type != "all":
            # Game type is in enhanced_games table
            param_name = self._get_param_name()
            self.where_conditions.append(f"eg.game_type = ${len(self.parameters) + 1}")
            self.parameters[param_name] = game_type
    
    def add_win_loss_filter(self, win_loss: str) -> None:
        """Add win/loss filter for team queries"""
        if win_loss and win_loss != "all":
            if win_loss.lower() == "win" or win_loss.upper() == "W":
                self.where_conditions.append(f"{self.base_table}.wins > {self.base_table}.losses")
            elif win_loss.lower() == "loss" or win_loss.upper() == "L":
                self.where_conditions.append(f"{self.base_table}.wins < {self.base_table}.losses")
    
    def add_dynamic_filters(self, filters: Dict[str, Any]) -> None:
        """Add dynamic filters from JSON object like {'points': {'gte': 20}, 'assists': {'gte': 5}}"""
        if not filters:
            return
            
        for field, conditions in filters.items():
            if isinstance(conditions, dict):
                for operator, value in conditions.items():
                    sql_op = self._get_sql_operator(operator)
                    param_name = self._get_param_name()
                    
                    if operator in ['in', 'not_in']:
                        # Handle list values for IN/NOT IN operators
                        if isinstance(value, list):
                            self.where_conditions.append(f"{self.base_table}.{field} {sql_op} (${len(self.parameters) + 1})")
                            self.parameters[param_name] = value
                        else:
                            # Convert single value to list
                            self.where_conditions.append(f"{self.base_table}.{field} {sql_op} (${len(self.parameters) + 1})")
                            self.parameters[param_name] = [value]
                    else:
                        self.where_conditions.append(f"{self.base_table}.{field} {sql_op} ${len(self.parameters) + 1}")
                        self.parameters[param_name] = value
            else:
                # Simple equality filter
                param_name = self._get_param_name()
                self.where_conditions.append(f"{self.base_table}.{field} = ${len(self.parameters) + 1}")
                self.parameters[param_name] = conditions
    
    def _get_sql_operator(self, operator: str) -> str:
        """Map filter operators to SQL operators"""
        mapping = {
            'gte': '>=', 'gt': '>', 'lte': '<=', 'lt': '<',
            'eq': '=', 'ne': '!=', 'in': 'IN', 'not_in': 'NOT IN',
            'like': 'LIKE', 'ilike': 'ILIKE'
        }
        return mapping.get(operator, '=')
    
    def add_lineup_filters(self, player_ids=None, exclude_player_ids=None, lineup_size=None, min_minutes=None) -> None:
        """Add lineup-specific filters"""
        if player_ids:
            # This would require complex logic to find lineups containing specific players
            # For now, add a placeholder condition
            param_name = self._get_param_name()
            self.where_conditions.append(f"{self.base_table}.player_ids @> ${len(self.parameters) + 1}")
            self.parameters[param_name] = player_ids
        
        if exclude_player_ids:
            param_name = self._get_param_name()
            self.where_conditions.append(f"NOT ({self.base_table}.player_ids && ${len(self.parameters) + 1})")
            self.parameters[param_name] = exclude_player_ids
        
        if lineup_size:
            param_name = self._get_param_name()
            self.where_conditions.append(f"array_length({self.base_table}.player_ids, 1) = ${len(self.parameters) + 1}")
            self.parameters[param_name] = lineup_size
        
        if min_minutes:
            param_name = self._get_param_name()
            self.where_conditions.append(f"{self.base_table}.minutes_played >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = min_minutes
    
    def add_sort_clause(self, sort: str) -> str:
        """Generate ORDER BY clause from sort specification"""
        if not sort:
            return ""
        
        sort_parts = []
        for field in sort.split(","):
            field = field.strip()
            if field.startswith("-"):
                sort_parts.append(f"{field[1:]} DESC")
            else:
                sort_parts.append(f"{field} ASC")
        
        return f"ORDER BY {', '.join(sort_parts)}"
    
    def add_pagination(self, limit: int, offset: int) -> str:
        """Generate LIMIT and OFFSET clause"""
        return f"LIMIT {limit} OFFSET {offset}"
    
    def build_query(self, select_fields: List[str] = None) -> Tuple[str, List[Any]]:
        """Build the complete SQL query"""
        if not select_fields:
            select_fields = [f"{self.base_table}.*"]
        
        query_parts = [
            f"SELECT {', '.join(select_fields)}",
            f"FROM {self.base_table}"
        ]
        
        if self.joins:
            query_parts.extend(self.joins)
        
        if self.where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
        
        # Convert parameters dict to ordered list
        param_values = []
        for i in range(1, len(self.parameters) + 1):
            for key, value in self.parameters.items():
                if key == f"param_{i}":
                    param_values.append(value)
                    break
        
        return " ".join(query_parts), param_values
    
    def build_count_query(self) -> Tuple[str, List[Any]]:
        """Build a count query for pagination"""
        query_parts = [
            f"SELECT COUNT(*)",
            f"FROM {self.base_table}"
        ]
        
        if self.joins:
            query_parts.extend(self.joins)
        
        if self.where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
        
        # Convert parameters dict to ordered list
        param_values = []
        for i in range(1, len(self.parameters) + 1):
            for key, value in self.parameters.items():
                if key == f"param_{i}":
                    param_values.append(value)
                    break
        
        return " ".join(query_parts), param_values


class PlayerQueryBuilder(QueryBuilder):
    """Specialized query builder for player statistics"""
    
    def __init__(self):
        super().__init__("player_game_stats pgs")
        # Add common joins for player queries
        self.joins.extend([
            "JOIN enhanced_games eg ON pgs.game_id = eg.game_id",
            "JOIN players p ON pgs.player_id = p.id",
            "JOIN teams t ON pgs.team_id = t.team_id"
        ])
        # Only count games where player actually played (minutes > 0)
        self.where_conditions.append("pgs.minutes_played > 0")
    
    def build_basic_stats_query(self, player_name: str = None, season: str = None) -> Tuple[str, List[Any]]:
        """Build a basic stats query for player statistics with aggregation."""
        # Apply filters
        if player_name:
            self.add_player_filters(player_name=player_name)
        if season:
            self.add_season_filter(season)
        
        # Define aggregation fields for basic stats
        select_fields = [
            "p.player_name",
            "COUNT(pgs.game_id) as games_played",
            "ROUND(AVG(pgs.points)::numeric, 1) as points_per_game",
            "ROUND(AVG(pgs.rebounds_total)::numeric, 1) as rebounds_per_game", 
            "ROUND(AVG(pgs.assists)::numeric, 1) as assists_per_game",
            "ROUND(AVG(pgs.steals)::numeric, 1) as steals_per_game",
            "ROUND(AVG(pgs.blocks)::numeric, 1) as blocks_per_game",
            "ROUND(AVG(pgs.turnovers)::numeric, 1) as turnovers_per_game",
            "ROUND(AVG(CASE WHEN pgs.field_goals_attempted > 0 THEN pgs.field_goals_made::float / pgs.field_goals_attempted END)::numeric, 3) as field_goal_percentage",
            "ROUND(AVG(CASE WHEN pgs.three_pointers_attempted > 0 THEN pgs.three_pointers_made::float / pgs.three_pointers_attempted END)::numeric, 3) as three_point_percentage",
            "ROUND(AVG(CASE WHEN pgs.free_throws_attempted > 0 THEN pgs.free_throws_made::float / pgs.free_throws_attempted END)::numeric, 3) as free_throw_percentage",
            "SUM(pgs.points) as total_points",
            "SUM(pgs.rebounds_total) as total_rebounds", 
            "SUM(pgs.assists) as total_assists",
            "ROUND(AVG(pgs.minutes_played)::numeric, 1) as minutes_per_game"
        ]
        
        # Build the query with aggregation
        query_parts = [
            f"SELECT {', '.join(select_fields)}",
            f"FROM {self.base_table}"
        ]
        
        if self.joins:
            query_parts.extend(self.joins)
        
        if self.where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
        
        # Add GROUP BY for aggregation
        query_parts.append("GROUP BY p.player_name")
        
        # Convert parameters dict to ordered list
        param_values = []
        for i in range(1, len(self.parameters) + 1):
            for key, value in self.parameters.items():
                if key == f"param_{i}":
                    param_values.append(value)
                    break
        
        return " ".join(query_parts), param_values


class TeamQueryBuilder(QueryBuilder):
    """Specialized query builder for team statistics"""
    
    def __init__(self):
        super().__init__("team_game_stats tgs")
        # Add common joins for team queries
        self.joins.extend([
            "JOIN enhanced_games eg ON tgs.game_id = eg.game_id",
            "JOIN teams t ON tgs.team_id = t.id"
        ])
    
    def build_basic_stats_query(self, team_name: str = None, season: str = None) -> Tuple[str, List[Any]]:
        """Build a basic stats query for team statistics with aggregation."""
        # Apply filters
        if team_name:
            self.add_team_filters(team_name=team_name)
        if season:
            self.add_season_filter(season)
        
        # Define aggregation fields for basic team stats
        select_fields = [
            "t.full_name as team_name",
            "t.tricode as team_abbreviation", 
            "COUNT(tgs.game_id) as games_played",
            "SUM(CASE WHEN tgs.wins > tgs.losses THEN 1 ELSE 0 END) as wins",
            "SUM(CASE WHEN tgs.wins < tgs.losses THEN 1 ELSE 0 END) as losses",
            "ROUND(AVG(tgs.points)::numeric, 1) as points_per_game",
            "ROUND(AVG(tgs.rebounds_total)::numeric, 1) as rebounds_per_game",
            "ROUND(AVG(tgs.assists)::numeric, 1) as assists_per_game", 
            "ROUND(AVG(tgs.steals)::numeric, 1) as steals_per_game",
            "ROUND(AVG(tgs.blocks)::numeric, 1) as blocks_per_game",
            "ROUND(AVG(tgs.turnovers)::numeric, 1) as turnovers_per_game",
            "ROUND(AVG(CASE WHEN tgs.field_goals_attempted > 0 THEN tgs.field_goals_made::float / tgs.field_goals_attempted END)::numeric, 3) as field_goal_percentage",
            "ROUND(AVG(CASE WHEN tgs.three_pointers_attempted > 0 THEN tgs.three_pointers_made::float / tgs.three_pointers_attempted END)::numeric, 3) as three_point_percentage",
            "ROUND(AVG(CASE WHEN tgs.free_throws_attempted > 0 THEN tgs.free_throws_made::float / tgs.free_throws_attempted END)::numeric, 3) as free_throw_percentage",
            "SUM(tgs.points) as total_points",
            "SUM(tgs.rebounds_total) as total_rebounds",
            "SUM(tgs.assists) as total_assists"
        ]
        
        # Build the query with aggregation
        query_parts = [
            f"SELECT {', '.join(select_fields)}",
            f"FROM {self.base_table}"
        ]
        
        if self.joins:
            query_parts.extend(self.joins)
        
        if self.where_conditions:
            query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
        
        # Add GROUP BY for aggregation
        query_parts.append("GROUP BY t.full_name, t.tricode")
        
        # Convert parameters dict to ordered list
        param_values = []
        for i in range(1, len(self.parameters) + 1):
            for key, value in self.parameters.items():
                if key == f"param_{i}":
                    param_values.append(value)
                    break
        
        return " ".join(query_parts), param_values


class LineupQueryBuilder(QueryBuilder):
    """Specialized query builder for lineup statistics"""
    
    def __init__(self):
        super().__init__("lineup_stats ls")
        # Add common joins for lineup queries
        self.joins.extend([
            "JOIN enhanced_games eg ON ls.game_id = eg.game_id",
            "JOIN teams t ON ls.team_id = t.id"
        ])


class ShotQueryBuilder(QueryBuilder):
    """Specialized query builder for shot chart data"""
    
    def __init__(self):
        super().__init__("play_events pe")
        # Add common joins for shot queries
        self.joins.extend([
            "JOIN enhanced_games eg ON pe.game_id = eg.game_id",
            "JOIN players p ON pe.player_id = p.id",
            "JOIN teams t ON pe.team_id = t.id"
        ])
        # Add shot-specific conditions
        self.where_conditions.append("pe.event_type IN ('Made Shot', 'Missed Shot')")


class PlayByPlayQueryBuilder(QueryBuilder):
    """Specialized query builder for play-by-play data with comprehensive filtering"""
    
    def __init__(self):
        super().__init__("play_events pe")
        # Add common joins for play-by-play queries
        self.joins.extend([
            "JOIN enhanced_games eg ON pe.game_id = eg.game_id"
        ])
        # Add optional joins that can be enabled based on query needs
        self.optional_joins = {
            "players": "LEFT JOIN players p ON pe.player_id = p.id",
            "teams": "LEFT JOIN teams t ON pe.team_id = t.team_id",
            "home_team": "LEFT JOIN teams ht ON eg.home_team_id = ht.team_id",
            "away_team": "LEFT JOIN teams at ON eg.away_team_id = at.team_id",
            "assist_player": "LEFT JOIN players ap ON pe.assist_player_id = ap.id"
        }
    
    def add_optional_join(self, join_type: str):
        """Add optional joins for additional data"""
        if join_type in self.optional_joins:
            join_sql = self.optional_joins[join_type]
            if join_sql not in self.joins:  # Avoid duplicates
                self.joins.append(join_sql)
    
    def add_shot_coordinate_filters(self, x_min=None, x_max=None, y_min=None, y_max=None, 
                                  shot_distance_min=None, shot_distance_max=None):
        """Add shot coordinate and distance filters"""
        # Ensure we only filter on actual shots
        self.where_conditions.append("pe.shot_x IS NOT NULL AND pe.shot_y IS NOT NULL")
        
        if x_min is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_x >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = x_min
        
        if x_max is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_x <= ${len(self.parameters) + 1}")
            self.parameters[param_name] = x_max
        
        if y_min is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_y >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = y_min
        
        if y_max is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_y <= ${len(self.parameters) + 1}")
            self.parameters[param_name] = y_max
        
        if shot_distance_min is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_distance >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = shot_distance_min
        
        if shot_distance_max is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_distance <= ${len(self.parameters) + 1}")
            self.parameters[param_name] = shot_distance_max
    
    def add_time_filters(self, period=None, time_remaining_min=None, time_remaining_max=None,
                        time_elapsed_min=None, time_elapsed_max=None, crunch_time=False):
        """Add time-based filters for specific game situations"""
        
        if period is not None:
            if isinstance(period, list):
                param_name = self._get_param_name()
                self.where_conditions.append(f"pe.period = ANY(${len(self.parameters) + 1})")
                self.parameters[param_name] = period
            else:
                param_name = self._get_param_name()
                self.where_conditions.append(f"pe.period = ${len(self.parameters) + 1}")
                self.parameters[param_name] = period
        
        if time_elapsed_min is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.time_elapsed_seconds >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = time_elapsed_min
        
        if time_elapsed_max is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.time_elapsed_seconds <= ${len(self.parameters) + 1}")
            self.parameters[param_name] = time_elapsed_max
        
        if crunch_time:
            # Crunch time: last 5 minutes of 4th quarter or any overtime
            crunch_condition = (
                "(pe.period = 4 AND pe.time_elapsed_seconds >= 2580) OR "  # Last 5 min of 4th (48*60 - 5*60 = 2580)
                "(pe.period > 4)"  # Any overtime
            )
            self.where_conditions.append(crunch_condition)
    
    def add_event_type_filters(self, event_types=None, shot_made=None, event_action_types=None):
        """Add event type and action filters"""
        
        if event_types:
            if isinstance(event_types, str):
                event_types = [event_types]
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.event_type = ANY(${len(self.parameters) + 1})")
            self.parameters[param_name] = event_types
        
        if shot_made is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_made = ${len(self.parameters) + 1}")
            self.parameters[param_name] = shot_made
        
        if event_action_types:
            if isinstance(event_action_types, str):
                event_action_types = [event_action_types]
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.event_action_type = ANY(${len(self.parameters) + 1})")
            self.parameters[param_name] = event_action_types
    
    def add_score_context_filters(self, score_margin_min=None, score_margin_max=None, 
                                close_game=False, blowout_threshold=None):
        """Add score context filters for game situations"""
        
        if score_margin_min is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.score_margin >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = score_margin_min
        
        if score_margin_max is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.score_margin <= ${len(self.parameters) + 1}")
            self.parameters[param_name] = score_margin_max
        
        if close_game:
            # Close game: score margin within 5 points
            self.where_conditions.append("ABS(pe.score_margin) <= 5")
        
        if blowout_threshold is not None:
            param_name = self._get_param_name()
            self.where_conditions.append(f"ABS(pe.score_margin) >= ${len(self.parameters) + 1}")
            self.parameters[param_name] = blowout_threshold
    
    def add_shot_zone_filters(self, shot_zones=None, shot_types=None):
        """Add shot zone and type filters"""
        
        if shot_zones:
            if isinstance(shot_zones, str):
                shot_zones = [shot_zones]
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_zone = ANY(${len(self.parameters) + 1})")
            self.parameters[param_name] = shot_zones
        
        if shot_types:
            if isinstance(shot_types, str):
                shot_types = [shot_types]
            param_name = self._get_param_name()
            self.where_conditions.append(f"pe.shot_type = ANY(${len(self.parameters) + 1})")
            self.parameters[param_name] = shot_types
    
    def add_clutch_situation_filters(self, last_minutes=5, score_within=5):
        """Add filters for clutch situations (close games in final minutes)"""
        # Clutch: last X minutes of regulation or overtime, score within Y points
        clutch_condition = (
            f"((pe.period = 4 AND pe.time_elapsed_seconds >= {2880 - last_minutes * 60}) OR "  # Last X min of 4th
            f"(pe.period > 4 AND pe.time_elapsed_seconds >= {(pe.period - 1) * 25 * 60 + 2880 - last_minutes * 60})) AND "  # OT
            f"ABS(pe.score_margin) <= {score_within}"
        )
        self.where_conditions.append(clutch_condition)
    
    def build_shot_chart_query(self, include_coordinates=True, include_zones=True):
        """Build specialized query for shot chart data"""
        # Only require coordinates if specifically requested and available
        if include_coordinates:
            # Make coordinates optional - include shots with or without coordinates
            pass  # Don't require coordinates by default
        
        # Build select fields for shot chart
        select_fields = [
            "pe.event_id",
            "pe.game_id", 
            "eg.season",
            "eg.game_date",
            "pe.period",
            "pe.time_remaining",
            "pe.shot_made",
            "pe.shot_distance"
        ]
        
        if include_coordinates:
            select_fields.extend(["pe.shot_x", "pe.shot_y"])
        
        if include_zones:
            select_fields.extend(["pe.shot_zone", "pe.shot_type"])
        
        # Add player info if joined
        if any("players p" in join for join in self.joins):
            select_fields.append("p.player_name")
        
        # Add team info if joined 
        if any("teams t" in join for join in self.joins):
            select_fields.append("t.full_name as team_name")
        
        return self.build_query(select_fields)
    
    def build_play_sequence_query(self, order_by_time=True):
        """Build query for sequential play-by-play events"""
        select_fields = [
            "pe.event_id",
            "pe.game_id",
            "pe.period", 
            "pe.time_remaining",
            "pe.time_elapsed_seconds",
            "pe.event_type",
            "pe.event_action_type",
            "pe.description",
            "pe.home_score",
            "pe.away_score",
            "pe.score_margin"
        ]
        
        # Add player and team names if joined
        if any("players p" in join for join in self.joins):
            select_fields.append("p.player_name")
        if any("teams t" in join for join in self.joins):
            select_fields.append("t.full_name as team_name")
        if any("assist_player" in join for join in self.joins):
            select_fields.append("ap.player_name as assist_player_name")
        
        query, params = self.build_query(select_fields)
        
        if order_by_time:
            query += " ORDER BY pe.game_id, pe.period, pe.time_elapsed_seconds DESC, pe.event_order"
        
        return query, params
    
    def build_distinct_games_query(self, include_game_details=True):
        """Build query to count distinct games and optionally include game details"""
        # First build the base query to count distinct games
        count_query_parts = [
            "SELECT COUNT(DISTINCT pe.game_id) as unique_games",
            f"FROM {self.base_table}"
        ]
        
        if self.joins:
            count_query_parts.extend(self.joins)
        
        if self.where_conditions:
            count_query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
        
        # Convert parameters dict to ordered list for count query
        param_values = []
        for i in range(1, len(self.parameters) + 1):
            for key, value in self.parameters.items():
                if key == f"param_{i}":
                    param_values.append(value)
                    break
        
        count_query = " ".join(count_query_parts)
        
        if not include_game_details:
            return count_query, param_values
        
        # If game details are requested, also build a query for game breakdown
        details_select_fields = [
            "pe.game_id",
            "eg.game_date",
            "eg.season",
            "COUNT(pe.event_id) as total_plays"
        ]
        
        # Add team information if available
        if any("home_team" in join for join in self.joins):
            details_select_fields.extend(["ht.full_name as home_team"])
        if any("away_team" in join for join in self.joins):
            details_select_fields.extend(["at.full_name as away_team"])
        
        details_query_parts = [
            f"SELECT {', '.join(details_select_fields)}",
            f"FROM {self.base_table}"
        ]
        
        if self.joins:
            details_query_parts.extend(self.joins)
        
        if self.where_conditions:
            details_query_parts.append(f"WHERE {' AND '.join(self.where_conditions)}")
        
        # Group by game to get per-game statistics
        group_by_fields = ["pe.game_id", "eg.game_date", "eg.season"]
        if any("home_team" in join for join in self.joins):
            group_by_fields.append("ht.full_name")
        if any("away_team" in join for join in self.joins):
            group_by_fields.append("at.full_name")
        
        details_query_parts.append(f"GROUP BY {', '.join(group_by_fields)}")
        details_query_parts.append("ORDER BY eg.game_date")
        
        details_query = " ".join(details_query_parts)
        
        # Return both queries
        return {
            'count_query': count_query,
            'details_query': details_query,
            'params': param_values
        }