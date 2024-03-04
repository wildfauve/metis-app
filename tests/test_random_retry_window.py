import pytest

from metis_app import chronos, random_retry_window

def test_is_short_of_the_window():
    window_width = 60*60
    now = chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])
    expiry_time = now + (60*60*3)  # 3 hours to expiry
    window_end = expiry_time - (60*60)

    result = random_retry_window.in_window(width=window_width, end=window_end, at=now)

    assert result == False

def test_in_window_with_limited_chance_of_retry():
    window_width = 60*60
    now = chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])
    expiry_time = now + (60*60*2)  # 2 hours to expiry
    window_end = expiry_time - (60*60)

    chances = [in_window(window_width, window_end, now) for i in range(50)]

    assert sum(1 for x in chances if x == False) > sum(1 for x in chances if x == True)


def test_in_window_with_high_chance_of_retry():
    window_width = 60*60
    now = int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]))
    expiry_time = now + (60*60) + 20  # 1 hour 20 sec to expiry
    window_end = expiry_time - (60*60)

    chances = [in_window(window_width, window_end, now) for i in range(50)]

    assert sum(1 for x in chances if x == True) > sum(1 for x in chances if x == False)


def test_must_retry_at_end_of_window():
    window_width = 60*60
    now = int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]))
    expiry_time = now + (60*60)  # 0 sec to expiry
    window_end = expiry_time - (60*60)

    chances = [in_window(window_width, window_end, now) for i in range(50)]

    assert all(chances) == True

def test_must_retry_within_theshold():
    window_width = 60*60
    now = int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]))
    expiry_time = now + (60*60) + 10  # 10 seconds until end of window (which is the threshold)
    window_end = expiry_time - (60*60)

    chances = [in_window(window_width, window_end, now) for i in range(50)]

    assert all(chances) == True

def test_is_left_of_window():
    window_width = 60*60
    now = int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]))
    expiry_time = now + (60*60*2)  # 3600 seconds until end of window
    window_end = expiry_time - (60*60)

    chances = [left_of_window(window_width, window_end, now) for i in range(50)]

    assert sum(1 for x in chances if x == True) > sum(1 for x in chances if x == False)


def in_window(window_width, window_end, window_at):
    return random_retry_window.in_window(width=window_width, end=window_end, at=window_at)

def left_of_window(window_width, window_end, window_at):
    return random_retry_window.left_of_window(width=window_width, end=window_end, at=window_at)
