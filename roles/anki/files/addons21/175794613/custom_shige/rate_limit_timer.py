import time

class RateLimitTimer:
    def __init__(self):
        self.timers = {}

    def limit(self, key, sec):
        if key not in self.timers:
            self.timers[key] = {
                'seconds': sec,
                'last_sync': time.time()
            }
            return False

        current_time = time.time()
        timer = self.timers[key]

        if current_time - timer['last_sync'] < timer['seconds']:
            return True

        timer['last_sync'] = current_time
        return False

rate_limit = RateLimitTimer()

# print(rate_limiter.limit("example", 5))
# print(rate_limiter.limit("example", 5))
# time.sleep(6)
# print(rate_limiter.limit("example", 5))