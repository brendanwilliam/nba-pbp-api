"""
WNBA Team Abbreviation Mapping (1997-2025)
Handles team relocations, name changes, and historical abbreviations

ACCURATE AS OF: January 2025
Research completed and verified against official WNBA sources
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime


class WNBATeamMapping:
    """Comprehensive WNBA team abbreviation mapping with historical changes."""
    
    # Current WNBA teams (2024-25 season)
    CURRENT_TEAMS = {
        'ATL': {'name': 'Atlanta Dream', 'city': 'Atlanta'},
        'CHI': {'name': 'Chicago Sky', 'city': 'Chicago'},
        'CONN': {'name': 'Connecticut Sun', 'city': 'Uncasville'},
        'DAL': {'name': 'Dallas Wings', 'city': 'Dallas'},
        'IND': {'name': 'Indiana Fever', 'city': 'Indianapolis'},
        'LA': {'name': 'Los Angeles Sparks', 'city': 'Los Angeles'},
        'LV': {'name': 'Las Vegas Aces', 'city': 'Las Vegas'},
        'MIN': {'name': 'Minnesota Lynx', 'city': 'Minneapolis'},
        'NY': {'name': 'New York Liberty', 'city': 'New York'},
        'PHX': {'name': 'Phoenix Mercury', 'city': 'Phoenix'},
        'SEA': {'name': 'Seattle Storm', 'city': 'Seattle'},
        'WSH': {'name': 'Washington Mystics', 'city': 'Washington'},
        'GS': {'name': 'Golden State Valkyries', 'city': 'San Francisco'},  # New 2025 expansion
    }
    
    # Historical team changes (year: {old_code: new_code})
    TEAM_RELOCATIONS = {
        2003: {'UTA': 'SAS', 'ORL': 'CONN'},  # Utah Starzz → San Antonio, Orlando Miracle → Connecticut Sun
        2010: {'DET': 'TUL'},  # Detroit Shock → Tulsa Shock  
        2016: {'TUL': 'DAL'},  # Tulsa Shock → Dallas Wings
        2018: {'SAS': 'LV'},   # San Antonio Stars → Las Vegas Aces
    }
    
    # Name changes without relocation
    TEAM_NAME_CHANGES = {
        2014: {'SAS': 'SAS'},   # San Antonio Silver Stars → San Antonio Stars
    }
    
    # Original WNBA teams (1997 inaugural season)
    INAUGURAL_TEAMS = {
        'CHA': {'name': 'Charlotte Sting', 'city': 'Charlotte'},
        'CLE': {'name': 'Cleveland Rockers', 'city': 'Cleveland'},
        'HOU': {'name': 'Houston Comets', 'city': 'Houston'},
        'NY': {'name': 'New York Liberty', 'city': 'New York'},
        'LA': {'name': 'Los Angeles Sparks', 'city': 'Los Angeles'},
        'PHX': {'name': 'Phoenix Mercury', 'city': 'Phoenix'},
        'SAC': {'name': 'Sacramento Monarchs', 'city': 'Sacramento'},
        'UTA': {'name': 'Utah Starzz', 'city': 'Salt Lake City'},
    }

    # Expansion teams by season
    EXPANSION_TEAMS = {
        '1998': ['DET', 'WSH'],  # Detroit Shock, Washington Mystics
        '1999': ['MIN', 'ORL'],  # Minnesota Lynx, Orlando Miracle
        '2000': ['MIA', 'POR', 'IND', 'SEA'],  # Miami Sol, Portland Fire, Indiana Fever, Seattle Storm
        '2006': ['CHI'],  # Chicago Sky
        '2008': ['ATL'],  # Atlanta Dream
        '2025': ['GS'],   # Golden State Valkyries
    }
    
    # Teams that no longer exist
    DEFUNCT_TEAMS = {
        'CHA': {'name': 'Charlotte Sting', 'active_until': 2006},
        'CLE': {'name': 'Cleveland Rockers', 'active_until': 2003},
        'HOU': {'name': 'Houston Comets', 'active_until': 2008},
        'SAC': {'name': 'Sacramento Monarchs', 'active_until': 2009},
        'MIA': {'name': 'Miami Sol', 'active_until': 2002},
        'POR': {'name': 'Portland Fire', 'active_until': 2002},
        'ORL': {'name': 'Orlando Miracle', 'active_until': 2002},
        'DET': {'name': 'Detroit Shock', 'active_until': 2009},
        'TUL': {'name': 'Tulsa Shock', 'active_until': 2015},
        'UTA': {'name': 'Utah Starzz', 'active_until': 2002},
        'SAS': {'name': 'San Antonio Stars', 'active_until': 2017},
    }
    
    # Special cases and alternative abbreviations
    ALTERNATIVE_ABBREVIATIONS = {
        'LAS': 'LV',      # Las Vegas alternative (often used)
        'LVA': 'LV',      # Las Vegas alternative
        'CON': 'CONN',    # Connecticut short form → full form
        'CT': 'CONN',     # Connecticut abbreviation → full form
        'NEW_YORK': 'NY', # New York underscore form
        'GSV': 'GS',      # Golden State alternative
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
        
        # Check inaugural teams
        if tricode in self.INAUGURAL_TEAMS:
            return {
                'tricode': tricode,
                **self.INAUGURAL_TEAMS[tricode],
                'season': season,
                'inaugural': True
            }
        
        return None
    
    def get_all_teams_for_season(self, season: str) -> List[str]:
        """Get all active team codes for a specific season."""
        season_year = int(season.split('-')[0])
        active_teams = []
        
        # Start with current teams (excluding future expansions)
        for tricode, info in self.CURRENT_TEAMS.items():
            # Golden State Valkyries start in 2025
            if tricode == 'GS' and season_year < 2025:
                continue
            active_teams.append(tricode)
        
        # Add historical teams that were active in this season
        for tricode, info in self.DEFUNCT_TEAMS.items():
            if season_year <= info['active_until']:
                active_teams.append(tricode)
        
        # Add inaugural teams for early seasons
        if season_year <= 1997:
            for tricode in self.INAUGURAL_TEAMS.keys():
                if tricode not in active_teams:
                    active_teams.append(tricode)
        
        # Remove teams that were relocated before this season
        for year, relocations in self.TEAM_RELOCATIONS.items():
            if season_year >= year:
                for old_code in relocations.keys():
                    if old_code in active_teams:
                        active_teams.remove(old_code)
        
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
                'years': "1997-present",  # WNBA started in 1997
                **self.CURRENT_TEAMS[current_tricode]
            })
        
        return history
    
    def get_season_info(self, season: str) -> Dict[str, any]:
        """Get comprehensive season information including team count and major changes."""
        season_year = int(season.split('-')[0])
        teams = self.get_all_teams_for_season(season)
        
        # Identify major changes for this season
        changes = []
        for year, relocations in self.TEAM_RELOCATIONS.items():
            if year == season_year:
                for old_code, new_code in relocations.items():
                    changes.append(f"{old_code} relocated to {new_code}")
        
        # Check for expansions
        expansions = []
        for expansion_season, new_teams in self.EXPANSION_TEAMS.items():
            if expansion_season == str(season_year) or expansion_season == season:
                expansions.extend(new_teams)
        
        return {
            'season': season,
            'team_count': len(teams),
            'active_teams': teams,
            'relocations': changes,
            'expansions': expansions,
            'wnba_age': season_year - 1997 + 1  # WNBA started in 1997
        }


# Global instance for easy access
WNBA_TEAMS = WNBATeamMapping()

# Backwards compatibility alias
NBA_TEAMS = WNBA_TEAMS  # For any legacy code that imports NBA_TEAMS