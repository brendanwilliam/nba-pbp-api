"""
NBA Team Abbreviation Mapping (1996-2025)
Handles team relocations, name changes, and historical abbreviations
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime


class NBATeamMapping:
    """Comprehensive NBA team abbreviation mapping with historical changes."""
    
    # Current NBA teams (2024-25 season)
    CURRENT_TEAMS = {
        'ATL': {'name': 'Atlanta Hawks', 'city': 'Atlanta'},
        'BOS': {'name': 'Boston Celtics', 'city': 'Boston'},
        'BKN': {'name': 'Brooklyn Nets', 'city': 'Brooklyn'},
        'CHA': {'name': 'Charlotte Hornets', 'city': 'Charlotte'},
        'CHI': {'name': 'Chicago Bulls', 'city': 'Chicago'},
        'CLE': {'name': 'Cleveland Cavaliers', 'city': 'Cleveland'},
        'DAL': {'name': 'Dallas Mavericks', 'city': 'Dallas'},
        'DEN': {'name': 'Denver Nuggets', 'city': 'Denver'},
        'DET': {'name': 'Detroit Pistons', 'city': 'Detroit'},
        'GSW': {'name': 'Golden State Warriors', 'city': 'Golden State'},
        'HOU': {'name': 'Houston Rockets', 'city': 'Houston'},
        'IND': {'name': 'Indiana Pacers', 'city': 'Indiana'},
        'LAC': {'name': 'LA Clippers', 'city': 'Los Angeles'},
        'LAL': {'name': 'Los Angeles Lakers', 'city': 'Los Angeles'},
        'MEM': {'name': 'Memphis Grizzlies', 'city': 'Memphis'},
        'MIA': {'name': 'Miami Heat', 'city': 'Miami'},
        'MIL': {'name': 'Milwaukee Bucks', 'city': 'Milwaukee'},
        'MIN': {'name': 'Minnesota Timberwolves', 'city': 'Minnesota'},
        'NOP': {'name': 'New Orleans Pelicans', 'city': 'New Orleans'},
        'NYK': {'name': 'New York Knicks', 'city': 'New York'},
        'OKC': {'name': 'Oklahoma City Thunder', 'city': 'Oklahoma City'},
        'ORL': {'name': 'Orlando Magic', 'city': 'Orlando'},
        'PHI': {'name': 'Philadelphia 76ers', 'city': 'Philadelphia'},
        'PHX': {'name': 'Phoenix Suns', 'city': 'Phoenix'},
        'POR': {'name': 'Portland Trail Blazers', 'city': 'Portland'},
        'SAC': {'name': 'Sacramento Kings', 'city': 'Sacramento'},
        'SAS': {'name': 'San Antonio Spurs', 'city': 'San Antonio'},
        'TOR': {'name': 'Toronto Raptors', 'city': 'Toronto'},
        'UTA': {'name': 'Utah Jazz', 'city': 'Utah'},
        'WAS': {'name': 'Washington Wizards', 'city': 'Washington'},
    }
    
    # Historical team changes (year: {old_code: new_code})
    TEAM_RELOCATIONS = {
        2008: {'SEA': 'OKC'},  # Seattle SuperSonics → Oklahoma City Thunder
        2012: {'NJN': 'BKN'},  # New Jersey Nets → Brooklyn Nets
        2002: {'CHA': 'NOH'},  # Charlotte Hornets → New Orleans Hornets (original)
        2013: {'NOH': 'NOP'},  # New Orleans Hornets → New Orleans Pelicans
        2014: {'CHA': 'CHA'},  # Charlotte Bobcats → Charlotte Hornets (reclaimed)
        2001: {'VAN': 'MEM'},  # Vancouver Grizzlies → Memphis Grizzlies
    }
    
    # Name changes without relocation
    TEAM_NAME_CHANGES = {
        1997: {'WAS': 'WAS'},  # Washington Bullets → Washington Wizards
    }
    
    # Expansion teams by season
    EXPANSION_TEAMS = {
        '1988-89': ['CHA', 'MIA'],
        '1989-90': ['ORL', 'MIN'],
        '1995-96': ['TOR', 'VAN'],  # Vancouver later became Memphis
        '2004-05': ['CHA'],  # Charlotte returned as Bobcats
    }
    
    # Teams that no longer exist
    DEFUNCT_TEAMS = {
        'SEA': {'name': 'Seattle SuperSonics', 'active_until': 2008},
        'NJN': {'name': 'New Jersey Nets', 'active_until': 2012},
        'NOH': {'name': 'New Orleans Hornets', 'active_until': 2013},
        'VAN': {'name': 'Vancouver Grizzlies', 'active_until': 2001},
        'NOK': {'name': 'New Orleans/Oklahoma City Hornets', 'active_until': 2007},  # Katrina relocation
    }
    
    # Special cases and alternative abbreviations
    ALTERNATIVE_ABBREVIATIONS = {
        'BRK': 'BKN',  # Brooklyn alternative
        'NOR': 'NOP',  # New Orleans alternative
        'GS': 'GSW',   # Golden State alternative
        'SA': 'SAS',   # San Antonio alternative
        'NO': 'NOP',   # New Orleans short form
    }
    
    def get_team_for_season(self, tricode: str, season: str) -> Optional[Dict[str, str]]:
        """Get team info for a specific season, handling historical changes."""
        season_year = int(season.split('-')[0])
        
        # Handle alternative abbreviations
        normalized_code = self.ALTERNATIVE_ABBREVIATIONS.get(tricode, tricode)
        
        # Check if it's a current team
        if normalized_code in self.CURRENT_TEAMS:
            return {
                'tricode': normalized_code,
                **self.CURRENT_TEAMS[normalized_code],
                'season': season
            }
        
        # Check historical relocations
        for year, relocations in self.TEAM_RELOCATIONS.items():
            if season_year < year and tricode in relocations.values():
                # Find the old code that became this new code
                old_code = next(old for old, new in relocations.items() if new == tricode)
                if old_code in self.DEFUNCT_TEAMS:
                    return {
                        'tricode': tricode,
                        **self.DEFUNCT_TEAMS[old_code],
                        'season': season,
                        'historical': True
                    }
            elif season_year >= year and tricode in relocations:
                # This team was relocated, use new code
                new_code = relocations[tricode]
                if new_code in self.CURRENT_TEAMS:
                    return {
                        'tricode': new_code,
                        **self.CURRENT_TEAMS[new_code],
                        'season': season,
                        'relocated_from': tricode
                    }
        
        # Check defunct teams
        if tricode in self.DEFUNCT_TEAMS:
            defunct_info = self.DEFUNCT_TEAMS[tricode]
            if season_year <= defunct_info['active_until']:
                return {
                    'tricode': tricode,
                    **defunct_info,
                    'season': season,
                    'defunct': True
                }
        
        return None
    
    def get_all_teams_for_season(self, season: str) -> List[str]:
        """Get all active team codes for a specific season."""
        season_year = int(season.split('-')[0])
        active_teams = []
        
        # Start with current teams
        for tricode in self.CURRENT_TEAMS.keys():
            active_teams.append(tricode)
        
        # Add historical teams that were active in this season
        for tricode, info in self.DEFUNCT_TEAMS.items():
            if season_year <= info['active_until']:
                active_teams.append(tricode)
        
        # Remove teams that were relocated before this season
        for year, relocations in self.TEAM_RELOCATIONS.items():
            if season_year >= year:
                for old_code in relocations.keys():
                    if old_code in active_teams:
                        active_teams.remove(old_code)
        
        # Special handling for Charlotte Hornets/Bobcats
        if season_year >= 2014:
            # Charlotte Hornets name reclaimed in 2014
            if 'CHA' not in active_teams:
                active_teams.append('CHA')
        elif 2004 <= season_year < 2014:
            # Charlotte Bobcats era (use CHA code for simplicity)
            if 'CHA' not in active_teams:
                active_teams.append('CHA')
        
        return sorted(active_teams)
    
    def validate_team_code(self, tricode: str, season: str) -> bool:
        """Validate if a team code was active in a given season."""
        return self.get_team_for_season(tricode, season) is not None
    
    def normalize_team_code(self, tricode: str) -> str:
        """Normalize team code to standard form."""
        return self.ALTERNATIVE_ABBREVIATIONS.get(tricode.upper(), tricode.upper())
    
    def get_team_history(self, current_tricode: str) -> List[Dict[str, str]]:
        """Get the complete history of a team including relocations."""
        history = []
        
        # Check if this is a relocated team
        for year, relocations in self.TEAM_RELOCATIONS.items():
            for old_code, new_code in relocations.items():
                if new_code == current_tricode:
                    # Add the historical entry
                    if old_code in self.DEFUNCT_TEAMS:
                        history.append({
                            'tricode': old_code,
                            'years': f"until {year}",
                            **self.DEFUNCT_TEAMS[old_code]
                        })
                    
                    # Add current entry
                    if current_tricode in self.CURRENT_TEAMS:
                        history.append({
                            'tricode': current_tricode,
                            'years': f"{year}-present",
                            **self.CURRENT_TEAMS[current_tricode]
                        })
                    break
        
        # If no relocation history, just return current info
        if not history and current_tricode in self.CURRENT_TEAMS:
            history.append({
                'tricode': current_tricode,
                'years': "1996-present",  # Default assumption
                **self.CURRENT_TEAMS[current_tricode]
            })
        
        return history


# Global instance for easy access
NBA_TEAMS = NBATeamMapping()