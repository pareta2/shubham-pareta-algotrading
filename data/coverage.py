"""
data/coverage.py
----------------
Pure date-range maths, nothing else.  Used to answer ONE question:

    "I already have these date ranges.  The user wants this range.
     Which parts are still missing?"

A range is a pair of dates (start, end) - both inclusive.
Example:
    have    = [(2024-01-01, 2024-03-31), (2024-06-01, 2024-09-30)]
    want    = (2024-01-01, 2024-12-31)
    missing = [(2024-04-01, 2024-05-31), (2024-10-01, 2024-12-31)]
"""

from datetime import date, timedelta
from typing import List, Tuple

Range = Tuple[date, date]
ONE_DAY = timedelta(days=1)


def merge_ranges(ranges: List[Range]) -> List[Range]:
    """Sort and join ranges that overlap or touch.  [(1,5),(6,9),(20,25)] -> [(1,9),(20,25)]"""
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + ONE_DAY:            # overlapping or adjacent
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def missing_ranges(have: List[Range], want: Range) -> List[Range]:
    """The parts of `want` that are not inside any range in `have`."""
    want_start, want_end = want
    gaps = []
    cursor = want_start
    for start, end in merge_ranges(have):
        if end < cursor:
            continue                                # entirely before what we need
        if start > want_end:
            break                                   # entirely after what we need
        if start > cursor:
            gaps.append((cursor, min(start - ONE_DAY, want_end)))
        cursor = max(cursor, end + ONE_DAY)
        if cursor > want_end:
            break
    if cursor <= want_end:
        gaps.append((cursor, want_end))
    return gaps


def days_to_ranges(days: List[date]) -> List[Range]:
    """Group individual days into consecutive ranges.  [1,2,3,7,8] -> [(1,3),(7,8)]"""
    return merge_ranges([(d, d) for d in days])


def split_range(start: date, end: date, max_days: int) -> List[Range]:
    """Cut one long range into pieces no longer than max_days each."""
    pieces = []
    while start <= end:
        piece_end = min(start + timedelta(days=max_days - 1), end)
        pieces.append((start, piece_end))
        start = piece_end + ONE_DAY
    return pieces
