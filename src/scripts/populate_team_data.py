"""Populate team data from Wikipedia and Basketball Reference."""

import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import json
import re
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/nba_pbp")

# Team mappings for Basketball Reference
TEAM_TRICODE_TO_BR = {
    'ATL': 'ATL', 'BOS': 'BOS', 'BKN': 'BRK', 'CHA': 'CHO', 'CHI': 'CHI',
    'CLE': 'CLE', 'DAL': 'DAL', 'DEN': 'DEN', 'DET': 'DET', 'GSW': 'GSW',
    'HOU': 'HOU', 'IND': 'IND', 'LAC': 'LAC', 'LAL': 'LAL', 'MEM': 'MEM',
    'MIA': 'MIA', 'MIL': 'MIL', 'MIN': 'MIN', 'NOP': 'NOP', 'NYK': 'NYK',
    'OKC': 'OKC', 'ORL': 'ORL', 'PHI': 'PHI', 'PHX': 'PHO', 'POR': 'POR',
    'SAC': 'SAC', 'SAS': 'SAS', 'TOR': 'TOR', 'UTA': 'UTA', 'WAS': 'WAS'
}


def scrape_wikipedia_teams():
    """Scrape team data from Wikipedia NBA page."""
    print("Scraping team data from Wikipedia...")
    url = "https://en.wikipedia.org/wiki/National_Basketball_Association"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the teams table
        teams_data = {}
        
        # Look for Eastern and Western Conference sections
        conferences = ['Eastern Conference', 'Western Conference']
        
        for conference in conferences:
            # Find conference header
            conf_header = soup.find('span', {'id': conference.replace(' ', '_')})
            if not conf_header:
                continue
                
            # Navigate to find the teams table
            current = conf_header.parent
            while current and current.name != 'table':
                current = current.find_next_sibling()
                if current and 'wikitable' in current.get('class', []):
                    break
            
            if current and current.name == 'table':
                rows = current.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        # Extract team name and link
                        team_cell = cells[0]
                        team_link = team_cell.find('a')
                        
                        if team_link:
                            team_name = team_link.text.strip()
                            wiki_url = 'https://en.wikipedia.org' + team_link.get('href', '')
                            
                            # Extract division
                            division = None
                            prev_row = row.find_previous_sibling('tr')
                            if prev_row and 'Division' in prev_row.text:
                                division = prev_row.text.strip().replace(' Division', '')
                            
                            teams_data[team_name] = {
                                'conference': conference.split()[0],
                                'division': division,
                                'wikipedia_url': wiki_url
                            }
        
        return teams_data
    
    except Exception as e:
        print(f"Error scraping Wikipedia: {e}")
        return {}


def scrape_basketball_reference(tricode):
    """Scrape team data from Basketball Reference."""
    br_code = TEAM_TRICODE_TO_BR.get(tricode, tricode)
    url = f"https://www.basketball-reference.com/teams/{br_code}/"
    
    print(f"Scraping Basketball Reference for {tricode} ({br_code})...")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"  Status code: {response.status_code}")
            return {}
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        data = {'basketball_ref_url': url}
        
        # Debug: print what we find
        info_div = soup.find('div', {'id': 'meta'})
        if info_div:
            # Extract team name
            h1 = info_div.find('h1')
            if h1:
                # Look for team name in different formats
                spans = h1.find_all('span')
                if spans:
                    full_name = spans[0].text.strip()
                    data['full_name'] = full_name
                else:
                    data['full_name'] = h1.text.strip()
            
            # Extract other info from data rows
            data_rows = info_div.find_all(['p', 'div'])
            for row in data_rows:
                text = row.text.strip()
                
                # Founded year - look for different patterns
                if 'Season' in text and '-' in text:
                    # Try to extract first season
                    match = re.search(r'(\d{4})-\d{2}', text)
                    if match:
                        data['founded'] = int(match.group(1))
                
                # Look for strong tags with labels
                strong_tags = row.find_all('strong')
                for strong in strong_tags:
                    label = strong.text.strip(':').lower()
                    
                    # Get the text after the strong tag
                    next_text = strong.next_sibling
                    if next_text:
                        value = str(next_text).strip()
                        
                        if 'arena' in label:
                            data['arena'] = value
                        elif 'owner' in label:
                            data['owner'] = value
                        elif 'executive' in label or 'general manager' in label:
                            data['general_manager'] = value
                        elif 'coach' in label:
                            data['head_coach'] = value
        
        print(f"  Found data: {list(data.keys())}")
        time.sleep(2)  # Be more respectful to the server
        return data
    
    except Exception as e:
        print(f"Error scraping Basketball Reference for {tricode}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def update_teams_data():
    """Update teams table with scraped data."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get existing teams
        cur.execute("SELECT id, tricode, name, city FROM teams")
        teams = cur.fetchall()
        
        # Scrape Wikipedia data
        wiki_data = scrape_wikipedia_teams()
        
        # Update each team
        for team in teams:
            tricode = team['tricode']
            team_name = team['name']
            city = team['city']
            full_name = f"{city} {team_name}"
            
            print(f"\nProcessing {full_name} ({tricode})...")
            
            # Get Wikipedia data
            wiki_info = wiki_data.get(full_name, {})
            if not wiki_info:
                # Try alternative names
                for wiki_team, info in wiki_data.items():
                    if team_name in wiki_team or city in wiki_team:
                        wiki_info = info
                        break
            
            # Scrape Basketball Reference
            br_data = scrape_basketball_reference(tricode)
            
            # Prepare update data
            update_data = {
                'team_tricode': tricode,
                'conference': wiki_info.get('conference'),
                'division': wiki_info.get('division'),
                'wikipedia_url': wiki_info.get('wikipedia_url'),
                'full_name': br_data.get('full_name', full_name),
                'nickname': team_name,
                'founded': br_data.get('founded'),
                'arena': br_data.get('arena'),
                'owner': br_data.get('owner'),
                'general_manager': br_data.get('general_manager'),
                'head_coach': br_data.get('head_coach'),
                'basketball_ref_url': br_data.get('basketball_ref_url')
            }
            
            # Update team record
            update_query = """
                UPDATE teams 
                SET team_tricode = %(team_tricode)s,
                    conference = %(conference)s,
                    division = %(division)s,
                    wikipedia_url = %(wikipedia_url)s,
                    full_name = %(full_name)s,
                    nickname = %(nickname)s,
                    founded = %(founded)s,
                    arena = %(arena)s,
                    owner = %(owner)s,
                    general_manager = %(general_manager)s,
                    head_coach = %(head_coach)s,
                    basketball_ref_url = %(basketball_ref_url)s,
                    updated_at = NOW()
                WHERE id = %(id)s
            """
            update_data['id'] = team['id']
            
            cur.execute(update_query, update_data)
            print(f"Updated {full_name} with {len([v for v in update_data.values() if v])} fields")
        
        # Assign team_id based on some logic (using row number for now)
        cur.execute("""
            WITH numbered_teams AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY tricode) as team_num
                FROM teams
            )
            UPDATE teams t
            SET team_id = nt.team_num
            FROM numbered_teams nt
            WHERE t.id = nt.id
        """)
        
        conn.commit()
        print("\nTeam data population complete!")
        
        # Show summary
        cur.execute("""
            SELECT COUNT(*) as total,
                   COUNT(conference) as with_conference,
                   COUNT(arena) as with_arena,
                   COUNT(founded) as with_founded
            FROM teams
        """)
        summary = cur.fetchone()
        print(f"\nSummary:")
        print(f"Total teams: {summary['total']}")
        print(f"Teams with conference: {summary['with_conference']}")
        print(f"Teams with arena: {summary['with_arena']}")
        print(f"Teams with founded year: {summary['with_founded']}")
        
    except Exception as e:
        print(f"Error updating teams: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def update_player_team_relationships():
    """Update player_team table with more accurate team IDs."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # First, let's check current state
        cur.execute("""
            SELECT COUNT(*) as total_relationships,
                   COUNT(DISTINCT person_id) as unique_players,
                   COUNT(DISTINCT team_id) as unique_teams
            FROM player_team
        """)
        result = cur.fetchone()
        print(f"\nPlayer-Team relationships:")
        print(f"Total relationships: {result[0]}")
        print(f"Unique players: {result[1]}")
        print(f"Unique teams: {result[2]}")
        
        conn.commit()
        
    except Exception as e:
        print(f"Error updating player-team relationships: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print("Starting team data population...")
    update_teams_data()
    update_player_team_relationships()