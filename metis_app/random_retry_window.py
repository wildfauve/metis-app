import random

"""
Adds randomness to any retry concept, allowing competing processes to not (probably) compete for executing
a retry flow which updates shared state.

Used for the token expiry assessment, allowing several competing token gettings to:
1. Obtain a new token before it expires (end).
2. Apply a shrinking threshold to that end (width).
3. Assert a position in or out of the window (at)

Example (using times, rather than their Unix time values):
a. A token expiries at 12:00:00
b. The refresh of the token should occur before (or at) 11:00:00
c. The random refresh window started an hour before 11:00:00
d. Its now 10:05:00

> new.(00:60:00).in_window?(end: 11:00:00, at: 10:05:00)
=> possibly true
The at is in the window, therefore determine_in_window_chance(end, at) is called.
This picks a random number between 1 second .. 55 minutes (end - at)
If the random seconds are within the threshold for retry (THRESHOLD = 10 seconds) then the its in the window.
While its random that at is in the window, its approaches certainty the closer we get to the at, until
its completely certain (the at_right_end_of_window?(end, at) function)
"""

threshold = 10

def in_window(width, end, at):
    if not_in_window(width, end, at):
        return False
    if at_right_end_of_window(width, end, at):
        return True
    return determine_in_window_chance(width, end, at)

# This is the negative of in_window
def left_of_window(width, end, at):
    return not in_window(width=width, end=end, at=at)

def not_in_window(width, end, at):
    return (end - width) > at

def at_right_end_of_window(width, end, at):
    return ((end - at) == 0) or ((end - at) < threshold)

def determine_in_window_chance(width, end, at):
    chance = random.randint(1, (end - at))
    return (width % chance) < threshold
