from sleeper_wrapper import League, Players, Stats
import globals

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


def get_trending_players(sport="nfl", add_drop="add", hours=24, limit=25):
    """Retrieve trending players on the waiver wire with more detailed player information."""
    players = Players()

    # Get all player data
    player_data = players.get_all_players()

    # Get trending players
    trending_players = players.get_trending_players(sport=sport, add_drop=add_drop, hours=hours, limit=limit)

    trending_players_info = []

    for player in trending_players:
        player_id = player.get("player_id")

        # Get player details from all players data
        player_details = player_data.get(player_id)

        if player_details:
            player_info = {
                "player_id": player_id,
                "full_name": player_details.get("full_name", "Unknown"),
                "team": player_details.get("team", "Unknown Team"),
                "position": player_details.get("position", "Unknown"),
                "trend_type": add_drop  # 'add' or 'drop'
            }
            trending_players_info.append(player_info)

    return trending_players_info


def get_league_settings(league):
    """
    Retrieve important league settings and scoring type.

    Args:
        league: Sleeper League object.

    Returns:
        A dictionary containing key league settings.
    """
    league_settings = league.get_league()

    # Extract only the important settings
    key_settings = {
        "name": league_settings.get("name", "Unknown League"),
        "season": league_settings.get("season", "Unknown Season"),
        "roster_positions": league_settings.get("roster_positions", []),
        "scoring_settings": league_settings.get("scoring_settings", "Unknown"),
        "num_teams": league_settings.get("total_rosters", 0),
        "playoff_week_start": league_settings.get("settings", {}).get("playoff_week_start", "Unknown"),
        "status": league_settings.get("status", "Unknown"),
    }

    return key_settings


def get_top_waiver_wire_players_by_position(league, season_type, season, week, player_data, top_n=10,
                                            scoring_format="ppr"):
    """
    Retrieve the top waiver wire players with the highest point projections for a given week, stratified by fantasy positions.

    Args:
        league: Sleeper League object.
        season_type: Type of season ("regular" or "post").
        season: The current season year.
        week: The week for which projections are needed.
        player_data: Dictionary of all player data.
        top_n: Number of top players to return per position.
        scoring_format: Scoring format (e.g., "ppr").

    Returns:
        Dictionary stratified by fantasy position, each containing a list of top players and their projected points.
    """
    from sleeper_wrapper import Stats

    # Initialize Stats
    stats = Stats()

    # Define valid fantasy positions
    fantasy_positions = {"QB", "RB", "WR", "TE", "K", "DEF"}

    # Get projections for the specified week
    week_projections = stats.get_week_projections(season_type, season, week)

    # Get league rosters to identify players already rostered
    rosters = league.get_rosters()
    rostered_players = {player_id for roster in rosters for player_id in roster.get("players", [])}

    # Filter waiver wire players and get projections stratified by position
    waiver_wire_projections = {}
    for player_id, projection_data in week_projections.items():
        if player_id not in rostered_players:
            projected_points = projection_data.get(f"pts_{scoring_format}", 0)
            player_name = player_data.get(player_id, {}).get("full_name", "Unknown")
            team = player_data.get(player_id, {}).get("team", "Unknown Team")
            position = player_data.get(player_id, {}).get("position", "Unknown")

            if position in fantasy_positions:
                if position not in waiver_wire_projections:
                    waiver_wire_projections[position] = []

                waiver_wire_projections[position].append({
                    "player_name": player_name,
                    "team": team,
                    "projected_points": projected_points
                })

    # Sort and truncate the top N players for each position
    stratified_top_players = {
        position: sorted(players, key=lambda x: x["projected_points"], reverse=True)[:top_n]
        for position, players in waiver_wire_projections.items()
    }

    return stratified_top_players


def get_league_info():
    league_id = globals.get_league_id()
    team_name = globals.get_team_name()
    league = League(league_id)

    # Get league settings
    league_settings = get_league_settings(league)
    scoring_type = league_settings.get("scoring_settings", {}).get("rec", "Unknown")
    globals.set_scoring_type(scoring_type)
    num_teams = league_settings.get("num_teams", 0)
    playoff_week_start = league_settings.get("playoff_week_start", "Unknown")
    result = f"League is a {scoring_type} PPR, {num_teams}-team league.\n"
    if playoff_week_start != "Unknown":
        result += f"Playoffs start in Week {playoff_week_start}.\n\n"

    # Get all player data
    players = Players()
    player_data = players.get_all_players()

    # Fetch league users and their rosters
    rosters = league.get_rosters()

    # Highlight user's team
    user_roster = get_team_roster(team_name, league, player_data)

    if user_roster:
        result += f"Your Team: {user_roster['team_name']}\n\n"
    else:
        result += f"No team found with the name '{team_name}'.\n\n"

    result += "Teams and Records:\n"
    for roster in rosters:
        team_name = get_team_name_from_roster_id(roster["roster_id"], league)
        wins = roster.get("settings", {}).get("wins", 0)
        losses = roster.get("settings", {}).get("losses", 0)
        points_for = roster.get("settings", {}).get("fpts", 0)
        players_list = [
            get_player_name_from_id(player_id, player_data) for player_id in roster.get("players", [])
        ]

        result += f"- {team_name}: {wins}-{losses} record, {points_for} points for\n"
        result += f"  Roster: {', '.join(players_list)}\n"

    return result


if __name__ == "__main__":
    get_league_info()
