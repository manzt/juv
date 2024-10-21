from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Literal


@dataclass
class Version: ...


@dataclass
class Info: ...


@dataclass
class Init:
    file: Path | None = None
    extra: list[str] = field(default_factory=list)
    kind: ClassVar[Literal["init"]] = "init"


@dataclass
class Add:
    file: Path
    packages: list[str]
    kind: ClassVar[Literal["add"]] = "add"


@dataclass
class Lab:
    file: Path
    version: str | None = None
    kind: ClassVar[Literal["lab"]] = "lab"


@dataclass
class Notebook:
    file: Path
    version: str | None = None
    kind: ClassVar[Literal["notebook"]] = "notebook"


@dataclass
class NbClassic:
    file: Path
    version: str | None = None
    kind: ClassVar[Literal["nbclassic"]] = "nbclassic"


Command = Init | Add | Lab | Notebook | NbClassic | Version | Info
