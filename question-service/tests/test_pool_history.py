"""Checks for the per-player history stores (in memory, and Redis through a small fake of the calls it makes)."""

from pool.history import MemorySeenStore, RedisSeenStore
from tests.pool_helpers import Counter


class FakeRedis:
    """Just the Redis commands RedisSeenStore uses; it records them so the tests can see keys and expiry times."""

    def __init__(self):
        self.sets, self.zsets, self.ttls, self.commands = {}, {}, {}, []

    def sunion(self, keys):
        self.commands.append(("sunion", tuple(keys)))
        out = set()
        for key in keys:
            out |= self.sets.get(key, set())
        return out

    def zrange(self, key, start, stop, withscores=False):
        self.commands.append(("zrange", key))
        return sorted(self.zsets.get(key, {}).items(), key=lambda kv: kv[1])

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis):
        self.redis, self.queue = redis, []

    def sadd(self, key, member):
        self.queue.append(("sadd", key, member))

    def zadd(self, key, mapping):
        self.queue.append(("zadd", key, mapping))

    def expire(self, key, seconds):
        self.queue.append(("expire", key, seconds))

    def execute(self):
        for name, key, argument in self.queue:
            if name == "sadd":
                self.redis.sets.setdefault(key, set()).add(argument)
            elif name == "zadd":
                self.redis.zsets.setdefault(key, {}).update(argument)
            else:
                self.redis.ttls[key] = argument
        self.redis.commands.append(("execute", len(self.queue)))
        self.queue = []


def stores():
    clock = Counter()
    return [MemorySeenStore(ttl_seconds=100, clock=clock), RedisSeenStore(FakeRedis(), ttl_seconds=100, clock=clock)]


def test_nothing_is_seen_at_first():
    for store in stores():
        assert store.seen(["p1"], "arrays", "easy") == set() and store.last_served(["p1"], "arrays", "easy") == {}
        assert store.seen([], "arrays", "easy") == set()


def test_a_marked_question_is_seen_by_exactly_those_players_in_exactly_that_bucket():
    for store in stores():
        store.mark(["p1", "p2"], "arrays", "easy", 7)
        assert store.seen(["p1"], "arrays", "easy") == {"7"} and store.seen(["p2"], "arrays", "easy") == {"7"}
        assert store.seen(["p3"], "arrays", "easy") == set()
        assert store.seen(["p1"], "arrays", "hard") == set() and store.seen(["p1"], "strings", "easy") == set()


def test_a_lobby_sees_everything_any_of_its_players_has_seen():
    for store in stores():
        store.mark(["a"], "arrays", "easy", 1)
        store.mark(["b"], "arrays", "easy", 2)
        assert store.seen(["a", "b"], "arrays", "easy") == {"1", "2"} and store.seen(["a", "c"], "arrays", "easy") == {"1"}


def test_the_time_a_question_was_served_is_the_latest_time_any_player_got_it():
    for store in stores():
        store.mark(["a"], "arrays", "easy", 1)      # time 1 (memory) / 1 (redis)
        store.mark(["b"], "arrays", "easy", 2)
        store.mark(["b"], "arrays", "easy", 1)      # b gets question 1 later than a did
        served = store.last_served(["a", "b"], "arrays", "easy")
        assert set(served) == {"1", "2"} and served["1"] > served["2"] > 0
        assert store.last_served(["a"], "arrays", "easy").keys() == {"1"}


def test_marking_the_same_question_twice_keeps_one_entry():
    for store in stores():
        store.mark(["a"], "arrays", "easy", 5)
        store.mark(["a"], "arrays", "easy", 5)
        assert store.seen(["a"], "arrays", "easy") == {"5"}


def test_memory_history_expires_after_the_ttl_and_a_new_mark_renews_it():
    now = [0.0]
    store = MemorySeenStore(ttl_seconds=100, clock=lambda: now[0])
    store.mark(["a"], "arrays", "easy", 1)
    now[0] = 99
    assert store.seen(["a"], "arrays", "easy") == {"1"}
    store.mark(["a"], "arrays", "easy", 2)                 # renews the whole key
    now[0] = 150
    assert store.seen(["a"], "arrays", "easy") == {"1", "2"}
    now[0] = 199.5
    assert store.seen(["a"], "arrays", "easy") == set() and store.last_served(["a"], "arrays", "easy") == {}


def test_redis_keys_ttl_and_scores_follow_the_documented_layout():
    redis = FakeRedis()
    store = RedisSeenStore(redis, ttl_seconds=3600, clock=lambda: 1234.5)
    store.mark(["p1", "p2"], "arrays", "easy", 42)
    assert redis.sets == {"seen:p1:arrays:easy": {"42"}, "seen:p2:arrays:easy": {"42"}}
    assert redis.zsets == {"served:p1:arrays:easy": {"42": 1234.5}, "served:p2:arrays:easy": {"42": 1234.5}}
    assert redis.ttls == {"seen:p1:arrays:easy": 3600, "seen:p2:arrays:easy": 3600, "served:p1:arrays:easy": 3600, "served:p2:arrays:easy": 3600}


def test_a_lobby_is_written_in_one_round_trip_and_read_with_one_union():
    redis = FakeRedis()
    store = RedisSeenStore(redis)
    store.mark(["a", "b", "c"], "graphs", "hard", 9)
    assert [c for c in redis.commands if c[0] == "execute"] == [("execute", 12)]
    store.seen(["a", "b", "c"], "graphs", "hard")
    assert redis.commands[-1] == ("sunion", ("seen:a:graphs:hard", "seen:b:graphs:hard", "seen:c:graphs:hard"))


def test_redis_ids_come_back_as_text_even_if_the_client_returns_numbers():
    redis = FakeRedis()
    redis.sets["seen:a:arrays:easy"] = {1, 2}
    assert RedisSeenStore(redis).seen(["a"], "arrays", "easy") == {"1", "2"}
