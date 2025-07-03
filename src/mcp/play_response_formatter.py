"""
Play-by-Play Response Formatter for NBA MCP Server

Handles rich formatting of play-by-play data including shot charts, play sequences,
and statistical summaries.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class ShotData:
    """Represents a single shot with all relevant data"""
    event_id: int
    player_name: str
    team_name: str
    shot_x: float
    shot_y: float
    shot_distance: float
    shot_made: bool
    shot_type: str
    shot_zone: str
    period: int
    time_remaining: str
    home_score: int
    away_score: int
    game_date: str
    season: str


@dataclass
class PlayEvent:
    """Represents a play-by-play event"""
    event_id: int
    game_id: str
    period: int
    time_remaining: str
    event_type: str
    description: str
    player_name: Optional[str]
    team_name: Optional[str]
    home_score: int
    away_score: int
    score_margin: int


class PlayResponseFormatter:
    """Formats play-by-play data into rich, readable responses"""
    
    def format_shot_chart_response(self, shots: List[Dict], query_context: str = "") -> str:
        """Format shot chart data with coordinates and analysis"""
        if not shots:
            return f"No shots found for query: {query_context}"
        
        # Convert to ShotData objects
        shot_data = []
        for shot in shots:
            try:
                shot_data.append(ShotData(
                    event_id=shot.get('event_id', 0),
                    player_name=shot.get('player_name', 'Unknown'),
                    team_name=shot.get('team_name', 'Unknown'),
                    shot_x=float(shot.get('shot_x', 0)),
                    shot_y=float(shot.get('shot_y', 0)),
                    shot_distance=float(shot.get('shot_distance', 0)),
                    shot_made=bool(shot.get('shot_made', False)),
                    shot_type=shot.get('shot_type', 'Unknown'),
                    shot_zone=shot.get('shot_zone', 'Unknown'),
                    period=int(shot.get('period', 1)),
                    time_remaining=shot.get('time_remaining', '00:00'),
                    home_score=int(shot.get('home_score', 0)),
                    away_score=int(shot.get('away_score', 0)),
                    game_date=shot.get('game_date', ''),
                    season=shot.get('season', '')
                ))
            except (ValueError, TypeError):
                continue  # Skip malformed data
        
        if not shot_data:
            return "No valid shot data found"
        
        # Build response
        response = f"**Shot Chart Analysis**\n"
        if query_context:
            response += f"Query: {query_context}\n"
        response += f"Total Shots: {len(shot_data)}\n\n"
        
        # Calculate shooting statistics
        made_shots = [s for s in shot_data if s.shot_made]
        response += f"**Shooting Summary:**\n"
        response += f"• Made: {len(made_shots)}/{len(shot_data)} ({len(made_shots)/len(shot_data)*100:.1f}%)\n"
        
        # Zone breakdown
        zone_stats = {}
        for shot in shot_data:
            zone = shot.shot_zone
            if zone not in zone_stats:
                zone_stats[zone] = {'made': 0, 'attempted': 0}
            zone_stats[zone]['attempted'] += 1
            if shot.shot_made:
                zone_stats[zone]['made'] += 1
        
        response += f"\n**By Zone:**\n"
        for zone, stats in zone_stats.items():
            pct = stats['made'] / stats['attempted'] * 100 if stats['attempted'] > 0 else 0
            response += f"• {zone}: {stats['made']}/{stats['attempted']} ({pct:.1f}%)\n"
        
        # Distance analysis
        distances = [s.shot_distance for s in shot_data if s.shot_distance > 0]
        if distances:
            avg_distance = sum(distances) / len(distances)
            max_distance = max(distances)
            min_distance = min(distances)
            response += f"\n**Distance Analysis:**\n"
            response += f"• Average: {avg_distance:.1f} feet\n"
            response += f"• Range: {min_distance:.1f} - {max_distance:.1f} feet\n"
        
        # Sample shots with coordinates
        response += f"\n**Shot Coordinates (Sample):**\n"
        sample_shots = shot_data[:5]  # First 5 shots
        for i, shot in enumerate(sample_shots, 1):
            status = "✓" if shot.shot_made else "✗"
            response += f"{i}. {status} {shot.player_name} - ({shot.shot_x:.1f}, {shot.shot_y:.1f}) - {shot.shot_distance:.1f}ft\n"
        
        if len(shot_data) > 5:
            response += f"... and {len(shot_data) - 5} more shots\n"
        
        return response
    
    def format_play_sequence_response(self, plays: List[Dict], query_context: str = "") -> str:
        """Format play-by-play sequence with timeline"""
        if not plays:
            return f"No plays found for query: {query_context}"
        
        # Convert to PlayEvent objects
        play_events = []
        for play in plays:
            try:
                play_events.append(PlayEvent(
                    event_id=play.get('event_id', 0),
                    game_id=play.get('game_id', ''),
                    period=int(play.get('period', 1)),
                    time_remaining=play.get('time_remaining', '00:00'),
                    event_type=play.get('event_type', 'Unknown'),
                    description=play.get('description', ''),
                    player_name=play.get('player_name'),
                    team_name=play.get('team_name'),
                    home_score=int(play.get('home_score') or 0),
                    away_score=int(play.get('away_score') or 0),
                    score_margin=int(play.get('score_margin') or 0)
                ))
            except (ValueError, TypeError):
                continue
        
        if not play_events:
            return "No valid play data found"
        
        response = f"**Play-by-Play Sequence**\n"
        if query_context:
            response += f"Query: {query_context}\n"
        response += f"Total Events: {len(play_events)}\n\n"
        
        # Group by period
        periods = {}
        for play in play_events:
            period = play.period
            if period not in periods:
                periods[period] = []
            periods[period].append(play)
        
        # Format by period
        for period in sorted(periods.keys()):
            period_name = f"Q{period}" if period <= 4 else f"OT{period-4}"
            response += f"**{period_name}:**\n"
            
            period_plays = periods[period]
            for play in period_plays[:10]:  # Limit to 10 plays per period for readability
                score_display = f"{play.home_score}-{play.away_score}"
                player_info = f" ({play.player_name})" if play.player_name else ""
                team_info = f" - {play.team_name}" if play.team_name else ""
                
                response += f"• {play.time_remaining} - {play.event_type}{player_info}{team_info} [{score_display}]\n"
                if play.description:
                    response += f"  {play.description}\n"
            
            if len(period_plays) > 10:
                response += f"  ... and {len(period_plays) - 10} more plays in {period_name}\n"
            response += "\n"
        
        return response
    
    def format_player_plays_response(self, plays: List[Dict], player_name: str, query_context: str = "") -> str:
        """Format plays specifically for a player"""
        if not plays:
            return f"No plays found for {player_name}"
        
        response = f"**{player_name} - Play Analysis**\n"
        if query_context:
            response += f"Query: {query_context}\n"
        response += f"Total Plays: {len(plays)}\n\n"
        
        # Categorize plays by type
        play_types = {}
        for play in plays:
            event_type = play.get('event_type', 'Unknown')
            if event_type not in play_types:
                play_types[event_type] = []
            play_types[event_type].append(play)
        
        # Summary by play type
        response += "**Play Type Summary:**\n"
        for play_type in sorted(play_types.keys()):
            count = len(play_types[play_type])
            response += f"• {play_type}: {count}\n"
        
        # Shooting breakdown if shots exist
        shots = play_types.get('Made Shot', []) + play_types.get('Missed Shot', [])
        if shots:
            made_shots = len(play_types.get('Made Shot', []))
            total_shots = len(shots)
            response += f"\n**Shooting:**\n"
            response += f"• Made: {made_shots}/{total_shots} ({made_shots/total_shots*100:.1f}%)\n"
        
        # Recent plays
        response += f"\n**Recent Plays:**\n"
        for i, play in enumerate(plays[:8], 1):  # Show first 8 plays
            period = play.get('period', 1)
            time = play.get('time_remaining', '00:00')
            event_type = play.get('event_type', 'Unknown')
            description = play.get('description', '')
            
            period_name = f"Q{period}" if period <= 4 else f"OT{period-4}"
            response += f"{i}. {period_name} {time} - {event_type}\n"
            if description:
                response += f"   {description}\n"
        
        if len(plays) > 8:
            response += f"... and {len(plays) - 8} more plays\n"
        
        return response
    
    def format_clutch_plays_response(self, plays: List[Dict], query_context: str = "") -> str:
        """Format clutch/crunch time plays with score context"""
        if not plays:
            return f"No clutch plays found"
        
        response = f"**Clutch Plays Analysis**\n"
        if query_context:
            response += f"Query: {query_context}\n"
        response += f"Total Clutch Plays: {len(plays)}\n\n"
        
        # Score context analysis
        close_plays = [p for p in plays if abs(p.get('score_margin', 100)) <= 5]
        response += f"**Score Context:**\n"
        response += f"• Plays within 5 points: {len(close_plays)}\n"
        
        # Key moments
        response += f"\n**Key Moments:**\n"
        
        # Sort by score margin (closest games first)
        plays_sorted = sorted(plays, key=lambda x: abs(x.get('score_margin', 100)))
        
        for i, play in enumerate(plays_sorted[:6], 1):  # Top 6 clutch moments
            period = play.get('period', 1)
            time = play.get('time_remaining', '00:00')
            event_type = play.get('event_type', 'Unknown')
            player = play.get('player_name', 'Unknown')
            margin = play.get('score_margin', 0)
            home_score = play.get('home_score', 0)
            away_score = play.get('away_score', 0)
            
            period_name = f"Q{period}" if period <= 4 else f"OT{period-4}"
            margin_text = f"Tied" if margin == 0 else f"{abs(margin)}pt {'lead' if margin > 0 else 'deficit'}"
            
            response += f"{i}. {period_name} {time} - {event_type} by {player}\n"
            response += f"   Score: {home_score}-{away_score} ({margin_text})\n"
        
        return response
    
    def format_shot_analysis_response(self, shots: List[Dict], analysis_type: str = "general") -> str:
        """Format detailed shot analysis"""
        if not shots:
            return "No shots found for analysis"
        
        response = f"**Shot Analysis - {analysis_type.title()}**\n"
        response += f"Total Shots Analyzed: {len(shots)}\n\n"
        
        # Basic shooting stats
        made_shots = [s for s in shots if s.get('shot_made', False)]
        response += f"**Overall Shooting:**\n"
        response += f"• Made: {len(made_shots)}/{len(shots)} ({len(made_shots)/len(shots)*100:.1f}%)\n"
        
        # Distance breakdown
        distance_ranges = {
            "At Rim (0-3ft)": [0, 3],
            "Short (3-10ft)": [3, 10],
            "Mid Range (10-20ft)": [10, 20],
            "Long Range (20-30ft)": [20, 30],
            "Beyond 30ft": [30, 100]
        }
        
        response += f"\n**By Distance:**\n"
        for range_name, (min_dist, max_dist) in distance_ranges.items():
            range_shots = [s for s in shots 
                          if min_dist <= s.get('shot_distance', 0) < max_dist]
            if range_shots:
                made = len([s for s in range_shots if s.get('shot_made', False)])
                pct = made / len(range_shots) * 100 if range_shots else 0
                response += f"• {range_name}: {made}/{len(range_shots)} ({pct:.1f}%)\n"
        
        # Shot type breakdown
        shot_types = {}
        for shot in shots:
            shot_type = shot.get('shot_type', 'Unknown')
            if shot_type not in shot_types:
                shot_types[shot_type] = {'made': 0, 'attempted': 0}
            shot_types[shot_type]['attempted'] += 1
            if shot.get('shot_made', False):
                shot_types[shot_type]['made'] += 1
        
        response += f"\n**By Shot Type:**\n"
        for shot_type, stats in shot_types.items():
            if stats['attempted'] > 0:
                pct = stats['made'] / stats['attempted'] * 100
                response += f"• {shot_type}: {stats['made']}/{stats['attempted']} ({pct:.1f}%)\n"
        
        return response
    
    def format_game_count_response(self, unique_games: int, game_details: List[Dict], 
                                 context, query: str = "") -> str:
        """Format game count response with breakdown of unique games"""
        response = f"**Game Count Analysis**\n"
        if query:
            response += f"Query: {query}\n"
        
        # Extract player and team names from context for better display
        players = [e.value for e in context.entities if e.entity_type == "player"]
        teams = [e.value for e in context.entities if e.entity_type == "team"]
        season = context.season
        
        # Build context description
        context_parts = []
        if players:
            if len(players) == 1:
                context_parts.append(f"Player: {players[0]}")
            else:
                context_parts.append(f"Players: {', '.join(players)}")
        
        if teams:
            if len(teams) == 1:
                context_parts.append(f"vs {teams[0]}")
            else:
                context_parts.append(f"Teams: {', '.join(teams)}")
        
        if season:
            context_parts.append(f"Season: {season}")
        
        if context_parts:
            response += f"Context: {', '.join(context_parts)}\n"
        
        response += f"\n**Total Unique Games: {unique_games}**\n\n"
        
        if unique_games == 0:
            response += "No games found matching the specified criteria.\n"
            response += "\n**Suggestions:**\n"
            response += "• Check player/team name spelling\n"
            response += "• Verify the season format (e.g., '2023-24')\n"
            response += "• Try a different season or broader criteria\n"
            return response
        
        if not game_details:
            return response
        
        # Group games by season
        games_by_season = {}
        total_plays = 0
        
        for game in game_details:
            game_season = game.get('season', 'Unknown')
            if game_season not in games_by_season:
                games_by_season[game_season] = []
            games_by_season[game_season].append(game)
            total_plays += game.get('total_plays', 0)
        
        # Season breakdown
        if len(games_by_season) > 1:
            response += "**Games by Season:**\n"
            for season in sorted(games_by_season.keys()):
                season_games = games_by_season[season]
                response += f"• {season}: {len(season_games)} games\n"
            response += "\n"
        
        # Game details (limit to prevent overwhelming output)
        response += "**Game Details:**\n"
        display_limit = min(10, len(game_details))  # Show max 10 games
        
        for i, game in enumerate(game_details[:display_limit], 1):
            game_id = game.get('game_id', 'Unknown')
            game_date = game.get('game_date', 'Unknown')
            game_season = game.get('season', 'Unknown')
            plays_count = game.get('total_plays', 0)
            
            # Format date if available
            date_display = game_date
            try:
                if game_date and game_date != 'Unknown':
                    from datetime import datetime
                    if isinstance(game_date, str):
                        # Try to parse and format date
                        parsed_date = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                        date_display = parsed_date.strftime("%m/%d/%Y")
            except:
                pass
            
            # Include team info if available
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            team_info = ""
            if home_team and away_team:
                team_info = f" ({away_team} @ {home_team})"
            
            response += f"{i}. {date_display} - {game_season}{team_info}\n"
            response += f"   Game ID: {game_id} | Plays: {plays_count}\n"
        
        if len(game_details) > display_limit:
            response += f"... and {len(game_details) - display_limit} more games\n"
        
        # Summary statistics
        response += f"\n**Summary:**\n"
        response += f"• Total Games: {unique_games}\n"
        response += f"• Total Plays: {total_plays:,}\n"
        if unique_games > 0:
            avg_plays = total_plays / unique_games
            response += f"• Average Plays per Game: {avg_plays:.1f}\n"
        
        # Season coverage
        seasons = sorted(set(game.get('season', 'Unknown') for game in game_details))
        if len(seasons) > 1:
            response += f"• Season Coverage: {seasons[0]} to {seasons[-1]}\n"
        elif seasons:
            response += f"• Season: {seasons[0]}\n"
        
        return response
    
    def format_error_response(self, error_message: str, query: str = "") -> str:
        """Format error responses consistently"""
        response = "**Query Processing Error**\n\n"
        if query:
            response += f"Query: {query}\n"
        response += f"Error: {error_message}\n\n"
        response += "**Suggestions:**\n"
        response += "• Try rephrasing your query\n"
        response += "• Specify player names or team names clearly\n"
        response += "• Check season format (e.g., '2023-24')\n"
        response += "• Use specific time periods (e.g., '4th quarter', 'overtime')\n"
        
        return response