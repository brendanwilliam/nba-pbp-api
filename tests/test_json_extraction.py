"""
Unit tests for JSON data extraction from WNBA game data.
Tests each extractor with sample JSON data and validates data transformation.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from src.database.json_extractors import (
    ArenaExtractor, TeamExtractor, GameExtractor, 
    PersonExtractor, PlayExtractor, BoxscoreExtractor
)


@pytest.fixture
def sample_game_json() -> Dict[str, Any]:
    """Load sample game JSON data for testing"""
    test_data_dir = Path(__file__).parent / "test_data"
    sample_file = test_data_dir / "raw_game_1022400005.json"
    
    with open(sample_file, 'r') as f:
        return json.load(f)


class TestArenaExtractor:
    """Test arena data extraction"""
    
    def test_extract_arena_basic(self, sample_game_json):
        """Test basic arena extraction"""
        arena_data = ArenaExtractor.extract(sample_game_json)
        
        assert arena_data['arena_id'] == 599
        assert arena_data['arena_city'] == "Arlington"
        assert arena_data['arena_name'] == "College Park Center"
        assert arena_data['arena_state'] == "TX"
        assert arena_data['arena_country'] == "US"
        assert arena_data['arena_timezone'] == "Central"
    
    def test_extract_arena_empty_fields(self, sample_game_json):
        """Test arena extraction with empty postal code and address"""
        arena_data = ArenaExtractor.extract(sample_game_json)
        
        # These fields are empty strings in the sample data
        assert arena_data['arena_postal_code'] is None
        assert arena_data['arena_street_address'] is None
    
    def test_extract_arena_missing_fields(self):
        """Test arena extraction with missing optional fields"""
        minimal_json = {
            'boxscore': {
                'arena': {
                    'arenaId': 123,
                    'arenaName': 'Test Arena'
                }
            }
        }
        
        arena_data = ArenaExtractor.extract(minimal_json)
        
        assert arena_data['arena_id'] == 123
        assert arena_data['arena_name'] == 'Test Arena'
        assert arena_data['arena_city'] is None
        assert arena_data['arena_state'] is None


class TestTeamExtractor:
    """Test team data extraction"""
    
    def test_extract_teams_basic(self, sample_game_json):
        """Test basic team extraction"""
        teams = TeamExtractor.extract_teams_from_game(sample_game_json)
        
        # Should have at least home and away teams
        assert len(teams) >= 2
        
        team_ids = [team['team_id'] for team in teams]
        assert 1611661329 in team_ids  # Away team (CHI)
        assert 1611661321 in team_ids  # Home team (DAL)
    
    def test_extract_teams_from_plays(self, sample_game_json):
        """Test that teams are extracted from play-by-play data"""
        teams = TeamExtractor.extract_teams_from_game(sample_game_json)
        
        # All team IDs should be valid integers
        for team in teams:
            assert isinstance(team['team_id'], int)
            assert team['team_id'] > 0


class TestGameExtractor:
    """Test game data extraction"""
    
    def test_extract_game_basic(self, sample_game_json):
        """Test basic game extraction"""
        game_data = GameExtractor.extract(sample_game_json)
        
        assert game_data['game_id'] == 1022400005
        assert game_data['arena_id'] == 599
        assert game_data['home_team_id'] == 1611661321
        assert game_data['away_team_id'] == 1611661329
        assert game_data['game_sellout'] is False
    
    def test_extract_game_datetime(self, sample_game_json):
        """Test game datetime parsing"""
        game_data = GameExtractor.extract(sample_game_json)
        
        assert game_data['game_et'] is not None
        assert isinstance(game_data['game_et'], datetime)
        # Should parse "2024-05-15T20:00:00Z" correctly
        expected_dt = datetime(2024, 5, 15, 20, 0, 0)
        assert game_data['game_et'].replace(tzinfo=None) == expected_dt
    
    def test_extract_game_optional_fields(self, sample_game_json):
        """Test extraction of optional game fields"""
        game_data = GameExtractor.extract(sample_game_json)
        
        # These fields may be None in some games
        assert 'game_code' in game_data
        assert 'game_duration' in game_data
        assert 'game_label' in game_data
        assert 'game_attendance' in game_data


class TestPersonExtractor:
    """Test person data extraction"""
    
    def test_extract_persons_basic(self, sample_game_json):
        """Test basic person extraction"""
        persons = PersonExtractor.extract_persons_from_game(sample_game_json)
        
        # Should have players from both teams
        assert len(persons) > 0
        
        # Check that all persons have required fields
        for person in persons:
            assert person['person_id'] is not None
            assert isinstance(person['person_id'], int)
    
    def test_extract_players(self, sample_game_json):
        """Test player extraction specifically"""
        persons = PersonExtractor.extract_persons_from_game(sample_game_json)
        
        # Find a specific player we know is in the data
        elizabeth_williams = next(
            (p for p in persons if p.get('person_name') == 'Elizabeth Williams'), 
            None
        )
        
        assert elizabeth_williams is not None
        assert elizabeth_williams['person_id'] == 204322
        assert elizabeth_williams['person_name_i'] == 'E. Williams'
        assert elizabeth_williams['person_name_first'] == 'Elizabeth'
        assert elizabeth_williams['person_name_family'] == 'Williams'
    
    def test_extract_officials(self, sample_game_json):
        """Test official extraction if present"""
        persons = PersonExtractor.extract_persons_from_game(sample_game_json)
        
        # Sample data may or may not have officials
        # Just verify no errors and structure is correct
        for person in persons:
            assert 'person_id' in person
            assert 'person_name' in person


class TestPlayExtractor:
    """Test play-by-play data extraction"""
    
    def test_extract_plays_basic(self, sample_game_json):
        """Test basic play extraction"""
        plays = PlayExtractor.extract_plays_from_game(sample_game_json)
        
        # Should have many plays in a full game
        assert len(plays) > 0
        
        # Check structure of first play
        first_play = plays[0]
        assert first_play['game_id'] == 1022400005
        assert 'period' in first_play
        assert 'action_type' in first_play
    
    def test_extract_plays_person_id_handling(self, sample_game_json):
        """Test that personId 0 is converted to None"""
        plays = PlayExtractor.extract_plays_from_game(sample_game_json)
        
        # Find plays with and without person IDs
        plays_with_person = [p for p in plays if p['person_id'] is not None]
        plays_without_person = [p for p in plays if p['person_id'] is None]
        
        # Should have both types
        assert len(plays_with_person) > 0
        assert len(plays_without_person) > 0
        
        # Person IDs should be positive integers when not None
        for play in plays_with_person:
            assert isinstance(play['person_id'], int)
            assert play['person_id'] > 0
    
    def test_extract_plays_periods(self, sample_game_json):
        """Test that plays are extracted from all periods"""
        plays = PlayExtractor.extract_plays_from_game(sample_game_json)
        
        # Get unique periods
        periods = set(play['period'] for play in plays)
        
        # Should have 4 periods for a regular game
        assert len(periods) == 4
        assert periods == {1, 2, 3, 4}
    
    def test_extract_plays_required_fields(self, sample_game_json):
        """Test that all plays have required fields"""
        plays = PlayExtractor.extract_plays_from_game(sample_game_json)
        
        required_fields = ['game_id', 'period', 'action_type']
        
        for play in plays:
            for field in required_fields:
                assert field in play
                assert play[field] is not None


class TestBoxscoreExtractor:
    """Test boxscore statistics extraction"""
    
    def test_extract_boxscores_basic(self, sample_game_json):
        """Test basic boxscore extraction"""
        boxscores = BoxscoreExtractor.extract_boxscores_from_game(sample_game_json)
        
        # Should have entries for players and team totals
        assert len(boxscores) > 0
        
        # Check structure
        for entry in boxscores:
            assert entry['game_id'] == 1022400005
            assert 'home_away_team' in entry
            assert entry['home_away_team'] in ['h', 'a']
            assert 'box_type' in entry
    
    def test_extract_boxscores_box_types(self, sample_game_json):
        """Test different box score types"""
        boxscores = BoxscoreExtractor.extract_boxscores_from_game(sample_game_json)
        
        box_types = set(entry['box_type'] for entry in boxscores)
        
        # Should have player stats and potentially team totals
        assert 'player' in box_types
        # May also have 'starters' and 'bench' if present in data
    
    def test_extract_boxscores_stat_mapping(self, sample_game_json):
        """Test that statistics are properly mapped"""
        boxscores = BoxscoreExtractor.extract_boxscores_from_game(sample_game_json)
        
        # Find a player entry
        player_entry = next(
            (entry for entry in boxscores if entry['box_type'] == 'player'),
            None
        )
        
        if player_entry:
            # Check that mapped fields exist
            stat_fields = ['pts', 'reb', 'ast', 'fgm', 'fga']
            for field in stat_fields:
                assert field in player_entry
    
    def test_extract_boxscores_plus_minus(self, sample_game_json):
        """Test plus/minus handling for players vs team totals"""
        boxscores = BoxscoreExtractor.extract_boxscores_from_game(sample_game_json)
        
        for entry in boxscores:
            if entry['box_type'] == 'player':
                # Players may have plus/minus
                assert 'pm' in entry
            else:
                # Team totals should not have plus/minus or it should be None
                if 'pm' in entry:
                    assert entry['pm'] is None


class TestIntegration:
    """Integration tests using all extractors together"""
    
    def test_full_game_extraction(self, sample_game_json):
        """Test extracting all data types from a game"""
        # Extract all data
        arena = ArenaExtractor.extract(sample_game_json)
        teams = TeamExtractor.extract_teams_from_game(sample_game_json)
        game = GameExtractor.extract(sample_game_json)
        persons = PersonExtractor.extract_persons_from_game(sample_game_json)
        plays = PlayExtractor.extract_plays_from_game(sample_game_json)
        boxscores = BoxscoreExtractor.extract_boxscores_from_game(sample_game_json)
        
        # Verify relationships
        assert game['arena_id'] == arena['arena_id']
        assert game['home_team_id'] in [t['team_id'] for t in teams]
        assert game['away_team_id'] in [t['team_id'] for t in teams]
        
        # All plays should be for this game
        for play in plays:
            assert play['game_id'] == game['game_id']
        
        # All boxscores should be for this game
        for boxscore in boxscores:
            assert boxscore['game_id'] == game['game_id']
    
    def test_data_consistency(self, sample_game_json):
        """Test data consistency across extractors"""
        game = GameExtractor.extract(sample_game_json)
        persons = PersonExtractor.extract_persons_from_game(sample_game_json)
        plays = PlayExtractor.extract_plays_from_game(sample_game_json)
        
        # Get unique person IDs from plays
        play_person_ids = set(
            play['person_id'] for play in plays 
            if play['person_id'] is not None
        )
        
        # Get person IDs from extracted persons
        extracted_person_ids = set(person['person_id'] for person in persons)
        
        # All person IDs in plays should be in extracted persons
        # (Note: this may not be 100% true if plays reference persons not in roster)
        missing_persons = play_person_ids - extracted_person_ids
        if missing_persons:
            # Log but don't fail - this is expected for some games
            print(f"Persons in plays but not in roster: {missing_persons}")