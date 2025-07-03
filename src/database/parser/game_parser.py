"""
Game Parser Module

Handles extraction of basic game information and metadata from NBA JSON data.
This includes game timing, scores, teams, and general game context.
"""

from typing import Dict, Any, Optional
from datetime import datetime


def extract_game_basic_info(raw_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract basic game information from raw NBA JSON data.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        
    Returns:
        Dictionary containing game basic information, or None if invalid data
        
    Keys returned:
        - game_id: NBA game identifier
        - game_code: Game code format (YYYYMMDD/TEAMTEAM)
        - game_status: Game status (1=scheduled, 2=live, 3=final)
        - game_status_text: Human readable status
        - season: Season format (YYYY-YY)
        - game_date: Game date as date object
        - game_time_utc: Game time in UTC
        - game_time_et: Game time in Eastern Time
        - home_team_id: Home team NBA ID
        - away_team_id: Away team NBA ID
        - home_score: Home team final score
        - away_score: Away team final score
        - period: Current/final period
        - game_clock: Game clock time
        - duration: Game duration
        - attendance: Attendance figure
        - sellout: Boolean sellout indicator
        - series_game_number: Playoff series game number
        - game_label: Game label (playoffs)
        - game_sub_label: Game sub label
        - series_text: Series description text
        - if_necessary: Boolean if game was if-necessary
        - is_neutral: Boolean neutral site indicator
    """
    props = raw_json.get('props', {})
    page_props = props.get('pageProps', {})
    game = page_props.get('game', {})
    
    # If no game object exists, this is likely a schedule/template page, not actual game data
    if not game or not game.get('gameId'):
        return None
    
    # Convert sellout to boolean (handle various formats)
    sellout_value = game.get('sellout')
    if isinstance(sellout_value, (int, str)):
        sellout = sellout_value in (1, '1', 'true', 'True', True)
    else:
        sellout = bool(sellout_value) if sellout_value is not None else False
    
    # Convert if_necessary to boolean
    if_necessary_value = game.get('ifNecessary')
    if isinstance(if_necessary_value, (int, str)):
        if_necessary = if_necessary_value in (1, '1', 'true', 'True', True)
    else:
        if_necessary = bool(if_necessary_value) if if_necessary_value is not None else False
    
    # Parse game_date first (we'll need it for season derivation)
    game_date = game.get('gameDate')
    parsed_game_date = None
    
    # Try to extract date from game_time_utc if gameDate is missing
    if not game_date:
        game_time_utc = game.get('gameTimeUTC')
        if game_time_utc:
            try:
                dt = datetime.fromisoformat(game_time_utc.replace('Z', '+00:00'))
                parsed_game_date = dt.date()
                game_date = dt.strftime('%Y-%m-%d')  # For season calculation
            except ValueError:
                pass
    
    if isinstance(game_date, str) and game_date and not parsed_game_date:
        try:
            # Convert from string format like "2004-03-20" to date
            parsed_game_date = datetime.strptime(game_date[:10], '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Extract or derive season
    season = game.get('season')
    if not season:
        # Try to derive from game_id (format: 0021700001 = 2017-18 season)
        game_id = game.get('gameId', '')
        if game_id and len(game_id) >= 5:
            try:
                year_code = int(game_id[3:5])  # Extract 2-digit year code from positions 3-4
                
                # Convert 2-digit year to 4-digit year
                if year_code >= 96:  # 1996-97 season onwards (96, 97, 98, 99)
                    start_year = 1900 + year_code
                else:  # 00-99 maps to 2000-2099
                    start_year = 2000 + year_code
                    
                end_year = start_year + 1
                season = f"{start_year}-{str(end_year)[2:]}"  # Convert to season format (e.g., "2017-18")
            except (ValueError, IndexError):
                season = None
        
        # Fallback: derive from date if available
        if not season and game_date:
            try:
                date_year = int(game_date[:4])
                # NBA season spans two years, games after June are next season
                month = int(game_date[5:7]) if len(game_date) >= 7 else 12
                if month >= 7:  # July onwards is new season
                    season = f"{date_year}-{str(date_year+1)[2:]}"
                else:  # January-June is previous season
                    season = f"{date_year-1}-{str(date_year)[2:]}"
            except (ValueError, IndexError):
                season = "unknown"
        
        if not season:
            season = "unknown"
    
    return {
        'game_id': game.get('gameId'),
        'game_code': game.get('gameCode'),
        'game_status': game.get('gameStatus'),
        'game_status_text': game.get('gameStatusText'),
        'season': season,
        'game_date': parsed_game_date,
        'game_time_utc': game.get('gameTimeUTC'),
        'game_time_et': game.get('gameTimeET'),
        'home_team_id': game.get('homeTeam', {}).get('teamId'),
        'away_team_id': game.get('awayTeam', {}).get('teamId'),
        'home_score': game.get('homeTeam', {}).get('score'),
        'away_score': game.get('awayTeam', {}).get('score'),
        'period': game.get('period'),
        'game_clock': game.get('gameClock'),
        'duration': game.get('duration'),
        'attendance': game.get('attendance'),
        'sellout': sellout,
        'series_game_number': game.get('seriesGameNumber'),
        'game_label': game.get('gameLabel'),
        'game_sub_label': game.get('gameSubLabel'),
        'series_text': game.get('seriesText'),
        'if_necessary': if_necessary,
        'is_neutral': bool(game.get('neutralSite', False))
    }