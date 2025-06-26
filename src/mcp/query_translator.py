"""
Natural Language Query Translator for NBA MCP Server

Translates natural language queries into structured database queries.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
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
class ExtractedEntity:
    entity_type: str
    value: str
    confidence: float
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None


@dataclass
class QueryContext:
    query_type: QueryType
    entities: List[ExtractedEntity]
    intent: str
    confidence: float
    season: Optional[str] = None
    time_period: Optional[str] = None


class NaturalLanguageQueryTranslator:
    """Translates natural language queries into structured database queries."""
    
    def __init__(self):
        self.player_patterns = self._init_player_patterns()
        self.team_patterns = self._init_team_patterns()
        self.stat_patterns = self._init_stat_patterns()
        self.time_patterns = self._init_time_patterns()
        self.intent_patterns = self._init_intent_patterns()
        
    def _init_player_patterns(self) -> Dict[str, List[str]]:
        """Initialize player name patterns for recognition."""
        return {
            "LeBron James": ["lebron", "lebron james", "king james", "lbj"],
            "Michael Jordan": ["jordan", "michael jordan", "mj", "his airness"],
            "Kobe Bryant": ["kobe", "kobe bryant", "black mamba", "bean"],
            "Stephen Curry": ["curry", "stephen curry", "steph curry", "chef curry"],
            "Kevin Durant": ["durant", "kevin durant", "kd", "durantula"],
            "Giannis Antetokounmpo": ["giannis", "greek freak", "antetokounmpo"],
            "Kawhi Leonard": ["kawhi", "kawhi leonard", "claw"],
            "James Harden": ["harden", "james harden", "beard"],
            "Russell Westbrook": ["westbrook", "russell westbrook", "russ"],
            "Chris Paul": ["cp3", "chris paul", "point god"],
            "Damian Lillard": ["lillard", "damian lillard", "dame"],
            "Luka Doncic": ["luka", "luka doncic", "doncic"],
            "Nikola Jokic": ["jokic", "nikola jokic", "joker"],
            "Joel Embiid": ["embiid", "joel embiid"],
            "Jayson Tatum": ["tatum", "jayson tatum"],
            "Devin Booker": ["booker", "devin booker"],
            "Ja Morant": ["ja", "ja morant", "morant"],
            "Zion Williamson": ["zion", "zion williamson"],
            "Anthony Davis": ["ad", "anthony davis", "davis"],
            "Jimmy Butler": ["butler", "jimmy butler"]
        }
    
    def _init_team_patterns(self) -> Dict[str, List[str]]:
        """Initialize team name patterns for recognition."""
        return {
            "Los Angeles Lakers": ["lakers", "los angeles lakers", "la lakers", "lal"],
            "Golden State Warriors": ["warriors", "golden state warriors", "gsw", "dubs"],
            "Boston Celtics": ["celtics", "boston celtics", "bos"],
            "Miami Heat": ["heat", "miami heat", "mia"],
            "Chicago Bulls": ["bulls", "chicago bulls", "chi"],
            "San Antonio Spurs": ["spurs", "san antonio spurs", "sas"],
            "Brooklyn Nets": ["nets", "brooklyn nets", "bkn"],
            "Philadelphia 76ers": ["sixers", "76ers", "philadelphia 76ers", "phi"],
            "Milwaukee Bucks": ["bucks", "milwaukee bucks", "mil"],
            "Phoenix Suns": ["suns", "phoenix suns", "phx"],
            "Denver Nuggets": ["nuggets", "denver nuggets", "den"],
            "Memphis Grizzlies": ["grizzlies", "memphis grizzlies", "mem"],
            "New Orleans Pelicans": ["pelicans", "new orleans pelicans", "nop"],
            "Dallas Mavericks": ["mavericks", "mavs", "dallas mavericks", "dal"],
            "Utah Jazz": ["jazz", "utah jazz", "uta"],
            "Portland Trail Blazers": ["blazers", "trail blazers", "portland trail blazers", "por"],
            "Oklahoma City Thunder": ["thunder", "oklahoma city thunder", "okc"],
            "Indiana Pacers": ["pacers", "indiana pacers", "ind"],
            "Charlotte Hornets": ["hornets", "charlotte hornets", "cha"],
            "Toronto Raptors": ["raptors", "toronto raptors", "tor"],
            "Atlanta Hawks": ["hawks", "atlanta hawks", "atl"],
            "Washington Wizards": ["wizards", "washington wizards", "was"],
            "Orlando Magic": ["magic", "orlando magic", "orl"],
            "Detroit Pistons": ["pistons", "detroit pistons", "det"],
            "Cleveland Cavaliers": ["cavaliers", "cavs", "cleveland cavaliers", "cle"],
            "New York Knicks": ["knicks", "new york knicks", "nyk"],
            "Sacramento Kings": ["kings", "sacramento kings", "sac"],
            "Houston Rockets": ["rockets", "houston rockets", "hou"],
            "Los Angeles Clippers": ["clippers", "los angeles clippers", "la clippers", "lac"],
            "Minnesota Timberwolves": ["timberwolves", "wolves", "minnesota timberwolves", "min"]
        }
    
    def _init_stat_patterns(self) -> Dict[str, List[str]]:
        """Initialize statistical category patterns."""
        return {
            "points": ["points", "pts", "scoring", "ppg", "points per game"],
            "rebounds": ["rebounds", "reb", "rpg", "rebounds per game", "boards"],
            "assists": ["assists", "ast", "apg", "assists per game", "dimes"],
            "steals": ["steals", "stl", "spg", "steals per game"],
            "blocks": ["blocks", "blk", "bpg", "blocks per game"],
            "field_goals": ["field goals", "fg", "field goal percentage", "shooting"],
            "three_pointers": ["three pointers", "3pt", "three point percentage", "threes"],
            "free_throws": ["free throws", "ft", "free throw percentage"],
            "turnovers": ["turnovers", "to", "tpg", "turnovers per game"],
            "fouls": ["fouls", "pf", "personal fouls", "fpg"],
            "minutes": ["minutes", "min", "mpg", "minutes per game"],
            "games": ["games", "gp", "games played"]
        }
    
    def _init_time_patterns(self) -> Dict[str, str]:
        """Initialize time/season patterns."""
        return {
            r"\b(\d{4})-(\d{2})\b": "season",
            r"\b(\d{4})\s*season\b": "season",
            r"\bthis\s+season\b": "current_season",
            r"\blast\s+season\b": "last_season",
            r"\bcareer\b": "career",
            r"\bplayoffs?\b": "playoffs",
            r"\bregular\s+season\b": "regular_season",
            r"\bfinals?\b": "finals",
            r"\brecent\b": "recent",
            r"\blast\s+\d+\s+games?\b": "last_n_games"
        }
    
    def _init_intent_patterns(self) -> Dict[QueryType, List[str]]:
        """Initialize intent recognition patterns."""
        return {
            QueryType.PLAYER_STATS: [
                r"\b(stats?|statistics?|averages?|numbers?)\b",
                r"\bhow\s+(many|much|good)\b",
                r"\bper\s+game\b",
                r"\bppg|rpg|apg\b"
            ],
            QueryType.PLAYER_COMPARISON: [
                r"\bcompare\b",
                r"\bversus\b",
                r"\bvs\.?\b",
                r"\bbetter\b",
                r"\bwho\s+is\s+(better|best)\b"
            ],
            QueryType.TEAM_STATS: [
                r"\bteam\s+(stats?|record|performance)\b",
                r"\bhow\s+(did|has)\s+.+\s+(team|perform)\b",
                r"\bwins?\s+and\s+losses?\b",
                r"\brecord\b"
            ],
            QueryType.GAME_ANALYSIS: [
                r"\bgame\s+\d+\b",
                r"\bwhat\s+happened\b",
                r"\bplay\s+by\s+play\b",
                r"\bgame\s+recap\b"
            ],
            QueryType.HISTORICAL_QUERY: [
                r"\ball\s+time\b",
                r"\bhistory\b",
                r"\bever\b",
                r"\brecord\s+for\b"
            ]
        }
    
    async def translate_query(self, query: str) -> QueryContext:
        """Translate natural language query to structured context."""
        query_lower = query.lower().strip()
        
        # Extract entities
        entities = []
        entities.extend(self._extract_players(query_lower))
        entities.extend(self._extract_teams(query_lower))
        entities.extend(self._extract_stats(query_lower))
        entities.extend(self._extract_time_periods(query_lower))
        
        # Determine query type and intent
        query_type = self._classify_query_type(query_lower)
        intent = self._extract_intent(query_lower, query_type)
        
        # Extract season and time period
        season = self._extract_season(query_lower)
        time_period = self._extract_time_period(query_lower)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(entities, query_type)
        
        return QueryContext(
            query_type=query_type,
            entities=entities,
            intent=intent,
            confidence=confidence,
            season=season,
            time_period=time_period
        )
    
    def _extract_players(self, query: str) -> List[ExtractedEntity]:
        """Extract player names from query."""
        entities = []
        
        for full_name, patterns in self.player_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    confidence = 1.0 if pattern == full_name.lower() else 0.8
                    entities.append(ExtractedEntity(
                        entity_type="player",
                        value=full_name,
                        confidence=confidence
                    ))
                    break  # Only match once per player
        
        return entities
    
    def _extract_teams(self, query: str) -> List[ExtractedEntity]:
        """Extract team names from query."""
        entities = []
        
        for full_name, patterns in self.team_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    confidence = 1.0 if pattern == full_name.lower() else 0.8
                    entities.append(ExtractedEntity(
                        entity_type="team",
                        value=full_name,
                        confidence=confidence
                    ))
                    break  # Only match once per team
        
        return entities
    
    def _extract_stats(self, query: str) -> List[ExtractedEntity]:
        """Extract statistical categories from query."""
        entities = []
        
        for stat_name, patterns in self.stat_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    confidence = 1.0 if pattern == stat_name else 0.9
                    entities.append(ExtractedEntity(
                        entity_type="statistic",
                        value=stat_name,
                        confidence=confidence
                    ))
                    break  # Only match once per stat
        
        return entities
    
    def _extract_time_periods(self, query: str) -> List[ExtractedEntity]:
        """Extract time periods from query."""
        entities = []
        
        for pattern, time_type in self.time_patterns.items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append(ExtractedEntity(
                    entity_type="time_period",
                    value=time_type,
                    confidence=0.9,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return entities
    
    def _classify_query_type(self, query: str) -> QueryType:
        """Classify the type of query."""
        type_scores = {}
        
        for query_type, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    score += 1
            type_scores[query_type] = score
        
        # Return type with highest score, or UNKNOWN if no matches
        if type_scores:
            max_type = max(type_scores.keys(), key=lambda k: type_scores[k])
            if type_scores[max_type] > 0:
                return max_type
        
        return QueryType.UNKNOWN
    
    def _extract_intent(self, query: str, query_type: QueryType) -> str:
        """Extract the specific intent from the query."""
        if query_type == QueryType.PLAYER_STATS:
            if "career" in query:
                return "career_stats"
            elif "season" in query:
                return "season_stats"
            elif "average" in query:
                return "averages"
            else:
                return "basic_stats"
        
        elif query_type == QueryType.PLAYER_COMPARISON:
            if "better" in query:
                return "who_is_better"
            else:
                return "compare_stats"
        
        elif query_type == QueryType.TEAM_STATS:
            if "record" in query:
                return "team_record"
            elif "performance" in query:
                return "team_performance"
            else:
                return "team_stats"
        
        elif query_type == QueryType.GAME_ANALYSIS:
            if "play by play" in query:
                return "play_by_play"
            elif "recap" in query:
                return "game_recap"
            else:
                return "game_summary"
        
        return "general_query"
    
    def _extract_season(self, query: str) -> Optional[str]:
        """Extract season from query."""
        # Look for YYYY-YY format
        season_match = re.search(r'\b(\d{4})-(\d{2})\b', query)
        if season_match:
            return season_match.group(0)
        
        # Look for YYYY season
        year_match = re.search(r'\b(\d{4})\s*season\b', query)
        if year_match:
            year = int(year_match.group(1))
            # Convert to YYYY-YY format
            next_year = str(year + 1)[-2:]
            return f"{year}-{next_year}"
        
        # Handle current/last season
        if "this season" in query or "current season" in query:
            return "2024-25"  # Would be dynamically determined
        elif "last season" in query:
            return "2023-24"  # Would be dynamically determined
        
        return None
    
    def _extract_time_period(self, query: str) -> Optional[str]:
        """Extract general time period from query."""
        if "career" in query:
            return "career"
        elif "playoffs" in query:
            return "playoffs"
        elif "regular season" in query:
            return "regular_season"
        elif "finals" in query:
            return "finals"
        elif "recent" in query:
            return "recent"
        
        # Look for "last N games"
        last_games_match = re.search(r'last\s+(\d+)\s+games?', query)
        if last_games_match:
            return f"last_{last_games_match.group(1)}_games"
        
        return None
    
    def _calculate_confidence(self, entities: List[ExtractedEntity], query_type: QueryType) -> float:
        """Calculate overall confidence in query understanding."""
        if not entities:
            return 0.1
        
        # Base confidence on entity confidence and query type
        entity_confidence = sum(e.confidence for e in entities) / len(entities)
        
        # Boost confidence if query type is not UNKNOWN
        type_confidence = 0.8 if query_type != QueryType.UNKNOWN else 0.3
        
        # Weighted average
        return (entity_confidence * 0.7) + (type_confidence * 0.3)