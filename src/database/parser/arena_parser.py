"""
Arena Parser Module

Handles extraction of arena and venue information from NBA JSON data.
This includes arena names, locations, capacities, and other venue details.
"""

from typing import Dict, Any, Optional


def extract_arena_info(raw_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract arena information from raw NBA JSON data.
    
    Args:
        raw_json: Raw JSON data from NBA.com game pages
        
    Returns:
        Dictionary containing arena information, or None if no arena data
        
    Keys returned:
        - arena_name: Name of the arena
        - arena_city: City where arena is located
        - arena_state: State/province of arena
        - arena_country: Country code (defaults to 'US')
        - arena_timezone: Timezone of the arena
        - arena_street_address: Street address
        - arena_postal_code: Postal/ZIP code
        - capacity: Arena capacity
    """
    props = raw_json.get('props', {})
    page_props = props.get('pageProps', {})
    game = page_props.get('game', {})
    arena = game.get('arena', {})
    
    if not arena.get('arenaName'):
        return None
        
    return {
        'arena_name': arena.get('arenaName'),
        'arena_city': arena.get('arenaCity'),
        'arena_state': arena.get('arenaState'),
        'arena_country': arena.get('arenaCountry', 'US'),
        'arena_timezone': arena.get('arenaTimezone'),
        'arena_street_address': arena.get('arenaStreetAddress'),
        'arena_postal_code': arena.get('arenaPostalCode'),
        'capacity': arena.get('capacity')
    }