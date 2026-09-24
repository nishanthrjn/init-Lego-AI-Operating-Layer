"""Offline constructor injection. Real provider calls require governed composition."""

import asyncio
from dataclasses import dataclass

from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    ModelId,
    ProviderId,
)
from legoai.reference.model_fake import FixedModel


@dataclass(frozen=True)
class TextAssistant:
    model: ModelPort

    async def answer(self, question: str) -> str:
        result = await self.model.chat(
            ChatRequest((ChatMessage(ChatRole.USER, question),))
        )
        return result.content


async def main() -> None:
    model = FixedModel(
        ChatResult(
            "Ports keep application logic independent of providers.",
            ModelId("fixture"),
            ProviderId("offline"),
            None,
        )
    )
    print(await TextAssistant(model).answer("Why use ports?"))


if __name__ == "__main__":
    asyncio.run(main())
