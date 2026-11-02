"""Which questions a player has already been given, per (topic, difficulty).

The question database does not know about players. History lives in Redis:
    seen:{player}:{topic}:{difficulty}    a set of question ids, with a TTL that is renewed whenever the player gets a question
    served:{player}:{topic}:{difficulty}  a sorted set of the same ids scored by the time they were served (for the fallback
                                           that repeats the question seen longest ago)
A lobby is several players who get the same question, so every read takes a list of players and answers for all of them together.

All access goes through SeenStore, so history can later be sharded by player id (a store that picks a Redis per player) without
changing the API. The trigger for doing that is documented in the README: sustained history-lookup latency above target under load.
"""

import time


class SeenStore:
    """The interface."""

    def seen(self, player_ids, topic, difficulty) -> set: raise NotImplementedError
    def mark(self, player_ids, topic, difficulty, question_id) -> None: raise NotImplementedError
    def last_served(self, player_ids, topic, difficulty) -> dict: raise NotImplementedError


def _keys(kind: str, player_ids, topic: str, difficulty: str) -> list[str]:
    return [f"{kind}:{player}:{topic}:{difficulty}" for player in player_ids]


class MemorySeenStore(SeenStore):
    """History in this process only: for development and tests (and the default when no Redis is configured)."""

    def __init__(self, ttl_seconds: int = 30 * 24 * 3600, clock=time.time):
        self.ttl, self.clock = ttl_seconds, clock
        self._data: dict[str, dict] = {}              # key -> {question id: time served}
        self._expires: dict[str, float] = {}

    def _live(self, key: str) -> dict:
        if key in self._data and self._expires[key] <= self.clock():
            del self._data[key], self._expires[key]
        return self._data.get(key, {})

    def seen(self, player_ids, topic, difficulty) -> set:
        found = set()
        for key in _keys("seen", player_ids, topic, difficulty):
            found |= set(self._live(key))
        return found

    def mark(self, player_ids, topic, difficulty, question_id) -> None:
        now = self.clock()
        for key in _keys("seen", player_ids, topic, difficulty):
            self._live(key)
            self._data.setdefault(key, {})[str(question_id)] = now
            self._expires[key] = now + self.ttl

    def last_served(self, player_ids, topic, difficulty) -> dict:
        latest: dict = {}
        for key in _keys("seen", player_ids, topic, difficulty):
            for question_id, when in self._live(key).items():
                latest[question_id] = max(latest.get(question_id, 0.0), when)
        return latest


class RedisSeenStore(SeenStore):
    """History in Redis. `client` is a redis.Redis created with decode_responses=True (or anything with the same calls)."""

    def __init__(self, client, ttl_seconds: int = 30 * 24 * 3600, clock=time.time):
        self.client, self.ttl, self.clock = client, ttl_seconds, clock

    @classmethod
    def from_url(cls, url: str, ttl_seconds: int = 30 * 24 * 3600) -> "RedisSeenStore":
        import redis
        return cls(redis.Redis.from_url(url, decode_responses=True), ttl_seconds)

    def seen(self, player_ids, topic, difficulty) -> set:
        keys = _keys("seen", player_ids, topic, difficulty)
        if not keys:
            return set()
        return {str(x) for x in self.client.sunion(keys)}

    def mark(self, player_ids, topic, difficulty, question_id) -> None:
        now = self.clock()
        pipe = self.client.pipeline()
        for seen_key, served_key in zip(_keys("seen", player_ids, topic, difficulty), _keys("served", player_ids, topic, difficulty)):
            pipe.sadd(seen_key, str(question_id))
            pipe.expire(seen_key, self.ttl)
            pipe.zadd(served_key, {str(question_id): now})
            pipe.expire(served_key, self.ttl)
        pipe.execute()

    def last_served(self, player_ids, topic, difficulty) -> dict:
        latest: dict = {}
        for key in _keys("served", player_ids, topic, difficulty):
            for question_id, when in self.client.zrange(key, 0, -1, withscores=True):
                latest[str(question_id)] = max(latest.get(str(question_id), 0.0), float(when))
        return latest
