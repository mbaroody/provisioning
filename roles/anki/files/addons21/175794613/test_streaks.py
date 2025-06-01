class TestClass:
    def __init__(self):
        self.config = {"achievement": True}

    def achievement(self, streak):
        def is_repeating_number(n):
            s = str(n)
            if len(s) >= 3:
                return all(c == s[0] for c in s)
            return False

        if (self.config["achievement"] == True
            and (
            streak % 100 == 0
            or streak % 365 == 0
            or streak in [7, 30, 60, 90]
            or is_repeating_number(streak)
            )
            ):
            return True
        return False

test_instance = TestClass()
for i in range(1, 10001):
    if test_instance.achievement(i):
        print(i)