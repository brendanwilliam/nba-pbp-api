#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('.')

async def test_database():
    from src.api.utils.database import DatabaseManager
    db = DatabaseManager()
    await db.connect()
    
    # Find LeBron James
    print('🔍 Finding LeBron James:')
    result = await db.execute_query("SELECT id, player_name FROM players WHERE player_name LIKE '%LeBron%' LIMIT 1")
    
    if not result:
        print('❌ LeBron James not found')
        return
    
    lebron = result[0]
    player_id = lebron['id']
    player_name = lebron['player_name']
    
    print(f'✅ Found: {player_name} (ID: {player_id})')
    
    # Get his stats
    print('\n📊 Getting career stats:')
    stats_query = """
    SELECT COUNT(*) as games_played,
           ROUND(AVG(points), 1) as avg_points,
           ROUND(AVG(rebounds_total), 1) as avg_rebounds,
           ROUND(AVG(assists), 1) as avg_assists,
           SUM(points) as total_points,
           ROUND(AVG(CASE WHEN field_goals_attempted > 0 THEN field_goals_made::numeric / field_goals_attempted ELSE 0 END), 3) as fg_pct,
           ROUND(AVG(CASE WHEN three_pointers_attempted > 0 THEN three_pointers_made::numeric / three_pointers_attempted ELSE 0 END), 3) as three_pt_pct
    FROM player_game_stats 
    WHERE player_id = $1
    """
    
    stats_result = await db.execute_query(stats_query, player_id)
    
    if stats_result:
        stats = stats_result[0]
        print(f'✅ Games Played: {stats["games_played"]}')
        print(f'✅ Total Points: {stats["total_points"]:,}')
        print(f'✅ Points per Game: {stats["avg_points"]}')
        print(f'✅ Rebounds per Game: {stats["avg_rebounds"]}')
        print(f'✅ Assists per Game: {stats["avg_assists"]}')
        print(f'✅ Field Goal %: {stats["fg_pct"]:.1%}')
        print(f'✅ Three Point %: {stats["three_pt_pct"]:.1%}')
        
        print('\n🎯 Database is working! Your MCP server can now connect to real NBA data.')
    else:
        print('❌ No stats found')

if __name__ == "__main__":
    asyncio.run(test_database())