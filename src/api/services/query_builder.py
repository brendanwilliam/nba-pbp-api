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
                    self.joins.append(f"JOIN teams t ON {base_table_alias}.team_id = t.team_id")
                param_name = self._get_param_name()
                name_conditions = []
                for name in team_names:
                    name_param = self._get_param_name()
                    name_conditions.append(f"(t.team_name ILIKE ${len(self.parameters) + 1} OR t.team_abbreviation ILIKE ${len(self.parameters) + 1})")
                    self.parameters[name_param] = f"%{name}%"
                self.where_conditions.append(f"({' OR '.join(name_conditions)})")
            else:
                # Add join to teams table if needed
                if "teams t" not in " ".join(self.joins):
                    self.joins.append(f"JOIN teams t ON {base_table_alias}.team_id = t.team_id")
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


class TeamQueryBuilder(QueryBuilder):
    """Specialized query builder for team statistics"""
    
    def __init__(self):
        super().__init__("team_game_stats tgs")
        # Add common joins for team queries
        self.joins.extend([
            "JOIN enhanced_games eg ON tgs.game_id = eg.game_id",
            "JOIN teams t ON tgs.team_id = t.team_id"
        ])


class LineupQueryBuilder(QueryBuilder):
    """Specialized query builder for lineup statistics"""
    
    def __init__(self):
        super().__init__("lineup_stats ls")
        # Add common joins for lineup queries
        self.joins.extend([
            "JOIN enhanced_games eg ON ls.game_id = eg.game_id",
            "JOIN teams t ON ls.team_id = t.team_id"
        ])


class ShotQueryBuilder(QueryBuilder):
    """Specialized query builder for shot chart data"""
    
    def __init__(self):
        super().__init__("play_events pe")
        # Add common joins for shot queries
        self.joins.extend([
            "JOIN enhanced_games eg ON pe.game_id = eg.game_id",
            "JOIN players p ON pe.player_id = p.id",
            "JOIN teams t ON pe.team_id = t.team_id"
        ])
        # Add shot-specific conditions
        self.where_conditions.append("pe.event_type IN ('Made Shot', 'Missed Shot')")


class PlayByPlayQueryBuilder(QueryBuilder):
    """Specialized query builder for play-by-play data"""
    
    def __init__(self):
        super().__init__("play_events pe")
        # Add common joins for play-by-play queries
        self.joins.extend([
            "JOIN enhanced_games eg ON pe.game_id = eg.game_id"
        ])
        # Add optional joins that can be enabled based on query needs
        self.optional_joins = {
            "players": "LEFT JOIN players p ON pe.player_id = p.id",
            "teams": "LEFT JOIN teams t ON pe.team_id = t.team_id"
        }
    
    def add_optional_join(self, join_type: str):
        """Add optional joins for additional data"""
        if join_type in self.optional_joins:
            self.joins.append(self.optional_joins[join_type])