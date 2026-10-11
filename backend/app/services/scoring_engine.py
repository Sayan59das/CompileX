from app.services.lobby_manager import LobbyState


class ScoringConfig:
    """Tweak these to change how points are awarded across the whole app."""
    BASE_POINTS: int = 100
    TIME_BONUS_MAX: int = 50
    EFFICIENCY_WEIGHT: float = 0.2

    @classmethod
    def set_base_points(cls, points: int):
        cls.BASE_POINTS = points

    @classmethod
    def set_time_bonus(cls, bonus: int):
        cls.TIME_BONUS_MAX = bonus

    @classmethod
    def set_efficiency_weight(cls, weight: float):
        cls.EFFICIENCY_WEIGHT = max(0.0, min(1.0, weight))


class ScoringEngine:

    def calculate_dynamic_score(
        self,
        base_points: int,
        passed_tests: int,
        total_tests: int,
        execution_time_ms: float,
        max_execution_time_ms: int,
        time_bonus_max: int = 50,
    ) -> dict:
        passed_ratio = passed_tests / max(total_tests, 1)
        base_score = int(base_points * passed_ratio)

        time_ratio = 0.0
        time_bonus = 0

        # only award time bonus if all tests passed
        if passed_tests == total_tests and execution_time_ms > 0:
            time_ratio = max(0.0, 1 - (execution_time_ms / max_execution_time_ms))
            time_bonus = int(time_bonus_max * time_ratio)

        efficiency_bonus = int(base_score * ScoringConfig.EFFICIENCY_WEIGHT * time_ratio)

        return {
            "base_score": base_score,
            "time_bonus": time_bonus,
            "efficiency_bonus": efficiency_bonus,
            "total_score": base_score + time_bonus + efficiency_bonus,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "execution_time_ms": execution_time_ms,
        }

    def get_leaderboard(self, lobby: LobbyState) -> list:
        ranked = sorted(lobby.players.values(), key=lambda p: (-p.score, p.questions_solved))
        return [
            {
                "rank": i + 1,
                "player_id": p.id,
                "username": p.username,
                "score": p.score,
                "questions_solved": p.questions_solved,
            }
            for i, p in enumerate(ranked)
        ]


scoring_engine = ScoringEngine()
