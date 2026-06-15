"""Channel abstraction. Normalizes any platform into one message shape, mirroring
OpenClaw's adapter pattern (Baileys/grammY -> internal format).
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
    group_id: str | None = None
    meta: dict = field(default_factory=dict)

    def session_key(self) -> str:
        # Collapse personal DMs into one "main" session; isolate each GROUP by its group
        # id (not the sender) so a whole group shares one workspace.
        if not self.is_group:
            return "main"
        return f"{self.channel}:{self.group_id or self.sender}"


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
        return InboundMessage(channel=self.name, sender="local", text=input("you › "))

    async def send(self, to: str, message: OutboundMessage) -> None:
        print(f"edith › {message.text}")
