# Analytics Module

**Status**: Planned for future development

**Purpose**: This module will contain data analysis and insights generation components for the NBA play-by-play data once the scraping and database population phases are complete.

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

This module is currently empty as it depends on:
1. Completion of the NBA game data scraping (Plan 08)
2. Implementation of the comprehensive database schema (Plans 09-10)
3. Population of normalized database tables (Plan 11)

The analytics components will be developed after the core data collection and storage infrastructure is fully operational.

## Upcoming features

### 1. Lineup tracking
We will use play-by-play data so we can track who is on the court at any given moment of any given game. This will allow us to create analytical profiles for lineup combinations.

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

For example, the Indiana Pacers in the 2025 playoffs have had multiple games that ESPN predicted to be >99% in favor of the Pacers' opponent in the final seconds. However, an analysis of Pacers' maximum score velocity and momentum would show what rate the Pacers are capable of scoring at and the likelihood of their momentum being enough to overcome the score difference at the end of the game.

Part of this analysis is the ability to predict the likelihood of a comeback or to analyze how consistant a team is in their ability to score at a high rate. I imagine this analysis could help teams select players that have a high score velocity for situations that require a comeback. Furthermore, analysts would be able to provide an accurate risk assesment of a comeback sparking performance.

### 3. Possession and shot clock tracking
Arguably the most important statistics when comparing how good teams are aross eras is defensive and offensive efficiency. These statistics are calculated by tracking the number of points a team either scores or allows per possession.

Possesion changes in basketball when one of the following occurs:
- The offensive team scores (FGM)
- The defensive team rebounds (DRB)
- The offensive player commits a turnover (foul, out-of-bounds, loss of ball, or travel, etc.) (TO)
- The defensive player commits a foul that results in a free throw (FT)

In addition, we can calculate the shotclock time remaining by tracking either:
- The time between a change of possession and the next shot attempt
- The time between an offensive player's shot attempt and the next shot attempt

Special cases:
- Offensive rebounds reset the shotclock to 14 seconds



