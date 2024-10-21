from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import typing
import re


@dataclass
class GithubAsset:
    user: str
    repo: str
    tag: str | None
    path: str

    @classmethod
    def try_from(cls, identifier: str) -> typing.Self | None:
        pattern = r"gh://(?P<user>[\w-]+)/(?P<repo>[\w-]+)(?:@(?P<tag>[\w.-]+))?/(?P<path>.*\.ipynb)"
        if match := re.match(pattern, identifier):
            user, repo, tag, path = match.groups()
            return cls(user, repo, tag, path)
        return None

    def url(self) -> str:
        return f"https://raw.githubusercontent.com/{self.user}/{self.repo}/{self.tag or 'main'}/{self.path}"


@dataclass
class RemoteSource:
    href: str


@dataclass
class StdinSource: ...


@dataclass
class LocalSource:
    path: Path


def resolve_source(src: str) -> RemoteSource | LocalSource | StdinSource | None:
    if src.startswith("http://") or src.startswith("https://"):
        return RemoteSource(src)

    if gh := GithubAsset.try_from(src):
        return RemoteSource(gh.url())

    if src == "-":
        return StdinSource()

    path = Path(src)
    if path.exists():
        return LocalSource(path)

    return None
