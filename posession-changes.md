# Possession Changes in Play-by-Play Data: July 2025

## Overview

There are a handful of events that change possession in the play-by-play data. These 'actionType' and additional conditions of these events are as follows:

| actionType | Additional Conditions | Description |
| --- | --- | --- |
| Made Shot | None | When a team makes a shot, possession changes to the other team. |
| Rebound | Defensive rebound | When the defensive team rebounds the ball, the possession changes to the defensive team. |
| Turnover | Bad Pass, Travel, etc. | When a team commits a turnover, possession changes to the other team. |
| Free Throw | (subType: "Free Throw N of N" where N is the total number of free throw attempts. On a miss, the "description" field leads with "MISS {player_last} Free Throw {n} of {N}"). If the final free throw is made, possession changes to the other team. Otherwise, possession goes to whoever rebounds the ball. | Free throws as a change of possession depend on the final free throw. If it is a make, possession changes, if it is a miss, possession goes to whoever rebounds the ball.


## Implementation/Updates

We need to update the `populate_enhanced_schema.py` script to handle possession changes. We also need to be able to include AND-1 possessions in the possession-by-possession organization.

We need to implement this in a new table titled 'play_possession_events'. This table will show the one-to-many relationship of possessions and plays. It will only include the 'posession_id' and 'play_id' columns to generate its own primary key of 'play_possession_events_id'.

We will need to update the 'play_events' table to include a 'possession_id' column to link to the 'possession_id' column in the 'possession_events' table.

In addition to this implementation, we want to be able to organize this database on a possession-by-possession basis. This will allow us to analyze possessions and their outcomes.

