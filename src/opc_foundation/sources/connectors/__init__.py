from .manual_url import ManualUrlConnector
from .hacker_news import HackerNewsConnector
from .github_issues import GitHubIssuesConnector
from .rss import RssConnector

# Canonical public aliases (matches API docs examples)
ManualURLConnector = ManualUrlConnector
HackerNewsConnector = HackerNewsConnector
GitHubIssuesConnector = GitHubIssuesConnector
RSSConnector = RssConnector

__all__ = [
    "ManualUrlConnector",
    "ManualURLConnector",
    "HackerNewsConnector",
    "GitHubIssuesConnector",
    "RssConnector",
    "RSSConnector",
]