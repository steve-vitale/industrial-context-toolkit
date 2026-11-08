"""Observe one dispatched input completing; no typing, retry, focus or commit operation."""
import time


def wait_for_exact(read, expected, record, timeout=3.0, clock=time.monotonic, sleep=time.sleep):
    start = clock()
    while True:
        value = read(); elapsed = clock() - start
        record(dict(elapsed=elapsed, text=value))
        if value == expected: return True
        if elapsed >= timeout: return False
        sleep(min(.05, timeout - elapsed))
