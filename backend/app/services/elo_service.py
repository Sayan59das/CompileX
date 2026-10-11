"""
ELO Rating Service for CompileX
Handles skill assessment quiz scoring and ELO updates after matches.

ELO Ranges:
  < 800   → Beginner
  800-1200 → Intermediate
  1200-1600 → Advanced
  1600+   → Expert
"""

from typing import Tuple


# ── ELO Constants ─────────────────────────────────────────────────────────────
K_FACTOR_NEW = 40       # First 10 games — high volatility
K_FACTOR_NORMAL = 20    # Standard games
K_FACTOR_EXPERT = 10    # Rating > 2000 — stabilizes at top

STARTING_RATING = 1000
MIN_RATING = 100
MAX_RATING = 3000


# ── Tier Labels ────────────────────────────────────────────────────────────────
def get_tier(rating: int) -> dict:
    """Return tier name, color, and icon based on rating."""
    if rating < 800:
        return {"name": "Beginner",     "color": "#6b7280", "icon": "🌱", "range": "< 800"}
    elif rating < 1200:
        return {"name": "Intermediate", "color": "#10b981", "icon": "⚡", "range": "800–1200"}
    elif rating < 1600:
        return {"name": "Advanced",     "color": "#3b82f6", "icon": "🔥", "range": "1200–1600"}
    elif rating < 2000:
        return {"name": "Expert",       "color": "#8b5cf6", "icon": "💎", "range": "1600–2000"}
    else:
        return {"name": "Master",       "color": "#f59e0b", "icon": "👑", "range": "2000+"}


def get_difficulty_for_rating(rating: int) -> str:
    """Map a user's ELO rating to a recommended difficulty level."""
    if rating < 900:
        return "easy"
    elif rating < 1300:
        return "medium"
    else:
        return "hard"


# ── Skill Quiz → Initial Rating ────────────────────────────────────────────────
def calculate_initial_rating(quiz_results: list[dict]) -> int:
    """
    Convert real code execution quiz results into an initial ELO rating.

    Each quiz_result dict:
      { "difficulty": "easy"|"medium"|"hard"|"expert",
        "solved": bool,
        "time_taken_seconds": int,
        "points_earned": int,   # optional — from actual test case execution
        "topic": str }          # optional — for topic-based weighting

    Scoring model:
      Base = 600 (everyone starts here)
      Each solved question adds weighted points based on difficulty + speed.
      Partial credit (points_earned > 0 but not fully solved) adds partial points.
    """
    if not quiz_results:
        return STARTING_RATING  # Default 1000 for skippers

    base = 600
    score = 0

    difficulty_weights = {
        "easy":   150,
        "medium": 280,
        "hard":   420,
        "expert": 580,
    }

    for result in quiz_results:
        diff = result.get("difficulty", "easy")
        solved = result.get("solved", False)
        time_taken = result.get("time_taken_seconds", 9999)
        points_earned = result.get("points_earned", 0)
        max_pts = difficulty_weights.get(diff, 150)

        if solved:
            score += max_pts
            # Speed bonus: faster = more points
            if time_taken < 30:
                score += 80
            elif time_taken < 60:
                score += 50
            elif time_taken < 120:
                score += 25
            elif time_taken < 180:
                score += 10
        elif points_earned and points_earned > 0:
            # Partial credit from actual test case execution
            score += int(max_pts * 0.4)

    rating = base + score
    return max(500, min(2000, rating))


# ── ELO Update After Match ─────────────────────────────────────────────────────
def _k_factor(rating: int, games_played: int) -> int:
    if games_played < 10:
        return K_FACTOR_NEW
    elif rating >= 2000:
        return K_FACTOR_EXPERT
    return K_FACTOR_NORMAL


def _expected_score(rating_a: int, rating_b: int) -> float:
    """Expected score for player A against player B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def calculate_elo_change(
    winner_rating: int,
    loser_rating: int,
    winner_games: int,
    loser_games: int,
) -> Tuple[int, int]:
    """
    Calculate new ratings for winner and loser.
    Returns (winner_new_rating, loser_new_rating).
    """
    k_winner = _k_factor(winner_rating, winner_games)
    k_loser  = _k_factor(loser_rating,  loser_games)

    expected_winner = _expected_score(winner_rating, loser_rating)
    expected_loser  = _expected_score(loser_rating,  winner_rating)

    winner_new = round(winner_rating + k_winner * (1 - expected_winner))
    loser_new  = round(loser_rating  + k_loser  * (0 - expected_loser))

    # Clamp
    winner_new = max(MIN_RATING, min(MAX_RATING, winner_new))
    loser_new  = max(MIN_RATING, min(MAX_RATING, loser_new))

    return winner_new, loser_new


def calculate_elo_draw(
    rating_a: int,
    rating_b: int,
    games_a: int,
    games_b: int,
) -> Tuple[int, int]:
    """Calculate new ratings for a draw."""
    k_a = _k_factor(rating_a, games_a)
    k_b = _k_factor(rating_b, games_b)

    expected_a = _expected_score(rating_a, rating_b)
    expected_b = _expected_score(rating_b, rating_a)

    new_a = round(rating_a + k_a * (0.5 - expected_a))
    new_b = round(rating_b + k_b * (0.5 - expected_b))

    new_a = max(MIN_RATING, min(MAX_RATING, new_a))
    new_b = max(MIN_RATING, min(MAX_RATING, new_b))

    return new_a, new_b
