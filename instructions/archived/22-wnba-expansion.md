# WNBA Expansion

## Overview

I want to add WNBA data to the API. The WNBA has data in a an identical format to the NBA at the '#__NEXT_DATA__' tag in the HTML of the NBA's game pages. The only difference is the URL patterns for WNBA games on wnba.com. We also have a disadvantage in that the WNBA does not have a game schedule page like the NBA does (this page only goes back to 2010).

We will have to implement a different scraping strategy for WNBA games to load up the queue. We will also have to be careful to create a new database instance for WNBA data and managing development between the two. While I initially thought that we might need a new repository, this is not the case. We can use the same repository but create a new database instance for WNBA data. 

My research shows that the WNBA has far fewer games than the NBA in a similarly long period of time. The first season was in 1997 and it is currently 2025. It also appears that the WNBA has been keeping track of play-by-play data since the start of the league. The number of games is as follows:
- 3060 regular season games from 1997-2024
- 271 playoff games from 1997-2024
- 3331 total games from 1997-2024

The WNBA also has a different URL pattern for games than the NBA. The NBA uses the following pattern:

Example 1: 1022500090
This is a 10 digit number starting with `10` and then a `2` for regular season and a `25` for the 2025 season. The last 5 digits are the game number, 90 in this case, represented as 00090.

Example 2: 1042400101
This is a 10 digit number starting with `10` and then a `4` for playoff games and a `24` for the 2024 season. The last 3 digits represent the round number, series id, and game number. For this example, it is round 1, series 0, and game 1, represented as 00101.

Example 3: 1040100010
This is a 10 digit number starting with `10` and then a `4` for playoff games and a `01` for the 2001 season. The last 5 digits are the game number in the playoffs. For this example, it's the 10th game of the postseason, represented as 00010.

Looking at example 1, it represents the regular season game ID convention. Example 2 is a modern playoff game ID convention. Example 3 is an older playoff game ID convention. This change likely happened at the same time as in the NBA.

When building the WNBA scraper, we can target the following URL pattern:

https://www.wnba.com/game/{game_id}/playbyplay

After the page loads, it adds the home and away team tricodes to the URL. For example url 1 becomes url 2 when the page loads:

Url 1: https://www.wnba.com/game/{game_id}/playbyplay
Url 2: https://www.wnba.com/game/{game_id}/{home_tricode}-vs-{away_tricode}/playbyplay

I want to use url 1 to find the page but save url 2 for the scraper to use. This is a workaround due to the fact that the WNBA does not have a game schedule page like the NBA does (this page only goes back to 2010).

I want to use the same scraper as the NBA scraper but modify it to use the WNBA URL pattern. If we need to make any changes to the scraper, we should do it in a way so that it can be used for both the NBA and WNBA based on a command line argument or inferring based on the URL pattern.




## Database

We will copy the schema from the nba_pbp database to the wnba_pbp database. This will allow us to use the same API for both the NBA and WNBA with only changing the database name.

## Implementation plan
(Fill this out when requested).
