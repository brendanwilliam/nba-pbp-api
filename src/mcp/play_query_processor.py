"""
Play-by-Play Query Processor for NBA MCP Server

Processes natural language queries into play-by-play database queries using the enhanced
PlayByPlayQueryBuilder and natural language translator.
"""

import sys
import os
from typing import Dict, List, Optional, Tuple, Any

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.query_builder import PlayByPlayQueryBuilder
from .query_translator import NaturalLanguageQueryTranslator, QueryContext, QueryType
from .play_response_formatter import PlayResponseFormatter


class PlayQueryProcessor:
    """Processes play-by-play queries from natural language to database results"""
    
    def __init__(self):
        self.translator = NaturalLanguageQueryTranslator()
        self.formatter = PlayResponseFormatter()
    
    async def process_play_query(self, query: str, database_manager) -> str:
        """Process a natural language play-by-play query and return formatted results"""
        try:
            # Translate natural language to structured context
            context = await self.translator.translate_query(query)
            
            # Check confidence
            if context.confidence < 0.3:
                return self.formatter.format_error_response(
                    "I'm not confident I understand your query. Please be more specific.",
                    query
                )
            
            # Build database query based on query type
            query_builder = PlayByPlayQueryBuilder()
            self._configure_query_builder(query_builder, context)
            
            # Execute query based on type
            if context.query_type == QueryType.SHOT_CHART:
                return await self._handle_shot_chart_query(query_builder, context, database_manager, query)
            elif context.query_type == QueryType.SHOT_ANALYSIS:
                return await self._handle_shot_analysis_query(query_builder, context, database_manager, query)
            elif context.query_type == QueryType.PLAYER_PLAYS:
                return await self._handle_player_plays_query(query_builder, context, database_manager, query)
            elif context.query_type == QueryType.CLUTCH_PLAYS:
                return await self._handle_clutch_plays_query(query_builder, context, database_manager, query)
            elif context.query_type == QueryType.TIME_SITUATION:
                return await self._handle_time_situation_query(query_builder, context, database_manager, query)
            elif context.query_type == QueryType.GAME_COUNT:
                return await self._handle_game_count_query(query_builder, context, database_manager, query)
            elif context.query_type == QueryType.PLAY_BY_PLAY:
                return await self._handle_play_sequence_query(query_builder, context, database_manager, query)
            else:
                # Default to play sequence
                return await self._handle_play_sequence_query(query_builder, context, database_manager, query)
        
        except Exception as e:
            return self.formatter.format_error_response(str(e), query)
    
    def _configure_query_builder(self, builder: PlayByPlayQueryBuilder, context: QueryContext):
        """Configure the query builder based on extracted entities"""
        
        # Add player filters
        players = [e.value for e in context.entities if e.entity_type == "player"]
        if players:
            builder.add_optional_join("players")
            # If multiple players, we want OR logic (any of these players)
            if len(players) == 1:
                builder.add_player_filters(player_name=players[0])
            else:
                # Create OR condition for multiple players
                player_conditions = []
                for player in players:
                    param_name = builder._get_param_name()
                    player_conditions.append(f"p.player_name ILIKE ${len(builder.parameters) + 1}")
                    builder.parameters[param_name] = f"%{player}%"
                if player_conditions:
                    builder.where_conditions.append(f"({' OR '.join(player_conditions)})")
        
        # Add team filters
        teams = [e.value for e in context.entities if e.entity_type == "team"]
        if teams:
            # For "vs" queries, the team mentioned is likely the opponent
            # We need to filter for games where this team was involved
            builder.add_optional_join("home_team")
            builder.add_optional_join("away_team")
            
            team_conditions = []
            for team in teams:
                param_name_home = builder._get_param_name()
                param_name_away = builder._get_param_name()
                team_conditions.append(f"(ht.full_name ILIKE ${len(builder.parameters) + 1} OR at.full_name ILIKE ${len(builder.parameters) + 2})")
                builder.parameters[param_name_home] = f"%{team}%"
                builder.parameters[param_name_away] = f"%{team}%"
            
            if team_conditions:
                builder.where_conditions.append(f"({' OR '.join(team_conditions)})")
        
        # Add season filter
        if context.season:
            builder.add_season_filter(context.season)
        
        # Add shot zone filters
        shot_zones = [e.value for e in context.entities if e.entity_type == "shot_zone"]
        if shot_zones:
            builder.add_shot_zone_filters(shot_zones=shot_zones)
        
        # Add event type filters
        event_types = [e.value for e in context.entities if e.entity_type == "event_type"]
        if event_types:
            builder.add_event_type_filters(event_types=event_types)
        
        # Add event action type filters
        event_actions = [e.value for e in context.entities if e.entity_type == "event_action_type"]
        if event_actions:
            # For broader matching, if someone says "dunk", include all dunk types
            expanded_actions = []
            for action in event_actions:
                if "Dunk" in action and action == "Dunk Shot":
                    # If they specified generic "dunk", include all dunk variations
                    expanded_actions.extend([
                        "Dunk Shot", "Slam Dunk Shot", "Driving Dunk Shot", 
                        "Alley Oop Dunk Shot", "Cutting Dunk Shot", "Running Dunk Shot",
                        "Putback Dunk Shot", "Reverse Dunk Shot", "Tip Dunk Shot"
                    ])
                else:
                    expanded_actions.append(action)
            
            builder.add_event_type_filters(event_action_types=expanded_actions)
        
        # Add distance filters
        distance_entities = [e for e in context.entities if e.entity_type == "distance"]
        for dist_entity in distance_entities:
            self._apply_distance_filter(builder, dist_entity.value)
        
        # Add situation filters
        situations = [e.value for e in context.entities if e.entity_type == "situation"]
        for situation in situations:
            self._apply_situation_filter(builder, situation)
        
        # Add time period filters
        time_periods = [e.value for e in context.entities if e.entity_type == "time_period"]
        for time_period in time_periods:
            self._apply_time_period_filter(builder, time_period)
    
    def _apply_distance_filter(self, builder: PlayByPlayQueryBuilder, distance_spec: str):
        """Apply distance filters based on extracted distance specifications"""
        if ":" in distance_spec:
            filter_type, value = distance_spec.split(":", 1)
            
            if filter_type == "distance_exact":
                try:
                    distance = float(value)
                    builder.add_shot_coordinate_filters(
                        shot_distance_min=distance-1, 
                        shot_distance_max=distance+1
                    )
                except ValueError:
                    pass
            elif filter_type == "distance_min":
                try:
                    distance = float(value)
                    builder.add_shot_coordinate_filters(shot_distance_min=distance)
                except ValueError:
                    pass
            elif filter_type == "distance_max":
                try:
                    distance = float(value)
                    builder.add_shot_coordinate_filters(shot_distance_max=distance)
                except ValueError:
                    pass
            elif filter_type == "close_range":
                builder.add_shot_coordinate_filters(shot_distance_max=10)
            elif filter_type == "mid_range":
                builder.add_shot_coordinate_filters(shot_distance_min=10, shot_distance_max=20)
            elif filter_type == "long_range":
                builder.add_shot_coordinate_filters(shot_distance_min=20)
    
    def _apply_situation_filter(self, builder: PlayByPlayQueryBuilder, situation: str):
        """Apply situation-based filters"""
        if situation == "first_quarter":
            builder.add_time_filters(period=1)
        elif situation == "second_quarter":
            builder.add_time_filters(period=2)
        elif situation == "third_quarter":
            builder.add_time_filters(period=3)
        elif situation == "fourth_quarter":
            builder.add_time_filters(period=4)
        elif situation == "crunch_time":
            builder.add_time_filters(crunch_time=True)
        elif situation == "clutch":
            builder.add_clutch_situation_filters()
        elif situation == "close_game":
            builder.add_score_context_filters(close_game=True)
        elif situation == "blowout":
            builder.add_score_context_filters(blowout_threshold=15)
        elif situation == "overtime":
            builder.add_time_filters(period=[5, 6, 7, 8, 9, 10])  # OT periods
    
    def _apply_time_period_filter(self, builder: PlayByPlayQueryBuilder, time_period: str):
        """Apply time period filters"""
        if "quarter" in time_period:
            # Extract quarter number
            if "1st" in time_period or "first" in time_period:
                builder.add_time_filters(period=1)
            elif "2nd" in time_period or "second" in time_period:
                builder.add_time_filters(period=2)
            elif "3rd" in time_period or "third" in time_period:
                builder.add_time_filters(period=3)
            elif "4th" in time_period or "fourth" in time_period:
                builder.add_time_filters(period=4)
        elif time_period == "playoffs":
            builder.add_game_type_filter("playoff")
        elif time_period == "regular_season":
            builder.add_game_type_filter("regular")
    
    async def _handle_shot_chart_query(self, builder: PlayByPlayQueryBuilder, context: QueryContext, 
                                     db_manager, original_query: str) -> str:
        """Handle shot chart specific queries"""
        # Ensure we have shot data
        builder.add_event_type_filters(event_types=["Made Shot", "Missed Shot"])
        
        # Build shot chart query
        sql, params = builder.build_shot_chart_query(include_coordinates=True, include_zones=True)
        
        # Execute query
        results = await db_manager.execute_query(sql, *params)
        
        return self.formatter.format_shot_chart_response(results, original_query)
    
    async def _handle_shot_analysis_query(self, builder: PlayByPlayQueryBuilder, context: QueryContext,
                                        db_manager, original_query: str) -> str:
        """Handle shot analysis queries"""
        # Focus on shot events
        builder.add_event_type_filters(event_types=["Made Shot", "Missed Shot"])
        
        sql, params = builder.build_shot_chart_query(include_coordinates=True, include_zones=True)
        results = await db_manager.execute_query(sql, *params)
        
        return self.formatter.format_shot_analysis_response(results, "shot_analysis")
    
    async def _handle_player_plays_query(self, builder: PlayByPlayQueryBuilder, context: QueryContext,
                                       db_manager, original_query: str) -> str:
        """Handle player-specific play queries"""
        # Get player name from context
        players = [e.value for e in context.entities if e.entity_type == "player"]
        player_name = players[0] if players else "Unknown Player"
        
        # Add player join
        builder.add_optional_join("players")
        
        sql, params = builder.build_play_sequence_query(order_by_time=True)
        results = await db_manager.execute_query(sql, *params)
        
        return self.formatter.format_player_plays_response(results, player_name, original_query)
    
    async def _handle_clutch_plays_query(self, builder: PlayByPlayQueryBuilder, context: QueryContext,
                                       db_manager, original_query: str) -> str:
        """Handle clutch/crunch time play queries"""
        # Add clutch situation filters
        builder.add_clutch_situation_filters()
        builder.add_optional_join("players")
        
        sql, params = builder.build_play_sequence_query(order_by_time=True)
        results = await db_manager.execute_query(sql, *params)
        
        return self.formatter.format_clutch_plays_response(results, original_query)
    
    async def _handle_time_situation_query(self, builder: PlayByPlayQueryBuilder, context: QueryContext,
                                         db_manager, original_query: str) -> str:
        """Handle time-specific situation queries"""
        builder.add_optional_join("players")
        
        # If the query mentions shots, filter for shot events
        if any(word in original_query.lower() for word in ['shot', 'shots', '3-pointer', 'three']):
            builder.add_event_type_filters(event_types=['Made Shot', 'Missed Shot'])
        
        sql, params = builder.build_play_sequence_query(order_by_time=True)
        results = await db_manager.execute_query(sql, *params)
        
        return self.formatter.format_play_sequence_response(results, original_query)
    
    async def _handle_play_sequence_query(self, builder: PlayByPlayQueryBuilder, context: QueryContext,
                                        db_manager, original_query: str) -> str:
        """Handle general play-by-play sequence queries"""
        # Add optional joins for rich data
        builder.add_optional_join("players")
        builder.add_optional_join("teams")
        
        sql, params = builder.build_play_sequence_query(order_by_time=True)
        results = await db_manager.execute_query(sql, *params)
        
        return self.formatter.format_play_sequence_response(results, original_query)
    
    async def _handle_game_count_query(self, builder: PlayByPlayQueryBuilder, context: QueryContext,
                                     db_manager, original_query: str) -> str:
        """Handle queries asking for unique game counts"""
        # Add joins for team information to show game details
        builder.add_optional_join("home_team")
        builder.add_optional_join("away_team")
        
        # Get both count and details
        query_result = builder.build_distinct_games_query(include_game_details=True)
        
        # Execute count query
        count_result = await db_manager.execute_query(query_result['count_query'], *query_result['params'])
        unique_games = count_result[0]['unique_games'] if count_result else 0
        
        # Execute details query for breakdown
        details_results = await db_manager.execute_query(query_result['details_query'], *query_result['params'])
        
        return self.formatter.format_game_count_response(
            unique_games, details_results, context, original_query
        )