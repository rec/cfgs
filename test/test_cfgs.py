import dataclasses as dc
from cfgs import Configs
from typing import List


def field(factory):
    return dc.field(default_factory=factory)


@dc.dataclass
class Audio(Configs):
    levels: List[float] = field(list)


@dc.dataclass
class DMX(Configs):
    channel: int = 0


@dc.dataclass
class Midi(Configs):
    channel: int = 0
    name: str = ''


@dc.dataclass
class Everything(Configs):
    audio: Audio = field(Audio)
    dmx: DMX = field(DMX)
    midi: Midi = field(Midi)


def test_simple():
    e = Everything()
    assert e.diff(e) == {}
    assert Everything().diff(e) == {}

    e.dmx.channel = 3
    assert e.diff(e) == {}
    assert Everything().diff(e) == {'dmx': {'channel': 3}}


def test_diff():
    e = Everything()
    e.audio.levels[:] = [1.0, 2.0]

    assert Everything().diff(e) == {'audio': {'levels': [1.0, 2.0]}}
    assert e.diff(Everything()) == {'audio': {'levels': []}}
