from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from typing import List

from src.generation.model_factory import get_langchain_model
from src.generation.arcade_tools import ARCADE_LANGCHAIN_TOOLS
from src.prompts.code_generation_prompts import (
    ARCHITECT_SYSTEM_PROMPT,
    PROGRAMMER_PROMPT_TEMPLATE,
    PLAN_REVIEW_PROMPT,
    FUZZER_GENERATION_PROMPT
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
        prompt = ChatPromptTemplate.from_messages([
            ("system", CPO_REVIEW_PROMPT),
            ("user", "Current GDD:\n{gdd}\n\n"
                     "Provide feedback to improve this design."
            )
        ])
        return prompt | self.llm | StrOutputParser()

    # --- Phase 2: Production (Architect & Programmer) ---
    def get_architect_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", ARCHITECT_SYSTEM_PROMPT),
            ("user", "GDD:\n{gdd}\n"
                     "Assets:\n{assets}\n\n"
                     "Task: Plan the game architecture. \n"
                     "{format_instructions}"
            )
        ])
        return prompt | self.llm | self.json_parser

    def get_architect_refinement_chain(self):
        """
        [NEW] Refines the Technical Plan based on Reviewer feedback.
        Matches the logic: 'Rewrite the Technical Implementation Plan by incorporating the feedback.'
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", ARCHITECT_SYSTEM_PROMPT),
            ("user",
             "Original Plan JSON:\n{original_plan}\n\n"
             "Reviewer Feedback:\n{feedback}\n\n"
             "TASK: Refine the architecture JSON to address the feedback.\n"
             "{format_instructions}")
        ])
        return prompt | self.llm | self.json_parser

    def get_plan_reviewer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", PLAN_REVIEW_PROMPT),
            ("user", "Architecture Plan:\n{plan}\n\n"
                     "Analyze for API correctness and Grid safety."
            )
        ])
        return prompt | self.llm | StrOutputParser()

    def get_programmer_chain(self):
        """
        Generates the code using RAG tools and specific Math Injection.
        """
        llm_with_tools = self.llm.bind_tools(ARCADE_LANGCHAIN_TOOLS)

        combined_system = f"{PROGRAMMER_PROMPT_TEMPLATE}"

        legacy_conventions = """
    ARCADE 2.x (LEGACY) MANDATORY CONVENTIONS:
    1. Drawing: Use 'draw_rectangle_filled' (center_x, center_y, width, height, color). 
       DO NOT use Arcade 3.0 'draw_rect_filled' or XYWH objects.
    2. Rendering: You MUST call 'arcade.start_render()' as the first line in 'on_draw'.
    3. Textures: The 'arcade.Texture(name, image)' constructor REQUIRES a unique name string as the first argument.
    4. Sprite Update: The 'update()' method for Sprites typically takes NO arguments. 
       Do NOT include 'delta_time' in Sprite.update unless manually passed.
    5. Grid Safety: Always verify 'if grid[r][c] is not None:' before accessing its attributes.
    """

        prompt = ChatPromptTemplate.from_messages([
            ("system", combined_system),
            ("user",
             "Architecture Context:\n{architecture_plan}\n\n"
             "Review Feedback:\n{review_feedback}\n\n"
             "Technical Constraints:\n{constraints}\n\n"
             f"RULES & HELPERS:\n{legacy_conventions}\n\n"
             "Math & Physics Formulas (MANDATORY):\n{math_context}\n\n"
             "TASK: Implement the FULL game logic in 'game.py'.\n"
             "Output ONLY the code block.")
        ])
        return prompt | llm_with_tools

    # --- Phase 3: Testing & Fixing ---
    def get_syntax_fixer_chain(self):
        combined_prompt = f"{FIXER_PROMPT}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", combined_prompt),
            ("user", "【BROKEN CODE】:\n{code}\n\n【ERROR MESSAGE】:\n{error}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_reviewer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", LOGIC_REVIEW_PROMPT),
            ("user", "【CODE】:\n{code}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_fixer_chain(self):
        combined_prompt = f"{LOGIC_FIXER_PROMPT}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", combined_prompt),
            ("user", "【Error Messages】:\n{error}\n\n【CODE】:\n{code}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_fuzzer_chain(self):
        """
        [NEW] Generates the Fuzzer Monkey Bot Logic snippet based on the GDD.
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a QA Automation Engineer specializing in Python Arcade 2.x."),
            ("user", FUZZER_GENERATION_PROMPT)
        ])
        return prompt | self.llm | StrOutputParser()