from typing import List, Dict, Tuple
from openskill.models import PlackettLuce, PlackettLuceRating
from app.models import SpeakerSlot

DEFAULT_MU = 1000.0
DEFAULT_SIGMA = DEFAULT_MU / 3.0

pl_model = PlackettLuce(mu=DEFAULT_MU, sigma=DEFAULT_SIGMA)


def compute_bp_elo(slots: List[SpeakerSlot], ranks: Dict[str, int]) -> List[Tuple[SpeakerSlot, float, float]]:
    """Return list of (slot, old_elo, new_elo) after rating update."""
    teams: Dict[str, List[SpeakerSlot]] = {}
    for slot in slots:
        team = slot.role.split('-')[0]
        teams.setdefault(team, []).append(slot)

    # Ensure teams order stable for rating call
    ordered_teams = sorted(teams.keys(), key=lambda t: ranks.get(t, 5))
    team_ratings = []
    for team in ordered_teams:
        rating_team = []
        for slot in teams[team]:
            mu = float(slot.user.elo_rating or DEFAULT_MU)
            sigma = float(getattr(slot.user, 'elo_sigma', DEFAULT_SIGMA) or DEFAULT_SIGMA)
            rating_team.append(PlackettLuceRating(mu=mu, sigma=sigma))
        team_ratings.append(rating_team)

    ranks_list = [ranks.get(team, 4) for team in ordered_teams]
    new_ratings = pl_model.rate(team_ratings, ranks=ranks_list)

    updates: List[Tuple[SpeakerSlot, float, float]] = []
    for team_idx, team in enumerate(ordered_teams):
        for player_idx, slot in enumerate(teams[team]):
            old_mu = float(slot.user.elo_rating or DEFAULT_MU)
            old_sigma = float(getattr(slot.user, 'elo_sigma', DEFAULT_SIGMA) or DEFAULT_SIGMA)
            new_mu = round(float(new_ratings[team_idx][player_idx].mu), 2)
            new_sigma = float(new_ratings[team_idx][player_idx].sigma)
            slot.user.elo_rating = new_mu
            if hasattr(slot.user, 'elo_sigma'):
                slot.user.elo_sigma = new_sigma
            updates.append((slot, old_mu, new_mu))
    return updates
