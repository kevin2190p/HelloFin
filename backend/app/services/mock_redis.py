import json
import time
import asyncio

class MockRedis:
    """
    A simple in-memory mock of aioredis for development without a real Redis server.
    """
    def __init__(self):
        self.data = {}  # For HSET / GET / SET
        self.lists = {} # For LPUSH / LRANGE
        self.sets = {}  # For SADD / SREM / SISMEMBER
        self.timers = {} # For SETEX (expiry simulation)

    async def hset(self, name, key=None, value=None, mapping=None):
        if name not in self.data:
            self.data[name] = {}
        if mapping:
            self.data[name].update(mapping)
        else:
            self.data[name][key] = value
        return 1

    async def hget(self, name, key):
        return self.data.get(name, {}).get(key)

    async def set(self, name, value):
        self.data[name] = value
        return True

    async def get(self, name):
        return self.data.get(name)

    async def setex(self, name, time_sec, value):
        self.data[name] = value
        # We don't strictly enforce expiry in mock, but we could if needed
        return True

    async def sadd(self, name, value):
        if name not in self.sets:
            self.sets[name] = set()
        self.sets[name].add(str(value))
        return 1

    async def srem(self, name, value):
        if name in self.sets:
            self.sets[name].discard(str(value))
        return 1

    async def exists(self, name):
        return 1 if (name in self.data or name in self.lists or name in self.sets) else 0

    async def lpush(self, name, value):
        if name not in self.lists:
            self.lists[name] = []
        self.lists[name].insert(0, value)
        return len(self.lists[name])

    async def lrange(self, name, start, end):
        lst = self.lists.get(name, [])
        if end == -1:
            return lst[start:]
        return lst[start : end + 1]

    async def delete(self, name):
        self.data.pop(name, None)
        self.lists.pop(name, None)
        self.sets.pop(name, None)
        return 1

    async def close(self):
        pass

    async def ping(self):
        return True
