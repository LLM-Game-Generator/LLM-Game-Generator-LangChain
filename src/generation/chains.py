from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from typing import List

from src.generation.model_factory import get_langchain_model
from src.generation.arcade_tools import ARCADE_LANGCHAIN_TOOLS
from src.prompts.code_generation_prompts import (
    PROGRAMMER_PROMPT_TEMPLATE,
    COMMON_DEVELOPER_INSTRUCTION,
    PLAN_REVIEW_PROMPT
)
from src.prompts.design_prompts import CEO_PROMPT, CPO_PROMPT, CPO_REVIEW_PROMPT
from src.prompts.testing_prompts import FIXER_PROMPT, LOGIC_REVIEW_PROMPT, LOGIC_FIXER_PROMPT


class FileSkeleton(BaseModel):
    filename: str = Field(description="The name of the file (e.g., 'game.py')")
    purpose: str = Field(description="Brief explanation of the file's role")
    skeleton_code: str = Field(description="Python skeleton code with class/method definitions and docstrings")


class TechnicalPlan(BaseModel):
    architecture: str = Field(description="Overview of the system architecture")
    files: List[FileSkeleton] = Field(description="List of files to generate")
    constraints: List[str] = Field(description="Critical technical constraints (e.g., 'Check NoneType')")


class ArcadeAgentChain:
    def __init__(self, provider="openai", model=None, temperature=0.7):
        self.llm = get_langchain_model(provider, model, temperature)
        self.json_parser = JsonOutputParser(pydantic_object=TechnicalPlan)

    # --- Phase 1: Design (CEO/CPO) ---
    def get_ceo_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", CEO_PROMPT),
            ("user", "User Idea: {input}\n\nProvide a high-level analysis.")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_cpo_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", CPO_PROMPT),
            ("user", "User Idea: {idea}\nCEO Analysis: {analysis}\nFeedback: {feedback}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_reviewer_chain(self):
        """
        This was missing and causing the AttributeError.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", CPO_REVIEW_PROMPT),
            ("user", "Current GDD:\n{gdd}\n\nProvide feedback to improve this design.")
        ])
        return prompt | self.llm | StrOutputParser()

    # --- Phase 2: Production (Architect & Programmer) ---
    def get_architect_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Game Architect specializing in Arcade 2.6.x."),
            ("user", "GDD:\n{gdd}\nAssets:\n{assets}\n\nTask: Plan the game architecture. \n{format_instructions}")
        ])
        return prompt | self.llm | self.json_parser

    def get_plan_reviewer_chain(self):
        """
        Plan reviewer chain to validate the architecture plan against Arcade 2.x API and Grid safety.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", PLAN_REVIEW_PROMPT),
            ("user", "Architecture Plan:\n{plan}\n\nAnalyze for API correctness and Grid safety.")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_programmer_chain(self):
        """
        整合了 PROGRAMMER_PROMPT_TEMPLATE 與 COMMON_DEVELOPER_INSTRUCTION。
        """
        llm_with_tools = self.llm.bind_tools(ARCADE_LANGCHAIN_TOOLS)

        combined_system = f"{PROGRAMMER_PROMPT_TEMPLATE}\n\n{COMMON_DEVELOPER_INSTRUCTION}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", combined_system),
            ("user",
             "Architecture Context:\n{architecture_plan}\n\n"
             "Review Feedback:\n{review_feedback}\n\n"
             "Constraints:\n{constraints}\n\n"
             "TASK: Implement the FULL game logic in 'game.py'.\n"
             "Output ONLY the code block.")
        ])
        return prompt | llm_with_tools

    # --- Phase 3: Testing & Fixing ---
    def get_syntax_fixer_chain(self):
        """對標 generator-core: 修復 Runtime/Syntax 錯誤"""
        # 整合 COMMON 指令確保修復時不會又引入 3.0 語法
        combined_prompt = f"{FIXER_PROMPT}\n\n{COMMON_DEVELOPER_INSTRUCTION}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", combined_prompt),
            ("user", "【BROKEN CODE】:\n{code}\n\n【ERROR MESSAGE】:\n{error}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_reviewer_chain(self):
        """對標 generator-core: 靜態檢查 API 規範與 NoneType 安全"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", LOGIC_REVIEW_PROMPT),
            ("user", "【CODE】:\n{code}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_fixer_chain(self):
        """對標 generator-core: 修正 Reviewer 發現的邏輯問題"""
        combined_prompt = f"{LOGIC_FIXER_PROMPT}\n\n{COMMON_DEVELOPER_INSTRUCTION}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", combined_prompt),
            ("user", "【Error Messages】:\n{error}\n\n【CODE】:\n{code}")
        ])
        return prompt | self.llm | StrOutputParser()