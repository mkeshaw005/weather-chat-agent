from __future__ import annotations

import asyncio
from typing import Annotated, Optional, Tuple, List

from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions import kernel_function, KernelArguments

from .config import get_settings
from .repository import SQLiteConversationRepository, ConversationRepository, Message


class TravelWeather:
    @kernel_function(
        description="Takes a city and a month and returns the average temperature for that month.",
        name="travel_weather",
    )
    async def weather(
        self,
        city: Annotated[str, "The city for which to get the average temperature."],
        month: Annotated[str, "The month for which to get the average temperature."],
    ) -> str:
        return f"The average temperature in {city} in {month} is 75 degrees."


class ChatService:
    """Singleton-style chat service that initializes the SK agent once and reuses it."""

    _instance: Optional["ChatService"] = None

    def __init__(self) -> None:
        settings = get_settings()

        service = AzureChatCompletion(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment_name=settings.azure_openai_chat_deployment_name,
        )
        prompt_settings = OpenAIChatPromptExecutionSettings()

        self._agent = ChatCompletionAgent(
            service=service,
            name="Frederick",
            instructions=(
                "You are a travel weather chat bot named Frederick. Help users find the average "
                "temperature in a given city and month."
            ),
            plugins=[TravelWeather()],
            arguments=KernelArguments(prompt_settings),
        )
        # Repo and config
        self._repo: ConversationRepository = SQLiteConversationRepository(settings.chat_db_path)
        self._max_history = settings.max_history_turns

    @classmethod
    def instance(cls) -> "ChatService":
        if cls._instance is None:
            cls._instance = ChatService()
        return cls._instance

    def repository(self) -> ConversationRepository:
        return self._repo

    async def ask(self, question: str, session_id: Optional[str] = None) -> Tuple[str, str]:
        # Ensure we have a session
        if not session_id or not self._repo.session_exists(session_id):
            session_id = self._repo.create_session()
            # Use the first question as a simple title
            title = question.strip()[:60]
            self._repo.update_session_title_if_empty(session_id, title)

        # Load recent history and build a compact transcript
        history: List[Message] = self._repo.get_messages(session_id, limit=self._max_history * 2)
        transcript_lines: List[str] = []
        if history:
            for m in history:
                role_cap = "System" if m.role == "system" else ("User" if m.role == "user" else "Assistant")
                transcript_lines.append(f"{role_cap}: {m.content}")
        # Append current user question
        transcript_lines.append(f"User: {question}")
        transcript_lines.append("Assistant:")
        prompt = "\n".join(transcript_lines)

        # Ask the agent with context
        response = await self._agent.get_response(prompt)
        content = getattr(response, "content", None)
        if not isinstance(content, str):
            try:
                content = str(content if content is not None else response)
            except Exception:
                content = ""

        # Persist this turn
        self._repo.append_message(session_id, "user", question)
        self._repo.append_message(session_id, "assistant", content)

        return content, session_id


async def warmup() -> None:
    """Optionally send a trivial request to ensure lazy resources are ready."""
    # No-op by default; could be used to validate configuration/environment.
    await asyncio.sleep(0)
