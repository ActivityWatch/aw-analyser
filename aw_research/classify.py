from typing import List, Dict, Any, Set
from urllib.parse import urlparse
from collections import Counter
from datetime import timedelta
from pprint import pprint
import re


from aw_core.models import Event
from aw_client import ActivityWatchClient

import pydash


classes = {
    r'[Aa]ctivity[Ww]atch|aw-.*': 'ActivityWatch',
    r'[Cc]rypto[Tt]ax': 'CryptoTax',
    r'[Ss]potify|[Ss]oundcloud': 'Music',
    r'[Yy]ouTube|[Vv]imeo|[Pp]lex': 'Video',
    r'[Pp]rogramming|[Gg]it[Hh]ub|[Pp]ython|[Mm]atplotlib|localhost': "Programming",
    r'[Ss]chool|LTH|FAFF25|FMAN20|exam|[0-9]{4}_[0-9]{2}_[0-9]{2}\.pdf': "School",
    r'(Khan Academy)|(Wolfram\|Alpha)': "Maths",
    r'Messenger|(messaged you)': "Communication",
    r'Gmail': "Communication",
    r'Google Search': "Searching",
    r'[Ff]acebook|[Rr]eddit|[Tt]witter': "Social Media",
    r'NCBI|PubMed': "Research",
    r'Google Docs|Standard Notes': "Writing",
    r'Ebay|Amazon|DECIEM|Huel|H\&M|Topman': "Shopping",
    r'/(media-)?annex/': "Archiving",
}

parent_categories = {
    'Music': ('Entertainment',),
    'Video': ('Entertainment',),
    'ActivityWatch': ('Programming',),
    'CryptoTax': ('Programming',),
    'Programming': ('Work',),
    'School': ('Work',),
}


def get_parent_categories(cat: str) -> set:
    # Recursive
    if cat in parent_categories:
        cats = set(parent_categories[cat])
        for parent in tuple(cats):
            cats |= get_parent_categories(parent)
        return cats
    return set()


def classify(events):
    for event in events:
        event.data["categories"] = set()

    for re_pattern, cat in classes.items():
        r = re.compile(re_pattern)
        for event in events:
            for attr in ["title", "app"]:
                if cat not in event.data["categories"] and \
                   r.findall(event.data[attr]):
                    event.data["categories"].add(cat)
                    event.data["categories"] |= get_parent_categories(cat)

    for e in events:
        if not e.data["categories"]:
            e.data["categories"].add("Uncategorized")

    return events


def _hostname(url):
    return urlparse(url).netloc


def group_by_url_hostname(events):
    return pydash.group_by(events, lambda e: _hostname(e.data["url"]))


def duration_of_groups(groups: Dict[Any, List[Event]]):
    groups_eventdurations = pydash.map_values(
        groups, lambda g: pydash.map_(g, lambda e: e.duration.total_seconds()))  # type: Dict[Any, float]

    return pydash.map_values(
        groups_eventdurations, lambda g: pydash.reduce_(g, lambda total, d: total + d))


def time_per_category(events):
    # Events need to be categorized
    c = Counter()
    for e in events:
        cats = e.data["categories"]
        for cat in cats:
            c[cat] += e.duration.total_seconds()
    return c


def get_events(bid):
    return ActivityWatchClient("test", testing=True) \
        .get_events(bid, limit=-1)


def test_hostname():
    assert _hostname("http://activitywatch.net/") == "activitywatch.net"
    assert _hostname("https://github.com/") == "github.com"


def _print_unclassified(events, n=10):
    for i, e in enumerate(e for e in sorted(events, key=lambda e: -e.duration) if "Uncategorized" in e.data["categories"]):
        print(e.duration, e.data)
        if i > n:
            break


def _main():
    # events = get_events("aw-watcher-web-chrome")
    # groups = group_by_url_hostname(events)
    # duration_pairs = pydash.to_pairs(duration_of_groups(groups))
    # pprint(sorted(duration_pairs, key=lambda p: p[1]))

    # TODO: Use a query and filter AFK
    events = get_events("aw-watcher-window_erb-laptop2-arch")
    events = classify(events)
    # pprint([e.data["categories"] for e in classify(events)])
    for c, s in time_per_category(events).most_common():
        print("{}\t{}".format(timedelta(seconds=s), c))

    # _print_unclassified(events, 30)


if __name__ == "__main__":
    _main()
