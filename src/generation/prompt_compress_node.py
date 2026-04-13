from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.generation.model_factory import get_langchain_model


class LocalPromptCompressor:
    def __init__(self, model_name="llama3.1:latest"):
        """
        Use local models for compressing the prompts
        """
        self.local_llm = get_langchain_model(provider="ollama", model_name=model_name, temperature=0.1)

    def compress_errors(self, error_history: list[str] | str) -> str:
        """
        To compress the history errors.
        """
        # Flatten to string if given list
        if isinstance(error_history, list):
            error_history = "\n---\n".join(error_history)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
               You are a python error summarization assistant.\n\n
               Your task is to take verbose Python error messages and summarize them into concise, actionable insights that retain all critical information for debugging.\n\n
               Make sure that you do NOT lose any important technical details, constraints, or instructions in the summarization process.\n\n
               """),
            ("user",
             "Summarize the following Python error message into a concise format suitable for debugging:\n\n{errors}")
        ])

        chain = prompt | self.local_llm | StrOutputParser()

        return chain.invoke({"errors": error_history})

    def compress_gdd(self, gdd_content: str) -> str:
        """
        To compress the gdd into a concise format suitable for prompt injection.
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
               You are a GDD summarization assistant.\n\n
               Your goal is to summarize the given Game Design Document (GDD) into a concise format that retains all critical information, constraints, and instructions necessary for game development.\n\n
               Make sure that you do NOT lose any important technical details, constraints, and instructions in the summarization process.\n\n
               """),
            ("user", "Summarize the following gdd into a concise format suitable for prompt injection:\n\n{gdd}")
        ])

        chain = prompt | self.local_llm | StrOutputParser()
        return chain.invoke({"gdd": gdd_content})