"""
Natural Language Query Translator for NBA MCP Server

Translates natural language queries into structured database queries.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from ..core.query_builder import QueryType, UnifiedQueryBuilder, PlayerQueryBuilder, GameQueryBuilder, PlayQueryBuilder


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
        self.shot_zone_patterns = self._init_shot_zone_patterns()
        self.event_type_patterns = self._init_event_type_patterns()
        self.event_action_patterns = self._init_event_action_patterns()
        self.distance_patterns = self._init_distance_patterns()
        self.situation_patterns = self._init_situation_patterns()
        
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
            # Shot chart and coordinate-based queries
            QueryType.SHOT_CHART: [
                r"\bshot\s+chart\b",
                r"\bshot\s+map\b",
                r"\bwhere\s+(did|does).+\s+shoot\b",
                r"\bshot\s+locations?\b",
                r"\bcoordinates?\b",
                r"\b(x|y)\s+position\b",
                r"\bfrom\s+where\b",
                r"\bheat\s+map\b",
                r"\bshooting\s+zones?\b"
            ],
            
            # Shot analysis queries
            QueryType.SHOT_ANALYSIS: [
                r"\bshots?\s+(made|missed)\b",
                r"\bshooting\s+percentage\b",
                r"\bmade\s+.+\s+from\b",
                r"\b(three|3).+(pointers?|pts?)\b",
                r"\blong\s+range\b",
                r"\bclose\s+range\b",
                r"\bmid\s+range\b",
                r"\bbeyond\s+\d+\s+feet\b",
                r"\bshot\s+distance\b",
                r"\bfrom\s+\d+\s+feet\b"
            ],
            
            # Time and situation-based queries
            QueryType.TIME_SITUATION: [
                r"\b(4th|fourth)\s+quarter\b",
                r"\bcrunch\s+time\b",
                r"\blast\s+\d+\s+minutes?\b",
                r"\bfinal\s+\d+\s+minutes?\b",
                r"\bovertime\b",
                r"\bot\b",
                r"\b\d+(st|nd|rd|th)\s+quarter\b",
                r"\bin\s+the\s+(first|second|third|fourth)\b",
                r"\bwith\s+\d+.+\s+(left|remaining)\b",
                r"\bunder\s+\d+\s+minutes?\b"
            ],
            
            # Clutch and close game situations
            QueryType.CLUTCH_PLAYS: [
                r"\bclutch\b",
                r"\bclose\s+games?\b",
                r"\bwhen\s+(it|score).+\s+(matters?|close)\b",
                r"\bfinal\s+moments?\b",
                r"\bgame\s+winning\b",
                r"\bwith\s+\d+\s+points?\s+(lead|behind)\b",
                r"\bscore\s+within\s+\d+\b",
                r"\btight\s+games?\b",
                r"\bpressure\s+situations?\b"
            ],
            
            # Player-specific play queries
            QueryType.PLAYER_PLAYS: [
                r"\bplays?\s+(made\s+)?by\b",
                r"\bwhat\s+did\s+.+\s+do\b",
                r"\bevery\s+.+\s+(shot|assist|block|steal)\b",
                r"\ball\s+.+\s+(shots?|assists?|blocks?|steals?)\b",
                r"\bshow\s+me\s+.+\s+(shots?|plays?)\b",
                r"\blist\s+.+\s+(shots?|assists?)\b"
            ],
            
            # Team play patterns
            QueryType.TEAM_PLAYS: [
                r"\bteam\s+plays?\b",
                r"\bdefensive\s+plays?\b",
                r"\boffensive\s+plays?\b",
                r"\ball\s+.+\s+team\s+(shots?|plays?)\b",
                r"\bhow\s+did\s+.+\s+play\b"
            ],
            
            # Assist analysis
            QueryType.ASSIST_ANALYSIS: [
                r"\bassists?\s+(by|from)\b",
                r"\bwho\s+assisted\b",
                r"\bpass(es)?\s+to\b",
                r"\bset\s+up\s+by\b",
                r"\bassisted\s+by\b",
                r"\ball\s+assists?\b"
            ],
            
            # Defensive plays
            QueryType.DEFENSIVE_PLAYS: [
                r"\bblocks?\s+(by|from)\b",
                r"\bsteals?\s+(by|from)\b",
                r"\bdefensive\s+plays?\b",
                r"\bturnovers?\s+forced\b",
                r"\bstole\s+the\s+ball\b",
                r"\bblocked\s+shots?\b"
            ],
            
            # Game flow and momentum
            QueryType.GAME_FLOW: [
                r"\bgame\s+flow\b",
                r"\bmomentum\b",
                r"\brunning?\s+score\b",
                r"\bsequence\s+of\s+plays?\b",
                r"\bhow\s+the\s+game\s+went\b",
                r"\btimeline\s+of\s+plays?\b",
                r"\bplay\s+by\s+play\b"
            ],
            
            # Game counting queries
            QueryType.GAME_COUNT: [
                r"\bhow\s+many\s+games?\b",
                r"\bnumber\s+of\s+games?\b",
                r"\bcount\s+of\s+games?\b",
                r"\btotal\s+games?\b",
                r"\bunique\s+games?\b",
                r"\bdistinct\s+games?\b",
                r"\bgames?\s+played\s+(against|vs|versus)\b",
                r"\bgames?\s+(against|vs|versus)\b"
            ],
            
            # General play-by-play
            QueryType.PLAY_BY_PLAY: [
                r"\bplay\s+by\s+play\b",
                r"\ball\s+plays?\b",
                r"\bevents?\s+in\s+(the\s+)?game\b",
                r"\bwhat\s+happened\s+in\b",
                r"\bshow\s+me\s+plays?\b",
                r"\blist\s+all\s+plays?\b"
            ],
            
            # Legacy patterns (keeping for backward compatibility)
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
                r"\bgame\s+recap\b",
                r"\bgame\s+summary\b"
            ],
            QueryType.HISTORICAL_QUERY: [
                r"\ball\s+time\b",
                r"\bhistory\b",
                r"\bever\b",
                r"\brecord\s+for\b"
            ]
        }
    
    def _init_shot_zone_patterns(self) -> Dict[str, List[str]]:
        """Initialize shot zone patterns for recognition."""
        return {
            "paint": ["paint", "in the paint", "close to basket", "near basket"],
            "mid_range": ["mid range", "midrange", "elbow", "free throw line", "baseline"],
            "three_point": ["three point", "3pt", "beyond the arc", "from three", "long range"],
            "corner": ["corner", "corner three", "corner 3"],
            "top_of_key": ["top of key", "center court", "straight away"],
            "wing": ["wing", "side", "left wing", "right wing"],
            "restricted_area": ["restricted area", "under basket", "at rim"]
        }
    
    def _init_event_type_patterns(self) -> Dict[str, List[str]]:
        """Initialize event type patterns for recognition."""
        return {
            "Made Shot": ["made shot", "scored", "made", "sink", "swish", "bucket", "field goal made"],
            "Missed Shot": ["missed shot", "missed", "miss", "brick", "off the rim", "field goal missed"],
            "Free Throw": ["free throw", "ft", "foul shot", "charity stripe"],
            "Rebound": ["rebound", "grabbed", "board", "rebounded", "offensive rebound", "defensive rebound"],
            "Foul": ["foul", "personal foul", "flagrant", "technical", "offensive foul", "flagrant foul"],
            "Turnover": ["turnover", "lost ball", "travel", "double dribble", "bad pass", "lost ball turnover"],
            "Substitution": ["substitution", "sub", "came in", "entered game", "checked in", "player change"],
            "Timeout": ["timeout", "time out", "called timeout", "team timeout"],
            "Jump Ball": ["jump ball", "tip off", "opening tip", "held ball"],
            "Violation": ["violation", "lane violation", "technical violation", "shot clock violation"],
            "Instant Replay": ["instant replay", "replay", "review", "video review"],
            "Ejection": ["ejection", "ejected", "thrown out", "disqualified"]
        }
    
    def _init_event_action_patterns(self) -> Dict[str, List[str]]:
        """Initialize event action type patterns for recognition."""
        return {
            # Shot types
            "Jump Shot": ["jump shot", "jumper", "pull up", "pullup jump shot"],
            "Layup Shot": ["layup", "layup shot", "lay up", "finger roll"],
            "Driving Layup Shot": ["driving layup", "drive", "driving to basket"],
            "Hook Shot": ["hook shot", "hook", "sky hook", "baby hook"],
            "Dunk Shot": ["dunk shot", "dunk", "slam", "slam dunk", "throwing it down"],
            "Slam Dunk Shot": ["slam dunk", "slam"],
            "Driving Dunk Shot": ["driving dunk", "drive and dunk"],
            "Alley Oop Dunk Shot": ["alley oop dunk", "alley-oop dunk", "oop dunk"],
            "Cutting Dunk Shot": ["cutting dunk", "cut and dunk"],
            "Running Dunk Shot": ["running dunk", "on the run dunk"],
            "Putback Dunk Shot": ["putback dunk", "offensive rebound dunk"],
            "Reverse Dunk Shot": ["reverse dunk", "reverse slam"],
            "Tip Shot": ["tip in", "putback", "tip shot", "offensive tip"],
            "Fadeaway Shot": ["fadeaway", "fade away", "turnaround fadeaway"],
            "Bank Shot": ["bank shot", "off the glass", "using the glass"],
            "Alley Oop Shot": ["alley oop", "alley-oop", "oop"],
            "Running Jump Shot": ["running jumper", "on the run", "running jump shot"],
            
            # Free throw types
            "Free Throw 1 of 1": ["technical free throw", "flagrant free throw", "and one"],
            "Free Throw 1 of 2": ["first free throw", "1 of 2"],
            "Free Throw 2 of 2": ["second free throw", "2 of 2"],
            
            # Foul types
            "Personal": ["personal foul", "common foul", "shooting foul"],
            "Shooting": ["shooting foul", "foul on the shot", "fouled shooting"],
            "Offensive": ["offensive foul", "charge", "charging foul"],
            "Flagrant 1": ["flagrant 1", "flagrant foul type 1", "unnecessary contact"],
            "Flagrant 2": ["flagrant 2", "flagrant foul type 2", "excessive contact"],
            "Technical": ["technical foul", "tech", "unsportsmanlike"],
            
            # Turnover types
            "Bad Pass": ["bad pass", "errant pass", "poor pass", "turnover pass"],
            "Lost Ball": ["lost ball", "lost the handle", "lost control"],
            "Traveling": ["travel", "traveling", "walk"],
            "Double Dribble": ["double dribble", "illegal dribble"],
            "Out of Bounds": ["out of bounds", "stepped out", "oob"],
            "Shot Clock": ["shot clock violation", "24 second violation"],
            
            # Rebound types
            "Defensive": ["defensive rebound", "defensive board"],
            "Offensive": ["offensive rebound", "offensive board", "second chance"],
            
            # Other actions
            "Steal": ["steal", "picked off", "intercepted"],
            "Block": ["block", "blocked shot", "rejection", "swat"]
        }
    
    def _init_distance_patterns(self) -> List[Tuple[str, str]]:
        """Initialize distance patterns for recognition."""
        return [
            (r"\b(\d+)\s*feet?\b", "distance_feet"),
            (r"\b(\d+)\s*ft\b", "distance_feet"), 
            (r"\bbeyond\s+(\d+)\s*feet?\b", "distance_min"),
            (r"\bfrom\s+(\d+)\s*feet?\b", "distance_exact"),
            (r"\bover\s+(\d+)\s*feet?\b", "distance_min"),
            (r"\bunder\s+(\d+)\s*feet?\b", "distance_max"),
            (r"\bwithin\s+(\d+)\s*feet?\b", "distance_max"),
            (r"\bclose\s+range\b", "close_range"),
            (r"\bmid\s+range\b", "mid_range"),
            (r"\blong\s+range\b", "long_range")
        ]
    
    def _init_situation_patterns(self) -> Dict[str, List[str]]:
        """Initialize game situation patterns."""
        return {
            "first_quarter": ["1st quarter", "first quarter"],
            "second_quarter": ["2nd quarter", "second quarter"],
            "third_quarter": ["3rd quarter", "third quarter"],
            "fourth_quarter": ["4th quarter", "fourth quarter", "final quarter"],
            "crunch_time": ["crunch time", "final minutes", "final moments", "end of game"],
            "clutch": ["clutch", "pressure", "game on the line", "when it matters"],
            "close_game": ["close game", "tight game", "score within", "close score"],
            "blowout": ["blowout", "rout", "dominant", "big lead", "huge margin"],
            "comeback": ["comeback", "rallied", "came back", "overcame deficit"],
            "overtime": ["overtime", "extra period", "additional time"],
            "playoffs": ["playoffs", "postseason", "playoff game"],
            "finals": ["finals", "championship", "title game"]
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
        entities.extend(self._extract_shot_zones(query_lower))
        entities.extend(self._extract_event_types(query_lower))
        entities.extend(self._extract_event_actions(query_lower))
        entities.extend(self._extract_distances(query_lower))
        entities.extend(self._extract_situations(query_lower))
        
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
        
        # Sort patterns by length (longest first) to avoid substring conflicts
        sorted_players = sorted(self.player_patterns.items(), 
                               key=lambda x: max(len(p) for p in x[1]), reverse=True)
        
        for full_name, patterns in sorted_players:
            for pattern in patterns:
                # Use word boundaries for short patterns to avoid substring matches
                if len(pattern) <= 3:
                    import re
                    if re.search(r'\b' + re.escape(pattern) + r'\b', query, re.IGNORECASE):
                        confidence = 1.0 if pattern == full_name.lower() else 0.8
                        entities.append(ExtractedEntity(
                            entity_type="player",
                            value=full_name,
                            confidence=confidence
                        ))
                        break
                else:
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
    
    def _extract_shot_zones(self, query: str) -> List[ExtractedEntity]:
        """Extract shot zones from query."""
        entities = []
        
        for zone, patterns in self.shot_zone_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    entities.append(ExtractedEntity(
                        entity_type="shot_zone",
                        value=zone,
                        confidence=0.85,
                        start_pos=query.find(pattern),
                        end_pos=query.find(pattern) + len(pattern)
                    ))
        
        return entities
    
    def _extract_event_types(self, query: str) -> List[ExtractedEntity]:
        """Extract event types from query."""
        entities = []
        
        for event_type, patterns in self.event_type_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    entities.append(ExtractedEntity(
                        entity_type="event_type",
                        value=event_type,
                        confidence=0.9,
                        start_pos=query.find(pattern),
                        end_pos=query.find(pattern) + len(pattern)
                    ))
        
        return entities
    
    def _extract_event_actions(self, query: str) -> List[ExtractedEntity]:
        """Extract event action types from query."""
        entities = []
        
        for action_type, patterns in self.event_action_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    entities.append(ExtractedEntity(
                        entity_type="event_action_type",
                        value=action_type,
                        confidence=0.9,
                        start_pos=query.find(pattern),
                        end_pos=query.find(pattern) + len(pattern)
                    ))
        
        return entities
    
    def _extract_distances(self, query: str) -> List[ExtractedEntity]:
        """Extract distance specifications from query."""
        entities = []
        
        for pattern, distance_type in self.distance_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                if distance_type in ["distance_feet", "distance_exact", "distance_min", "distance_max"]:
                    value = match.group(1) if match.groups() else match.group(0)
                else:
                    value = distance_type
                
                entities.append(ExtractedEntity(
                    entity_type="distance",
                    value=f"{distance_type}:{value}",
                    confidence=0.9,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return entities
    
    def _extract_situations(self, query: str) -> List[ExtractedEntity]:
        """Extract game situations from query."""
        entities = []
        
        for situation, patterns in self.situation_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    entities.append(ExtractedEntity(
                        entity_type="situation",
                        value=situation,
                        confidence=0.85,
                        start_pos=query.find(pattern),
                        end_pos=query.find(pattern) + len(pattern)
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