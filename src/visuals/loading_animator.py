import itertools
import sys
import threading
import time


class LoadingDotsAnimator:
    def __init__(self, prefix: str = "", interval: float = 0.3):
        self.prefix = prefix
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._animate)
        self._dot_cycle = itertools.cycle(["", ".", "..", "..."])

    def _animate(self):
        while not self._stop_event.is_set():
            dots = next(self._dot_cycle)
            sys.stdout.write(f"\r{self.prefix}{dots}   ")
            sys.stdout.flush()
            time.sleep(self.interval)

    def is_stop_set(self):
        return self._stop_event.is_set()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate)
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
