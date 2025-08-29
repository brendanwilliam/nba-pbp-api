# WNBA JSON Processing Instructions

## Tables to be created

### arena
Endpoint: .boxscore.arena

Columns:
- arenaId (primary key)
- arenaCity
- arenaName
- arenaState
- arenaCountry
- arenaTimezone
- arenaPostalCode
- arenaStreetAddress

### game
Endpoint: .boxscore

Columns:
- gameId (primary key)
- gameCode
- arenaId (.boxscore.arena.arenaId)
- gameEt
- sellout
- homeTeamId
- homeTeamWins (.boxscore.homeTeam.teamWins)
- homeTeamLosses (.boxscore.homeTeam.teamLosses)
- homePlayers (.boxscore.homeTeam.players)
- awayTeamId
- awayTeamWins (.boxscore.awayTeam.teamWins)
- awayTeamLosses (.boxscore.awayTeam.teamLosses)
- awayPlayers (.boxscore.awayTeam.players)
- duration
- gameLabel
- attendance
- officials (.boxscore.officials)

### person_game
Endpoint: .boxscore (.officials and .players)

Columns:
- personGameId (generated primary key doesn't exist in JSON)
- gameId (foreign key)
- personId (foreign key)


### play
Endpoint: .postGameData.postPlayByPlayData -> .actions (for each period listed)

Columns:
- playId (generated primary key doesn't exist in JSON)
- gameId (foreign key)
- clock (formatted as PT10M00.00S for 10 minutes and 0 seconds)
- period
- teamId
- subType
- xLegacy
- yLegacy
- actionId
- location
- personId
- scoreAway
- scoreHome
- shotValue
- actionType
- shotResult
- description
- isFieldGoal
- pointsTotal
- teamTricode
- actionNumber
- shotDistance

### person
Endpoint: .postGameData.postPlayByPlayData -> .actions -> .personId

Columns:
- personId (primary key)
- name
- nameI
- firstName
- familyName

### boxscore
Endpoint: .postGameData.postBoxscoreData

Columns:
- gameId (foreign key)
- home/away team (string "h" or "a")
- teamId
- boxType (string "starters" "bench" or "player")
- personId (Only for "player" boxType. Otherwise null.)
- blocks
- points
- steals
- assists
- minutes
- turnovers
- foulsPersonal
- reboundsTotal
- fieldGoalsMade
- freeThrowsMade
- plusMinusPoints (Only for "player" boxType. Otherwise null.)
- reboundsDefensive
- reboundsOffensive
- threePointersMade
- fieldGoalsAttempted
- freeThrowsAttempted
- fieldGoalsPercentage
- freeThrowsPercentage
- threePointersAttempted
- threePointersPercentage