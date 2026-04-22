"""Utilidades comunes a todos los agentes."""
from __future__ import annotations

from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from ..llm import get_chat_model

T = TypeVar("T", bound=BaseModel)


def build_chain(
    system_prompt: str,
    output_model: type[T],
    llm: BaseChatModel | None = None,
    temperature: float = 0.4,
):
    """Cadena estándar: system prompt + input → output estructurado Pydantic."""
    llm = llm or get_chat_model(temperature=temperature)
    parser = PydanticOutputParser(pydantic_object=output_model)
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", "{input}\n\n{format_instructions}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())
    return prompt | llm | parser
