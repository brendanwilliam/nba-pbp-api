# Analytics Module

**Status**: Active Development

**Purpose**: This module contains data analysis and insights generation components for the NBA play-by-play data.

## Implemented Components

### lineup_tracker.py
Advanced NBA lineup tracking system that determines which players are on court at any moment during a game.

**Features:**
- Detects starting lineups from game data
- Tracks all substitutions throughout the game  
- Handles period transitions (detects actual lineups at start of each quarter)
- Chain substitution detection (groups rapid multi-player substitutions)
- Phantom player detection (corrects for missing substitution data)
- Generates complete timeline of lineup states

**Usage:**
```python
from analytics.lineup_tracker import LineupTracker

# Load game JSON data
with open('game.json', 'r') as f:
    game_data = json.load(f)

# Create tracker
tracker = LineupTracker(game_data)

# Get starting lineups
home_starters, away_starters = tracker.get_starting_lineups()

# Build complete lineup timeline
timeline = tracker.build_lineup_timeline()

# Get players on court at specific moment
players = tracker.get_players_on_court(period=2, clock="PT05M30.00S")
```

**Accuracy:**
- Modern games (2017+): ~100% accuracy
- Mid-era games (2003-2015): 75-90% accuracy  
- Historical games (1996-2003): 70-75% accuracy

The reduced accuracy for historical games is due to data quality issues in the NBA's older play-by-play records.

## Planned Components

### Data Analysis
- Statistical analysis of play-by-play data
- Player performance metrics calculation
- Team analytics and comparisons
- Game flow analysis and momentum tracking

### Insights Generation
- Automated report generation
- Trend identification across seasons
- Performance pattern recognition
- Clutch time analysis

### Visualization
- Chart and graph generation for statistics
- Dashboard components for web interface
- Interactive data exploration tools

## Current Status

The lineup tracking component has been implemented and tested. Additional analytics components are planned after:
1. Completion of the NBA game data scraping (Plan 08)
2. Full population of normalized database tables (Plan 11)

## Upcoming features

### 1. Lineup tracking ✅ (Implemented)
Using play-by-play data to track who is on the court at any given moment. The `lineup_tracker.py` module provides:
- Real-time lineup states throughout games
- Substitution event tracking
- Period transition handling
- Data quality correction for missing events

This enables analytical profiles for lineup combinations, plus/minus calculations, and player combination analysis.

### 2. Score and score difference tracking
By default, the play-by-play data only includes scores when there is a change in the score. This score difference allows us to track 'momentum' in the game and the rate of change of the score for each team.

#### Score velocity
**Score velocity** is a calculation of the number of points a team has scored over the past 60 seconds. It is calculated as a rolling sum of the change in score over a window of time. We will use a window of 60 seconds for this calculation. The equation is as follows:
```
score_velocity = sum(team_score(t) - team_score(t-window_size))
```

#### Score momentum
**Score momentum** is a calculation of the change in score over the past 60 seconds. It is calculated as a rolling sum of the change in score over a window of time. We will use a window of 60 seconds for this calculation. The equation is as follows:
```
score_momentum = sum(team_score(t) - team_score(t-window_size))
```

#### Related statistics
This calculation can be used to predict the likelihood of how much will each team score by the end of the game. We can use this to calculate the expected score and score difference at any given moment in the game.

These statistics could have value to betters, analysts, and fans as it provides a way to use the play-by-play data to make predictions about the statistical outcome of a game. We could see towards the end of a game the maximum amount of points a team is capable of scoring or the likelihood of their momentum being overcome by the opposing team.

For example, the Indiana Pacers in the 2025 playoffs have had multiple games that ESPN predicted to be >99% in favor of the Pacer's o

### 3. Possession and shot clock tracking