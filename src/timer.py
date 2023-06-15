class Timer:
    current_time = 0

    def update_time(self, interval):
        self.current_time += interval

    def reset(self):
        self.current_time = 0