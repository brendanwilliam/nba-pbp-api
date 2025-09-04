"""
Utility functions for WNBA game ID parsing and analysis.
"""

def parse_game_id(game_id: int) -> dict:
    """
    Parse WNBA game ID to extract season and game type information.
    
    WNBA game IDs follow format: 10SYY00GGG where:
    - 10 = League prefix (WNBA)
    - S = Season type (2=regular, 4=playoff) 
    - YY = Year (24=2024, 23=2023, etc.)
    - 00 = Fixed padding
    - GGG = Game number
    
    Args:
        game_id: Integer game ID
        
    Returns:
        dict: Contains 'season' (int) and 'game_type' (str)
        
    Examples:
        >>> parse_game_id(1022400001)
        {'season': 2024, 'game_type': 'regular'}
        
        >>> parse_game_id(1042300302) 
        {'season': 2023, 'game_type': 'playoff'}
        
        >>> parse_game_id(1029700003)
        {'season': 1997, 'game_type': 'regular'}
    """
    game_id_str = str(game_id)
    
    # Default values for malformed IDs
    result = {'season': None, 'game_type': None}
    
    # Validate basic format (should be 10 digits starting with 10)
    if len(game_id_str) != 10 or not game_id_str.startswith('10'):
        return result
    
    try:
        # Extract season type (position 2)
        season_type_digit = game_id_str[2]
        if season_type_digit == '2':
            game_type = 'regular'
        elif season_type_digit == '4':
            game_type = 'playoff'
        else:
            # Unknown season type, but continue parsing
            game_type = 'unknown'
        
        # Extract year (positions 3-4)
        year_suffix = int(game_id_str[3:5])
        
        # Convert YY to full year
        if year_suffix >= 97:  # 1997-1999
            season = 1900 + year_suffix
        else:  # 2000+
            season = 2000 + year_suffix
            
        result['season'] = season
        result['game_type'] = game_type
        
    except (ValueError, IndexError):
        # Return None values if parsing fails
        pass
    
    return result


def determine_season_from_game_id(game_id: int) -> int:
    """
    Extract just the season from a game ID.
    
    Args:
        game_id: Integer game ID
        
    Returns:
        int: Season year or None if parsing fails
    """
    return parse_game_id(game_id)['season']


def determine_game_type_from_game_id(game_id: int) -> str:
    """
    Extract just the game type from a game ID.
    
    Args:
        game_id: Integer game ID
        
    Returns:
        str: 'regular', 'playoff', 'unknown', or None if parsing fails
    """
    return parse_game_id(game_id)['game_type']