from sleeper_wrapper import Stats, Players
import tools.utils as utils
from typing import List
import globals
player_data = Players().get_all_players()
season_type = "regular"

def get_player_projected_points(player_name: str, season : int, weeks : str) -> str:
    """
    Retrieve the projected fantasy points for a specific player for the given match week.

    Parameters:
    ----------
    player_name : str
        The full name of the player (case insensitive).
    season : int
        The season year (e.g., 2024).
    week : str
        The week numbers for which to retrieve projections. Must be a comma-separated string of week numbers, for example, "1,2,3".

    Returns:
    -------
    str:
        The projected fantasy points for the player in the specified week.

    Notes:
    ------
    - The function uses Sleeper API data to retrieve player projections.
    - Player projections are derived based on the season type ("regular").
    - Ensure the player data is up to date to prevent missing or incorrect projections.

    Examples:
    ---------
    >>> get_player_projected_points("Christian McCaffrey", 2024, 8)
    Christian McCaffrey is projected to score 20.5 points in week 8.
    >>> get_player_projected_points("Nonexistent Player", 2024, 8)
    "Player 'Nonexistent Player' not found."
    """
    player_name = utils.convert_player_name(player_name)
    stats = Stats()
    print(weeks)
    # convert comma-separated string to list of integers
    weeks = list(map(int, weeks.split(",")))

    player_id = utils.convert_player_name_to_sleeper_id(player_name)

    if not player_id:
        return f"Player '{player_name}' not found."
    
    scoring_format = utils.convert_scoring_type_to_text(globals.get_scoring_type())

    week_str = ""


    for week in weeks:
        print(season_type, season, week)
        week_projections = stats.get_week_projections(season_type, season, week)
        projected_points = week_projections.get(str(player_id), {}).get(f"pts_{scoring_format}", 0)
        week_str += f"According to Sleeper, {player_name} is projected to score {projected_points} points in week {week}.\n"

    return week_str


def get_player_total_projected_points(player_name, season, current_week, total_weeks=17, scoring_format="ppr"):
    """
    Calculate the total projected fantasy points for a specific player for the rest of the season.

    Parameters:
    ----------
    player_name : str
        The full name of the player (case insensitive).
    season : int
        The season year (e.g., 2024).
    current_week : int
        The current week number (e.g., 8). The calculation starts from this week onward.
    total_weeks : int, optional
        The total number of weeks in the season (default is 17). Adjust for custom leagues.
    scoring_format : str, optional
        The scoring format for projections (default is "ppr"). Options include:
        - "ppr" for points per reception
        - "half_ppr" for half points per reception
        - "standard" for no points per reception

    Returns:
    -------
    float
        The total projected fantasy points for the player for the rest of the season in the specified scoring format.
    str
        If the player's name is not found in the dataset, a descriptive error message is returned.

    Notes:
    ------
    - The function aggregates weekly projections from the current week to the end of the season.
    - Player projections are based on the Sleeper API's data for the "regular" season.
    - Use this function to evaluate long-term potential when making trades or waiver wire decisions.

    Examples:
    ---------
    >>> get_player_total_projected_points("Justin Jefferson", 2024, 8)
    105.3
    >>> get_player_total_projected_points("Nonexistent Player", 2024, 8)
    "Player 'Nonexistent Player' not found."
    """
    player_name = utils.convert_player_name(player_name)

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



get_player_projected_points_tool = {
    'type': 'function',
    'function': {
        'name': 'get_player_projected_points',
        'description': 'Get the projected points for a player',
        'parameters': {
            'type': 'object',
            'required': ['player_name', 'season', 'weeks'],
            'properties': {
                'player_name': {'type': 'string', 'description': 'The name of the player'},
                'season': {'type': 'integer', 'description': 'The season year'},
                'weeks': {'type': 'string', 'description': 'The week numbers for which to retrieve projections. Must be a comma-separated string of week numbers, for example, "1,2,3".'},
            },
        },
    },
}
