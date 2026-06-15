"""Channel abstraction. Normalizes any platform into a unified message shape,
mirroring OpenClaw's channel-adapter pattern (Baileys/grammY -> internal format).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class InboundMessage:
    channel: str
    sender: str
    text: str
    is_group: bool = False
    meta: dict = field(default_factory=dict)

    def session_key(self) -> str:
        # FIX(OpenClaw): collapse personal DMs into one "main" session; isolate groups.
        return "main" if not self.is_group else f"{self.channel}:{self.sender}"


@dataclass
class OutboundMessage:
    text: str
    attachments: list[str] = field(default_factory=list)


class Channel(ABC):
    name: str = "base"

    @abstractmethod
    async def receive(self) -> InboundMessage: ...

    @abstractmethod
    async def send(self, to: str, message: OutboundMessage) -> None: ...


class CLIChannel(Channel):
    """A trivial local channel so the gateway is runnable without any network bind."""

    name = "cli"

    async def receive(self) -> InboundMessage:
        text = input("you › ")
        return InboundMessage(channel=self.name, sender="local", text=text)

    async def send(self, to: str, message: OutboundMessage) -> None:
        print(f"edith › {message.text}")
