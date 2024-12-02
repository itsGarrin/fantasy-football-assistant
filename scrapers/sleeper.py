import json

from sleeper_wrapper import League, Players, Stats


def get_player_name_from_id(player_id, player_data):
    """Convert Sleeper player ID to full name, or return the player ID if it's not numeric."""
    if not player_id.isdigit():
        return player_id  # Return player_id as is if it's not a number

    return player_data.get(player_id, {}).get('full_name', player_id)


def get_team_name_from_roster_id(roster_id, league):
    """Get team name from roster ID."""
    users = league.get_users()
    rosters = league.get_rosters()
    owner_id = next((roster["owner_id"] for roster in rosters if roster["roster_id"] == roster_id), None)

    for user in users:
        if user["user_id"] == owner_id:
            return user["display_name"]
    return "Unknown Team"


def get_team_roster(team_name, league, player_data):
    """Retrieve roster details for a specific team."""
    rosters = league.get_rosters()
    users = league.get_users()

    for user in users:
        if user["display_name"].lower() == team_name.lower():
            owner_id = user["user_id"]
            for roster in rosters:
                if roster["owner_id"] == owner_id:
                    return {
                        "team_name": team_name,
                        "owner_id": owner_id,
                        "players": [
                            get_player_name_from_id(player_id, player_data) for player_id in roster.get("players", [])
                        ],
                        "starters": [
                            get_player_name_from_id(player_id, player_data) for player_id in roster.get("starters", [])
                        ],
                        "roster_id": roster["roster_id"]
                    }
    return None


def get_league_standings(league, player_data):
    """Retrieve league standings with readable team names."""
    rosters = league.get_rosters()
    standings = []
    for roster in rosters:
        standings.append({
            "team_name": get_team_name_from_roster_id(roster["roster_id"], league),
            "wins": roster.get("settings", {}).get("wins", 0),
            "losses": roster.get("settings", {}).get("losses", 0),
            "points_for": roster.get("settings", {}).get("fpts", 0)
        })
    return sorted(standings, key=lambda x: (-x["wins"], -x["points_for"]))


def get_matchups(league, week, player_data):
    """Retrieve weekly matchups with players and team names."""
    matchups = league.get_matchups(week)
    rosters = league.get_rosters()

    roster_map = {roster["roster_id"]: get_team_name_from_roster_id(roster["roster_id"], league) for roster in rosters}
    readable_matchups = []

    # Iterate over matchups to find both teams in each matchup
    for matchup in matchups:
        team1_roster_id = matchup["roster_id"]  # Team 1's roster ID
        # Find the opponent's roster ID (assumes the matchup has two teams)
        opponent_roster_id = next((roster["roster_id"] for roster in rosters if roster["roster_id"] != team1_roster_id), None)

        if opponent_roster_id:
            team1_name = roster_map.get(team1_roster_id, "Unknown Team")
            team2_name = roster_map.get(opponent_roster_id, "Unknown Team")

            # Get players for each team
            team1_players = [get_player_name_from_id(player_id, player_data) for player_id in matchup.get("starters", [])]
            team2_players = []

            # Find opponent's players
            for roster in rosters:
                if roster["roster_id"] == opponent_roster_id:
                    team2_players = [get_player_name_from_id(player_id, player_data) for player_id in roster.get("starters", [])]
                    break

            points = matchup.get("points", 0)

            readable_matchups.append({
                "team1_name": team1_name,
                "team2_name": team2_name,
                "team1_players": team1_players,
                "team2_players": team2_players,
                "points": points
            })

    return readable_matchups


def get_player_scores(league, player_data, season_type, season, week, scoring_format="ppr"):
    """Retrieve player scores and projections for a given week based on the league's scoring format."""
    # Initialize Stats
    stats = Stats()

    # Get stats for the specified week
    week_stats = stats.get_week_stats(season_type, season, week)

    # Get projections for the specified week
    week_projections = stats.get_week_projections(season_type, season, week)

    # List to hold player scores
    player_scores = []

    # Get matchups data
    matchups = league.get_matchups(week)

    # Iterate over the matchups to fetch player data
    for matchup in matchups:
        players = matchup.get("players", [])

        for player_id in players:
            # Get player score for the selected scoring format
            player_score = stats.get_player_week_score(week_stats, player_id)
            actual_score = player_score.get(f'pts_{scoring_format}', 0)  # Format: 'pts_ppr', 'pts_std', 'pts_half_ppr'

            # Get projected score for the selected scoring format
            projected_score = week_projections.get(str(player_id), {}).get(f'pts_{scoring_format}', 0)

            # Get player name from player_data
            player_name = get_player_name_from_id(player_id, player_data)

            # Format and append player score data
            player_scores.append({
                "player_name": player_name,
                "player_id": player_id,
                "actual_score": actual_score,
                "projected_score": projected_score
            })

    return player_scores


def get_transactions(league, player_data, week):
    """Retrieve league transactions for a specific week with readable player names and roster names."""
    transactions = league.get_transactions(week)
    rosters = league.get_rosters()
    users = league.get_users()

    # Map roster IDs to team names
    roster_map = {roster["roster_id"]: get_team_name_from_roster_id(roster["roster_id"], league) for roster in rosters}

    readable_transactions = []

    for transaction in transactions:
        transaction_type = transaction.get("type", "Unknown")

        # Get added and dropped players, ensure they are not None
        added_players = transaction.get("adds", {}) or {}
        dropped_players = transaction.get("drops", {}) or {}

        # Add added players information
        for player_id, team_id in added_players.items():
            player_name = get_player_name_from_id(player_id, player_data)
            team_name = roster_map.get(team_id, "Unknown Team")
            readable_transactions.append({
                "type": f"{transaction_type} (Added)",
                "player": player_name,
                "team": team_name
            })

        # Add dropped players information
        for player_id, team_id in dropped_players.items():
            player_name = get_player_name_from_id(player_id, player_data)
            team_name = roster_map.get(team_id, "Unknown Team")
            readable_transactions.append({
                "type": f"{transaction_type} (Dropped)",
                "player": player_name,
                "team": team_name
            })

    return readable_transactions


def main():
    league_id = 1131774234440876032
    league = League(league_id)

    # Get all player data
    players = Players()
    player_data = players.get_all_players()

    # Fetch and display league users
    users = league.get_users()
    print("\nAvailable Teams:")
    for user in users:
        print(f"- {user['display_name']}")

    team_name = input("\nEnter team name to fetch roster: ")
    team_roster = get_team_roster(team_name, league, player_data)

    if team_roster:
        print("\nTeam Roster:")
        print(json.dumps(team_roster, indent=4))
    else:
        print(f"No team found with the name '{team_name}'.")

    # Fetch league standings
    standings = get_league_standings(league, player_data)
    print("\nLeague Standings:")
    for standing in standings:
        print(f"Team: {standing['team_name']}, Wins: {standing['wins']}, Losses: {standing['losses']}, Points For: {standing['points_for']}")

    # Fetch weekly matchups
    week = int(input("\nEnter week number for matchups: "))
    matchups = get_matchups(league, week, player_data)
    print(f"\nMatchups for Week {week}:")
    for matchup in matchups:
        print(f"Matchup: {matchup['team1_name']} vs {matchup['team2_name']}")
        print(f"Team 1 Players:")
        for player in matchup['team1_players']:
            print(f" - {player}")
        print(f"Team 2 Players:")
        for player in matchup['team2_players']:
            print(f" - {player}")
        print("\n")

    # Fetch player scores for the given week
    season_type = "regular"  # Can be "pre" or "regular"
    season = 2024
    player_scores = get_player_scores(league, player_data, season_type, season, week)
    print("\nPlayer Scores:")
    for score in player_scores:
        print(f"Player: {score['player_name']}, Actual: {score['actual_score']}, Projected: {score['projected_score']}")

    # Fetch transactions for the given week
    transactions = get_transactions(league, player_data, week)
    print(f"\nTransactions for Week {week}:")
    for transaction in transactions:
        print(f"Type: {transaction['type']}, Player: {transaction['player']}, Team: {transaction['team']}")


if __name__ == "__main__":
    main()
