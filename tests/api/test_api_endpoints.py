"""
API Endpoint Testing Suite

This script tests all NBA Play-by-Play API endpoints when running locally.
Tests basic functionality, error handling, and validates expected response structures.

Usage:
    python test_api_endpoints.py
    python test_api_endpoints.py --verbose
    python test_api_endpoints.py --base-url http://localhost:8001

Requirements:
    - API server running locally (default: http://localhost:8000)
    - Database populated with NBA game data
    - requests library installed
"""

import requests
import json
import sys
import argparse
import time
from typing import Dict, Optional, List
from datetime import datetime


class APIEndpointTester:
    """Test suite for NBA Play-by-Play API endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Test results tracking
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        # Sample test data (will be populated from API responses)
        self.test_data = {
            'player_id': None,
            'team_id': None,
            'game_id': None,
            'season': None,
            'celtics_team_id': None,
            'tatum_player_id': None,
            'brown_player_id': None
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.verbose or level == "ERROR":
            print(f"[{timestamp}] {level}: {message}")
    
    def make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """Make HTTP request to API endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, params=params, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            self.log(f"{method} {endpoint} -> {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"HTTP {response.status_code}: {response.text}", "ERROR")
                return None
                
        except requests.exceptions.ConnectionError:
            self.log(f"Connection failed to {url}", "ERROR")
            return None
        except Exception as e:
            self.log(f"Request error: {str(e)}", "ERROR")
            return None
    
    def assert_response_structure(self, response: Dict, expected_keys: List[str], test_name: str):
        """Validate response has expected structure"""
        try:
            for key in expected_keys:
                if key not in response:
                    raise AssertionError(f"Missing key '{key}' in response")
            
            self.results['passed'] += 1
            self.log(f"✓ {test_name} - Structure validation passed")
            return True
            
        except AssertionError as e:
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {str(e)}")
            self.log(f"✗ {test_name} - {str(e)}", "ERROR")
            return False
    
    def test_health_endpoint(self):
        """Test /health endpoint"""
        self.log("Testing health endpoint...")
        response = self.make_request("GET", "/health")
        
        if response:
            expected_keys = ["status", "timestamp", "service", "version"]
            self.assert_response_structure(response, expected_keys, "Health endpoint")
            
            # Validate status is healthy
            if response.get("status") == "healthy":
                self.log("✓ Health status is healthy")
            else:
                self.log(f"✗ Unexpected health status: {response.get('status')}", "ERROR")
        else:
            self.results['failed'] += 1
            self.results['errors'].append("Health endpoint: No response received")
    
    def test_root_endpoint(self):
        """Test / root endpoint"""
        self.log("Testing root endpoint...")
        response = self.make_request("GET", "/")
        
        if response:
            expected_keys = ["message", "version", "docs", "health", "description"]
            self.assert_response_structure(response, expected_keys, "Root endpoint")
    
    def populate_test_data(self):
        """Get sample data IDs for testing from teams endpoint"""
        self.log("Populating test data from API...")
        
        # Get teams to find a team_id (Lakers for general testing)
        response = self.make_request("GET", "/api/v1/teams/search", {"query": "Lakers", "limit": 1})
        if response and response.get("teams"):
            self.test_data['team_id'] = response["teams"][0].get("team_id")
            self.log(f"Found team_id: {self.test_data['team_id']}")
        
        # Get Celtics team ID for Tatum/Brown testing
        response = self.make_request("GET", "/api/v1/teams/search", {"query": "Celtics", "limit": 1})
        if response and response.get("teams"):
            self.test_data['celtics_team_id'] = response["teams"][0].get("team_id")
            self.log(f"Found Celtics team_id: {self.test_data['celtics_team_id']}")
        
        # Get a player from player search
        response = self.make_request("GET", "/api/v1/players/search", {"query": "James", "limit": 1})
        if response and response.get("players"):
            self.test_data['player_id'] = response["players"][0].get("player_id")
            self.log(f"Found player_id: {self.test_data['player_id']}")
        
        # Search for Jayson Tatum
        response = self.make_request("GET", "/api/v1/players/search", {"query": "Tatum", "limit": 1})
        if response and response.get("players"):
            self.test_data['tatum_player_id'] = response["players"][0].get("player_id")
            self.log(f"Found Tatum player_id: {self.test_data['tatum_player_id']}")
        
        # Search for Jaylen Brown
        response = self.make_request("GET", "/api/v1/players/search", {"query": "Brown", "limit": 5})
        if response and response.get("players"):
            # Look for Jaylen Brown specifically (filter by likely Celtics association)
            for player in response["players"]:
                if "jaylen" in player.get("player_name", "").lower():
                    self.test_data['brown_player_id'] = player.get("player_id")
                    self.log(f"Found Jaylen Brown player_id: {self.test_data['brown_player_id']}")
                    break
        
        # Try to get a recent season and game from player stats
        if self.test_data['player_id']:
            response = self.make_request("GET", "/api/v1/player-stats", {
                "player_id": self.test_data['player_id'],
                "limit": 1
            })
            if response and response.get("data"):
                game_data = response["data"][0]
                self.test_data['season'] = game_data.get("season")
                self.test_data['game_id'] = game_data.get("game_id")
                self.log(f"Found season: {self.test_data['season']}, game_id: {self.test_data['game_id']}")
    
    def test_player_stats_basic(self):
        """Test basic player stats endpoint"""
        self.log("Testing player stats basic endpoint...")
        
        params = {"limit": 5}
        if self.test_data['player_id']:
            params['player_id'] = self.test_data['player_id']
        
        response = self.make_request("GET", "/api/v1/player-stats", params)
        
        if response:
            expected_keys = ["data", "total_records", "query_info"]
            if self.assert_response_structure(response, expected_keys, "Player stats basic"):
                # Validate data structure
                if response.get("data") and len(response["data"]) > 0:
                    player_data = response["data"][0]
                    expected_player_keys = ["player_id", "player_name", "points", "rebounds", "assists"]
                    self.assert_response_structure(player_data, expected_player_keys, "Player data structure")
    
    def test_player_stats_with_filters(self):
        """Test player stats with various filters"""
        self.log("Testing player stats with filters...")
        
        # Test with JSON filters
        filters = json.dumps({"points": {"gte": 20}, "assists": {"gte": 5}})
        params = {
            "limit": 10,
            "filters": filters,
            "sort": "-points",
            "include_summary": True
        }
        
        if self.test_data['season']:
            params['season'] = self.test_data['season']
        
        response = self.make_request("GET", "/api/v1/player-stats", params)
        
        if response:
            self.assert_response_structure(response, ["data", "total_records"], "Player stats with filters")
            
            # Check if summary is included when requested
            if "statistical_analysis" in response:
                self.log("✓ Statistical analysis included as requested")
            
            # Validate filtering worked (if data exists)
            if response.get("data"):
                for player in response["data"]:
                    if player.get("points", 0) >= 20 and player.get("assists", 0) >= 5:
                        self.log("✓ Filter validation passed")
                        break
    
    def test_player_stats_by_id(self):
        """Test individual player stats endpoint"""
        if not self.test_data['player_id']:
            self.log("Skipping player stats by ID - no player_id available")
            return
        
        self.log(f"Testing player stats by ID: {self.test_data['player_id']}")
        
        response = self.make_request("GET", f"/api/v1/players/{self.test_data['player_id']}/stats", {
            "limit": 5,
            "season": "latest"
        })
        
        if response:
            expected_keys = ["player_info", "stats", "total_records", "pagination"]
            self.assert_response_structure(response, expected_keys, "Player stats by ID")
    
    def test_player_search(self):
        """Test player search endpoint"""
        self.log("Testing player search...")
        
        response = self.make_request("GET", "/api/v1/players/search", {
            "query": "LeBron",
            "limit": 5
        })
        
        if response:
            expected_keys = ["query", "players", "total_found"]
            if self.assert_response_structure(response, expected_keys, "Player search"):
                # Validate search worked
                if response.get("players") and len(response["players"]) > 0:
                    player = response["players"][0]
                    if "lebron" in player.get("player_name", "").lower():
                        self.log("✓ Search functionality working")
    
    def test_player_stats_analysis(self):
        """Test player stats analysis endpoint"""
        if not self.test_data['player_id']:
            self.log("Skipping player analysis - no player_id available")
            return
        
        self.log("Testing player stats analysis...")
        
        response = self.make_request("POST", "/api/v1/player-stats/analyze", {
            "player_id": self.test_data['player_id'],
            "include_summary": True,
            "correlation": ["points", "assists", "rebounds"]
        })
        
        if response:
            # Analysis endpoint returns StatisticalAnalysis structure
            expected_keys = ["summary", "correlation", "distribution"]
            self.assert_response_structure(response, expected_keys, "Player stats analysis")
    
    def test_team_stats_basic(self):
        """Test basic team stats endpoint"""
        self.log("Testing team stats basic endpoint...")
        
        params = {"limit": 5}
        if self.test_data['team_id']:
            params['team_id'] = self.test_data['team_id']
        
        response = self.make_request("GET", "/api/v1/team-stats", params)
        
        if response:
            expected_keys = ["data", "total_records", "query_info"]
            if self.assert_response_structure(response, expected_keys, "Team stats basic"):
                # Validate data structure
                if response.get("data") and len(response["data"]) > 0:
                    team_data = response["data"][0]
                    expected_team_keys = ["team_id", "team_name", "points", "rebounds", "assists"]
                    self.assert_response_structure(team_data, expected_team_keys, "Team data structure")
    
    def test_team_stats_by_id(self):
        """Test individual team stats endpoint"""
        if not self.test_data['team_id']:
            self.log("Skipping team stats by ID - no team_id available")
            return
        
        self.log(f"Testing team stats by ID: {self.test_data['team_id']}")
        
        response = self.make_request("GET", f"/api/v1/teams/{self.test_data['team_id']}/stats", {
            "limit": 5,
            "season": "latest"
        })
        
        if response:
            expected_keys = ["team_info", "stats", "total_records", "pagination"]
            self.assert_response_structure(response, expected_keys, "Team stats by ID")
    
    def test_team_search(self):
        """Test team search endpoint"""
        self.log("Testing team search...")
        
        response = self.make_request("GET", "/api/v1/teams/search", {
            "query": "Lakers",
            "limit": 5
        })
        
        if response:
            expected_keys = ["query", "teams", "total_found"]
            if self.assert_response_structure(response, expected_keys, "Team search"):
                # Validate search worked
                if response.get("teams") and len(response["teams"]) > 0:
                    team = response["teams"][0]
                    if "lakers" in team.get("team_name", "").lower():
                        self.log("✓ Team search functionality working")
    
    def test_teams_by_season(self):
        """Test teams by season endpoint"""
        if not self.test_data['season']:
            season = "2023-24"  # Fallback season
        else:
            season = self.test_data['season']
        
        self.log(f"Testing teams by season: {season}")
        
        response = self.make_request("GET", f"/api/v1/teams/by-season/{season}")
        
        if response:
            expected_keys = ["season", "teams", "total_found"]
            self.assert_response_structure(response, expected_keys, "Teams by season")
    
    def test_head_to_head(self):
        """Test head-to-head stats endpoint"""
        if not self.test_data['team_id']:
            self.log("Skipping head-to-head - no team_id available")
            return
        
        # Use Lakers vs Celtics as a common matchup (team IDs 1 and 2 typically)
        team1_id = self.test_data['team_id']
        team2_id = 2 if team1_id != 2 else 1
        
        self.log(f"Testing head-to-head: {team1_id} vs {team2_id}")
        
        response = self.make_request("GET", f"/api/v1/teams/{team1_id}/head-to-head/{team2_id}", {
            "season": "all"
        })
        
        if response:
            expected_keys = ["team1_info", "team2_info", "summary", "games"]
            self.assert_response_structure(response, expected_keys, "Head-to-head stats")
    
    def test_team_stats_analysis(self):
        """Test team stats analysis endpoint"""
        if not self.test_data['team_id']:
            self.log("Skipping team analysis - no team_id available")
            return
        
        self.log("Testing team stats analysis...")
        
        response = self.make_request("POST", "/api/v1/team-stats/analyze", {
            "team_id": self.test_data['team_id'],
            "include_summary": True,
            "correlation": ["points", "rebounds", "assists"]
        })
        
        if response:
            expected_keys = ["summary", "correlation", "distribution"]
            self.assert_response_structure(response, expected_keys, "Team stats analysis")
    
    def test_lineup_stats_basic(self):
        """Test basic lineup stats endpoint"""
        if not self.test_data['player_id'] or not self.test_data['team_id']:
            self.log("Skipping lineup stats - insufficient test data")
            return
        
        self.log("Testing lineup stats basic endpoint...")
        
        # Get multiple players from the same team for lineup analysis
        response = self.make_request("GET", "/api/v1/player-stats", {
            "team_id": self.test_data['team_id'],
            "limit": 3
        })
        
        if response and response.get("data") and len(response["data"]) >= 2:
            player_ids = [player["player_id"] for player in response["data"][:2]]
            
            lineup_response = self.make_request("GET", "/api/v1/lineup-stats", {
                "player_ids": player_ids,
                "team_id": self.test_data['team_id'],
                "limit": 5
            })
            
            if lineup_response:
                expected_keys = ["data", "total_records"]
                self.assert_response_structure(lineup_response, expected_keys, "Lineup stats basic")
        else:
            self.log("Skipping lineup test - insufficient player data")
    
    def test_common_lineups(self):
        """Test common lineups endpoint"""
        if not self.test_data['team_id']:
            self.log("Skipping common lineups - no team_id available")
            return
        
        self.log(f"Testing common lineups for team: {self.test_data['team_id']}")
        
        response = self.make_request("GET", f"/api/v1/lineups/common/{self.test_data['team_id']}", {
            "season": "latest",
            "min_games": 1,
            "lineup_size": 5,
            "limit": 5
        })
        
        if response:
            expected_keys = ["team_info", "common_lineups", "filters", "total_found"]
            self.assert_response_structure(response, expected_keys, "Common lineups")
    
    def test_player_combinations(self):
        """Test player combinations endpoint"""
        if not self.test_data['team_id']:
            self.log("Skipping player combinations - no team_id available")
            return
        
        self.log("Testing player combinations...")
        
        # Get players for combination analysis
        response = self.make_request("GET", "/api/v1/player-stats", {
            "team_id": self.test_data['team_id'],
            "limit": 3
        })
        
        if response and response.get("data") and len(response["data"]) >= 2:
            player_ids = [player["player_id"] for player in response["data"][:2]]
            
            combo_response = self.make_request("GET", "/api/v1/lineups/player-combinations", {
                "player_ids": player_ids,
                "team_id": self.test_data['team_id'],
                "season": "latest",
                "min_minutes": 5.0
            })
            
            if combo_response:
                expected_keys = ["player_info", "summary", "games_together", "filters"]
                self.assert_response_structure(combo_response, expected_keys, "Player combinations")
        else:
            self.log("Skipping combinations test - insufficient player data")
    
    def test_tatum_brown_lineup(self):
        """Test specific lineup analysis for Jayson Tatum and Jaylen Brown"""
        if not self.test_data['tatum_player_id'] or not self.test_data['brown_player_id']:
            self.log("Skipping Tatum-Brown lineup test - player IDs not found")
            return
        
        self.log("Testing Tatum-Brown lineup analysis...")
        
        tatum_id = self.test_data['tatum_player_id']
        brown_id = self.test_data['brown_player_id']
        
        # Log what we're testing
        self.log(f"Analyzing lineup data for Tatum (ID: {tatum_id}) and Brown (ID: {brown_id})")
        
        # Test 1: Basic lineup stats with both players (all seasons)
        lineup_response = self.make_request("GET", "/api/v1/lineup-stats", {
            "player_ids": [tatum_id, brown_id],
            "team_id": self.test_data['celtics_team_id'],
            "season": "all",
            "limit": 10,
            "include_summary": True
        })
        
        if lineup_response:
            expected_keys = ["data", "total_records"]
            if self.assert_response_structure(lineup_response, expected_keys, "Tatum-Brown lineup stats"):
                self.log(f"✓ Found {lineup_response.get('total_records', 0)} games with Tatum-Brown lineup")
                
                # Check if summary statistics are included
                if "statistical_analysis" in lineup_response:
                    self.log("✓ Statistical analysis included for Tatum-Brown")
        
        # Test 2: Player combinations analysis (all seasons)
        combo_response = self.make_request("GET", "/api/v1/lineups/player-combinations", {
            "player_ids": [tatum_id, brown_id],
            "team_id": self.test_data['celtics_team_id'],
            "season": "all",
            "min_minutes": 10.0
        })
        
        if combo_response:
            expected_keys = ["player_info", "summary", "games_together", "filters"]
            if self.assert_response_structure(combo_response, expected_keys, "Tatum-Brown combinations"):
                # Validate player info contains both players
                player_info = combo_response.get("player_info", [])
                if len(player_info) == 2:
                    self.log("✓ Both Tatum and Brown found in player_info")
                    
                    # Log the summary statistics for the duo
                    summary = combo_response.get("summary", {})
                    games_together = summary.get("total_games_together", 0)
                    avg_plus_minus = summary.get("average_plus_minus", 0)
                    expected_together = 601  # Known total (as of 2025)
                    
                    self.log(f"✓ Tatum-Brown played {games_together} games together with {avg_plus_minus:.1f} avg +/-")
                    
                    # Calculate coverage for games together
                    if games_together > 0:
                        together_coverage = (games_together / expected_together * 100)
                        self.log(f"✓ Duo coverage: {together_coverage:.1f}% ({games_together}/{expected_together})")
                        
                        if together_coverage > 90:
                            self.log("✓ Excellent data coverage for Tatum-Brown duo!")
                        elif together_coverage > 50:
                            self.log("⚠️  Partial data coverage - some games missing")
                        else:
                            self.log("⚠️  Low data coverage - major processing needed")
                    else:
                        self.log(f"⚠️  No games together found (expected: {expected_together})")
                        self.log("   💡 This indicates raw data processing is needed")
        
        # Test 3: Individual player stats for comparison (all seasons)
        tatum_response = self.make_request("GET", "/api/v1/player-stats", {
            "player_id": tatum_id,
            "team_id": self.test_data['celtics_team_id'],
            "season": "all",
            "limit": 1
        })
        
        brown_response = self.make_request("GET", "/api/v1/player-stats", {
            "player_id": brown_id,
            "team_id": self.test_data['celtics_team_id'],
            "season": "all",
            "limit": 1
        })
        
        if tatum_response and brown_response:
            tatum_games = tatum_response.get("total_records", 0)
            brown_games = brown_response.get("total_records", 0)
            self.log(f"✓ Individual stats in DB: Tatum {tatum_games} games, Brown {brown_games} games")
            
            # Check coverage vs expected numbers (as of 2025)
            expected_tatum = 706  # Total career games
            expected_brown = 738  # Total career games
            expected_together = 601  # Games they've played together
            
            tatum_coverage = (tatum_games / expected_tatum * 100) if expected_tatum > 0 else 0
            brown_coverage = (brown_games / expected_brown * 100) if expected_brown > 0 else 0
            
            self.log(f"✓ Data coverage: Tatum {tatum_coverage:.1f}% ({tatum_games}/{expected_tatum})")
            self.log(f"✓ Data coverage: Brown {brown_coverage:.1f}% ({brown_games}/{expected_brown})")
            self.log(f"✓ Expected Tatum-Brown games together: {expected_together}")
        
        # Test 3b: Get individual stats WITHOUT team filter to see total games
        tatum_all_teams = self.make_request("GET", "/api/v1/player-stats", {
            "player_id": tatum_id,
            "season": "all",
            "limit": 1
        })
        
        brown_all_teams = self.make_request("GET", "/api/v1/player-stats", {
            "player_id": brown_id,
            "season": "all", 
            "limit": 1
        })
        
        if tatum_all_teams and brown_all_teams:
            tatum_total = tatum_all_teams.get("total_records", 0)
            brown_total = brown_all_teams.get("total_records", 0)
            self.log(f"✓ Total career games in DB: Tatum {tatum_total}, Brown {brown_total}")
            
            # Check if they played for other teams
            if tatum_total != tatum_games:
                self.log(f"✓ Tatum played {tatum_total - tatum_games} games for other teams")
            if brown_total != brown_games:
                self.log(f"✓ Brown played {brown_total - brown_games} games for other teams")
        
        # Test 4: Common lineups featuring both players (all seasons)
        if self.test_data['celtics_team_id']:
            common_response = self.make_request("GET", f"/api/v1/lineups/common/{self.test_data['celtics_team_id']}", {
                "season": "all",
                "min_games": 3,
                "lineup_size": 5,
                "limit": 10
            })
            
            if common_response:
                lineups = common_response.get("common_lineups", [])
                tatum_brown_lineups = 0
                
                # Check how many common lineups include both players
                for lineup in lineups:
                    lineup_players = lineup.get("lineup_players", [])
                    if tatum_id in lineup_players and brown_id in lineup_players:
                        tatum_brown_lineups += 1
                
                self.log(f"✓ Found {tatum_brown_lineups} common 5-man lineups featuring both Tatum and Brown")
        
        # Test 5: Compare latest season vs all-time to show the difference
        latest_combo_response = self.make_request("GET", "/api/v1/lineups/player-combinations", {
            "player_ids": [tatum_id, brown_id],
            "team_id": self.test_data['celtics_team_id'],
            "season": "latest",
            "min_minutes": 5.0
        })
        
        if latest_combo_response and combo_response:
            latest_games = latest_combo_response.get("summary", {}).get("total_games_together", 0)
            all_time_games = combo_response.get("summary", {}).get("total_games_together", 0)
            self.log(f"✓ Season comparison: {latest_games} games (latest) vs {all_time_games} games (all-time)")
        
        # Test 6: Data coverage analysis - check what seasons we have
        season_check_response = self.make_request("GET", "/api/v1/player-stats", {
            "player_id": tatum_id,
            "season": "all",
            "limit": 50,  # Get more records to see season distribution
            "sort": "-season"
        })
        
        if season_check_response and season_check_response.get("data"):
            seasons_found = set()
            for game in season_check_response["data"]:
                if game.get("season"):
                    seasons_found.add(game["season"])
            
            seasons_list = sorted(list(seasons_found), reverse=True)
            self.log(f"✓ Database contains seasons: {', '.join(seasons_list)}")
            self.log(f"✓ Total seasons in DB: {len(seasons_list)} (Tatum entered 2017-18)")
            
            # Expected seasons for Tatum (2017-18 through 2024-25)
            expected_seasons = ["2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
            missing_seasons = [s for s in expected_seasons if s not in seasons_found]
            if missing_seasons:
                self.log(f"✓ Missing seasons: {', '.join(missing_seasons)}")
            else:
                self.log("✓ All expected Tatum seasons present")
        
        # Test 7: Raw data vs processed data comparison
        # This tests if we have raw game data that hasn't been processed into normalized tables
        self.log("Checking raw vs processed data consistency...")
        
        # Note: This would require a direct database query endpoint or raw data endpoint
        # For now, we'll test what we can through the API
        # In a real implementation, you might add an admin endpoint like:
        # GET /admin/raw-data-stats or GET /admin/data-pipeline-status
        
        # Try to test if there's a diagnostics endpoint
        diagnostic_response = self.make_request("GET", "/admin/data-stats")
        if diagnostic_response:
            self.log("✓ Found admin diagnostics endpoint")
            if "raw_game_data_count" in diagnostic_response and "processed_game_count" in diagnostic_response:
                raw_count = diagnostic_response.get("raw_game_data_count", 0)
                processed_count = diagnostic_response.get("processed_game_count", 0)
                processing_ratio = (processed_count / raw_count * 100) if raw_count > 0 else 0
                self.log(f"✓ Raw games: {raw_count}, Processed: {processed_count}")
                self.log(f"✓ Processing ratio: {processing_ratio:.1f}%")
                
                if processing_ratio < 90:
                    self.log("⚠️  Significant data processing gap detected!")
                    self.log("   💡 Run: python -m src.scripts.populate_enhanced_schema")
        else:
            self.log("ℹ️  No admin diagnostics endpoint found")
            self.log("   💡 Based on low game counts, likely need to run:")
            self.log("   💡 python -m src.scripts.populate_enhanced_schema")
            self.log("   💡 This processes raw_game_data → normalized tables")
        
        # Check if there are any obvious data processing issues by looking at data patterns
        recent_season_response = self.make_request("GET", "/api/v1/player-stats", {
            "player_id": tatum_id,
            "season": "2023-24",  # Check a specific recent season
            "limit": 100,
            "sort": "game_date"
        })
        
        if recent_season_response:
            games_2023_24 = recent_season_response.get("total_records", 0)
            self.log(f"✓ 2023-24 season has {games_2023_24} Tatum games (expected: ~70-82)")
            
            if games_2023_24 > 0:
                # Check for date gaps or missing months
                game_data = recent_season_response.get("data", [])
                if game_data:
                    dates = [game.get("game_date") for game in game_data if game.get("game_date")]
                    if dates:
                        self.log(f"✓ Date range: {min(dates)} to {max(dates)}")
                        # Check if we have reasonable game frequency
                        if len(dates) < 50:
                            self.log(f"⚠️  Low game count for full season - possible data processing issue")
            else:
                self.log("⚠️  No games found for 2023-24 - major data processing issue")
        
        # Test 8: Data completeness indicators
        # Check if processed data seems complete vs what we'd expect from raw scraping
        self.log("Analyzing data completeness patterns...")
        
        # Check multiple recent seasons to see if there's a pattern
        for season in ["2023-24", "2022-23", "2021-22"]:
            season_response = self.make_request("GET", "/api/v1/player-stats", {
                "player_id": tatum_id,
                "season": season,
                "limit": 1
            })
            
            if season_response:
                season_games = season_response.get("total_records", 0)
                self.log(f"✓ {season}: {season_games} games")
                
                # Flag seasons with unexpectedly low counts
                if season_games < 40:  # NBA season typically 70+ games
                    self.log(f"⚠️  {season} has unusually low game count - check data processing")
            else:
                self.log(f"⚠️  {season}: No data found - missing from processed tables")
        
        # Check if we have basic game metadata that should always be present
        if recent_season_response and recent_season_response.get("data"):
            sample_game = recent_season_response["data"][0]
            required_fields = ["game_id", "player_name", "team_name", "points", "game_date", "season"]
            missing_fields = [field for field in required_fields if field not in sample_game or sample_game[field] is None]
            
            if missing_fields:
                self.log(f"⚠️  Missing required fields in processed data: {missing_fields}")
                self.log("   This suggests incomplete data processing from raw_game_data")
            else:
                self.log("✓ All required fields present in processed game data")
    
    def test_error_handling(self):
        """Test API error handling"""
        self.log("Testing error handling...")
        
        # Test invalid player ID
        response = self.make_request("GET", "/api/v1/players/999999/stats")
        if response is None:
            self.log("✓ Invalid player ID properly handled")
        
        # Test invalid team ID  
        response = self.make_request("GET", "/api/v1/teams/999999/stats")
        if response is None:
            self.log("✓ Invalid team ID properly handled")
        
        # Test invalid JSON filters
        response = self.make_request("GET", "/api/v1/player-stats", {
            "filters": "invalid json"
        })
        if response is None:
            self.log("✓ Invalid JSON filters properly handled")
    
    def test_pagination(self):
        """Test pagination functionality"""
        self.log("Testing pagination...")
        
        # Test with small limit and offset
        response = self.make_request("GET", "/api/v1/player-stats", {
            "limit": 2,
            "offset": 0
        })
        
        if response:
            query_info = response.get("query_info", {})
            pagination = query_info.get("pagination", {})
            
            expected_keys = ["limit", "offset", "has_next", "has_prev"]
            if self.assert_response_structure(pagination, expected_keys, "Pagination structure"):
                # Test pagination values
                if pagination.get("limit") == 2 and pagination.get("offset") == 0:
                    self.log("✓ Pagination values correct")
                
                # Test second page
                if pagination.get("has_next"):
                    response2 = self.make_request("GET", "/api/v1/player-stats", {
                        "limit": 2,
                        "offset": 2
                    })
                    if response2:
                        self.log("✓ Next page pagination working")
    
    def run_all_tests(self):
        """Run all API endpoint tests"""
        start_time = time.time()
        
        print("=" * 60)
        print("NBA Play-by-Play API Endpoint Testing Suite")
        print("=" * 60)
        
        # Basic connectivity tests
        self.test_health_endpoint()
        self.test_root_endpoint()
        
        # Populate test data from API
        self.populate_test_data()
        
        # Player endpoints
        print("\n--- Player Endpoints ---")
        self.test_player_stats_basic()
        self.test_player_stats_with_filters()
        self.test_player_stats_by_id()
        self.test_player_search()
        self.test_player_stats_analysis()
        
        # Team endpoints
        print("\n--- Team Endpoints ---")
        self.test_team_stats_basic()
        self.test_team_stats_by_id()
        self.test_team_search()
        self.test_teams_by_season()
        self.test_head_to_head()
        self.test_team_stats_analysis()
        
        # Lineup endpoints
        print("\n--- Lineup Endpoints ---")
        self.test_lineup_stats_basic()
        self.test_common_lineups()
        self.test_player_combinations()
        self.test_tatum_brown_lineup()
        
        # General functionality
        print("\n--- General Functionality ---")
        self.test_error_handling()
        self.test_pagination()
        
        # Results summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("Test Results Summary")
        print("=" * 60)
        print(f"Tests Passed: {self.results['passed']}")
        print(f"Tests Failed: {self.results['failed']}")
        print(f"Total Duration: {duration:.2f} seconds")
        
        if self.results['errors']:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"  - {error}")
        
        if self.results['failed'] == 0:
            print("\n🎉 All tests passed!")
            return True
        else:
            print(f"\n❌ {self.results['failed']} test(s) failed")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test NBA Play-by-Play API endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL for API (default: http://localhost:8000)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Create and run test suite
    tester = APIEndpointTester(base_url=args.base_url, verbose=args.verbose)
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during testing: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()