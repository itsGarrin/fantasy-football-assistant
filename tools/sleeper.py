from sleeper_wrapper import Stats


def get_player_projected_points(player_name, player_data, season_type, season, week, scoring_format="ppr"):
    """Retrieve the projected points for a specific player for the upcoming match."""
    stats = Stats()
    week_projections = stats.get_week_projections(season_type, season, week)

    # Find player ID from the name
    player_id = next(
        (pid for pid, pdata in player_data.items() if pdata.get("full_name").lower() == player_name.lower()), None)

    if not player_id:
        return f"Player '{player_name}' not found."

    projected_points = week_projections.get(str(player_id), {}).get(f"pts_{scoring_format}", 0)
    return projected_points

def get_player_total_projected_points(player_name, player_data, season_type, season, current_week, total_weeks=17,
                                      scoring_format="ppr"):
    """Retrieve the total projected points for a player for the rest of the season."""
    stats = Stats()
    total_projected_points = 0

    # Find player ID from the name
    player_id = next(
        (pid for pid, pdata in player_data.items() if pdata.get("full_name").lower() == player_name.lower()), None)

    if not player_id:
        return f"Player '{player_name}' not found."

    for week in range(current_week, total_weeks + 1):
        week_projections = stats.get_week_projections(season_type, season, week)
        total_projected_points += week_projections.get(str(player_id), {}).get(f"pts_{scoring_format}", 0)

    return total_projected_points