import json
import os
import re
import sys

from generation.asset_gen import generate_assets
from prompts.game_logic_cheat_sheet import PHYSICS_MATH_CHEAT_SHEET, GRID_MATH_CHEAT_SHEET, PLATFORMER_CHEAT_SHEET
from src.generation.core.game_state import GameState
from utils import clean_code_content, save_generated_files

def apply_deterministic_fix(original_code: str, start_line: int, end_line: int, replacement: str) -> str:
    """
    Replace the codes directly by:
    :param original_code: the original full codes
    :param start_line: starting line number
    :param end_line: ending line number
    :replacement: the replacement code
    :return the full fixed codes
    """

    # 1. slice the original code to a line by line list
    code_lines = original_code.split('\n')

    # 2. Clear the markdown marks
    clean_replacement = replacement.replace("```python=", "").replace("```python", "").replace("```", "").strip('\n')

    # 3. Dealing with the line number (starting from 1 to starting from 0)
    start_idx = start_line - 1
    end_idx = end_line

    # 4. combine the fixing codes
    new_code_lines = code_lines[:start_idx] + [clean_replacement] + code_lines[end_idx:]

    # 5. combine to str
    return '\n'.join(new_code_lines)


import json
import os
import re
import sys
from datetime import datetime  # [新增] 用於紀錄 Commit 的時間戳記

from generation.asset_gen import generate_assets
from prompts.game_logic_cheat_sheet import PHYSICS_MATH_CHEAT_SHEET, GRID_MATH_CHEAT_SHEET, PLATFORMER_CHEAT_SHEET
from src.generation.core.game_state import GameState
from utils import clean_code_content, save_generated_files


def apply_deterministic_fix(original_code: str, start_line: int, end_line: int, replacement: str) -> str:
    # 1. slice the original code to a line by line list
    code_lines = original_code.split('\n')
    # 2. Clear the markdown marks
    clean_replacement = replacement.replace("```python=", "").replace("```python", "").replace("```", "").strip('\n')
    # 3. Dealing with the line number (starting from 1 to starting from 0)
    start_idx = start_line - 1
    end_idx = end_line
    # 4. combine the fixing codes
    new_code_lines = code_lines[:start_idx] + [clean_replacement] + code_lines[end_idx:]
    # 5. combine to str
    return '\n'.join(new_code_lines)


def ceo_node(state: GameState, agents, log_callback):
    log_callback(f"[Design] CEO Analyzing idea: {state['user_input']}...")
    analysis = agents.get_ceo_chain().invoke({"input": state["user_input"]})
    return {"ceo_analysis": analysis, "design_iterations": 0, "design_feedback": "None"}


def cpo_node(state: GameState, agents, log_callback):
    log_callback(f"[Design] CPO Drafting GDD (Round {state['design_iterations'] + 1})...")
    gdd = agents.get_cpo_chain().invoke({
        "idea": state["user_input"],
        "analysis": state["ceo_analysis"],
        "feedback": state["design_feedback"]
    })
    return {"gdd": gdd}


def design_reviewer_node(state: GameState, agents, log_callback):
    log_callback("[Design] Reviewer critiquing GDD...")
    feedback = agents.get_reviewer_chain().invoke({"gdd": state["gdd"]})
    return {
        "design_feedback": feedback,
        "design_iterations": state["design_iterations"] + 1
    }


def asset_node(state: GameState, provider_name, log_callback):
    log_callback("[System] Generating Assets...")
    assets = generate_assets(gdd_context=state["gdd"], provider=provider_name)
    return {"assets_json": assets}


def architect_node(state: GameState, agents, log_callback):
    log_callback(f"[Architect] Planning system architecture (Round {state['plan_iterations'] + 1})...")

    if state['plan_iterations'] == 0:
        plan = agents.get_architect_chain().invoke({
            "gdd": state["gdd"],
            "assets": state["assets_json"],
            "format_instructions": agents.json_parser.get_format_instructions()
        })
    else:
        log_callback("[Architect] Refining plan based on feedback...")
        plan_str = json.dumps(state["architecture_plan"], indent=2)
        plan = agents.get_architect_refinement_chain().invoke({
            "original_plan": plan_str,
            "feedback": state["plan_feedback"],
            "format_instructions": agents.json_parser.get_format_instructions()
        })
    return {"architecture_plan": plan}


def plan_reviewer_node(state: GameState, agents, log_callback):
    log_callback("[Architect] Plan Review...")
    plan_str = json.dumps(state["architecture_plan"], indent=2)
    feedback = agents.get_plan_reviewer_chain().invoke({"plan": plan_str})
    return {
        "plan_feedback": feedback,
        "plan_iterations": state["plan_iterations"] + 1
    }


def programmer_node(state: GameState, agents, prompt_compress_agents, work_dir, log_callback):
    math_injection = ""
    gdd_lower = state["gdd"].lower()
    if any(k in gdd_lower for k in ["pool", "billiard", "physics", "ball", "shooter", "tank"]):
        log_callback("[System] Detected Physics/Top-Down Game. Injecting Vector Math...")
        math_injection = PHYSICS_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["grid", "2048", "tetris", "snake", "puzzle", "board"]):
        log_callback("[System] Detected Grid-Based Game. Injecting Grid Math...")
        math_injection = GRID_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["jump", "platform", "gravity", "flappy", "mario"]):
        log_callback("[System] Detected Platformer. Injecting Gravity Logic...")
        math_injection = PLATFORMER_CHEAT_SHEET

    log_callback("[Programmer] AI deciding on required templates...")
    needed_templates = []
    try:
        log_callback("[Programmer] Extracting core mechanics for template decision...")
        compressed_gdd = prompt_compress_agents.get_gdd_mechanics_extractor().invoke({"gdd": state["gdd"]})
        resp = agents.get_template_decision_chain().invoke({"gdd": compressed_gdd})

        match = re.search(r'\[.*?\]', resp, re.DOTALL)
        if match:
            parsed_list = json.loads(match.group(0))
            needed_templates = [t for t in parsed_list if t in ["menu.py", "camera.py", "asset_manager.py"]]
        if not needed_templates:
            needed_templates = ["asset_manager.py", "camera.py", "menu.py"]  # Fallback
    except Exception as e:
        log_callback(f"[Warning] Template decision failed, using defaults. Error: {e}")
        needed_templates = ["asset_manager.py", "camera.py", "menu.py"]

    log_callback(f"[Programmer] Selected templates: {needed_templates}")

    template_code_blocks = []
    guaranteed_imports = []
    template_instructions = ""

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    template_dir = os.path.join(root_dir, "src", "generation", "../template")

    for t_file in needed_templates:
        t_path = os.path.join(template_dir, t_file)
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                template_code_blocks.append([t_file, f.read()])

            if "asset_manager" in t_file:
                guaranteed_imports.append("from asset_manager import AssetManager")
                template_instructions += (
                    "- **Asset Loading (MANDATORY)**: NEVER use `arcade.load_texture`. ALWAYS use `AssetManager` like this:\n"
                    "  `self.texture = AssetManager.get_texture('player.png', fallback_color=arcade.color.RED, width=32, height=32)`\n"
                )
            elif "camera" in t_file:
                guaranteed_imports.append("from camera import FollowCamera")
                template_instructions += (
                    "- **Scrolling (MANDATORY)**: Use `FollowCamera` for scrolling levels. Usage:\n"
                    "  * Init: `self.camera = FollowCamera(SCREEN_WIDTH, SCREEN_HEIGHT, map_width, map_height)`\n"
                    "  * Draw: Call `self.camera.use()` before drawing world sprites. Call `self.ui_camera.use()` for HUD.\n"
                    "  * Update: Call `self.camera.update_to_target(self.player)` in `on_update`.\n"
                )
            elif "menu" in t_file:
                guaranteed_imports.append("from menu import PauseView")
                template_instructions += (
                    "- **Pause System (MANDATORY)**: DO NOT write `self.paused = True`. Instead, handle ESC key like this:\n"
                    "  `if key == arcade.key.ESCAPE: self.window.show_view(PauseView(self))`\n"
                )
        else:
            log_callback(f"[Warning] Template file not found: {t_path}")

    imports_str = "\n".join(guaranteed_imports)
    if template_instructions:
        template_injection_prompt = (
            "\n=======================================================\n"
            "🔥 CRITICAL: PRE-BUILT MODULES REQUIREMENT 🔥\n"
            "=======================================================\n"
            "I have already created the template files for you. You MUST use them in `game.py`!\n\n"
            "1. YOU MUST PUT THESE IMPORTS AT THE VERY TOP OF `game.py`:\n"
            "```python\n"
            f"{imports_str}\n"
            "```\n\n"
            "2. YOU MUST FOLLOW THESE IMPLEMENTATION RULES:\n"
            f"{template_instructions}\n"
            "Failure to use these classes will result in immediate system crash!\n"
            "=======================================================\n"
        )

    log_callback("[Programmer] Implementing game.py with RAG, Math & Templates...")
    complexity_constraints = (
        "1. Write verbose code with detailed comments.\n"
        "2. Implement at least 3 different enemy types or obstacles if applicable.\n"
        "3. Include a 'ParticleManager' class for visual effects.\n"
        "4. ABSOLUTELY NO ABBREVIATED CODE. WRITE EVERY LINE.\n"
        "5. Implement a proper Game Over view and Restart mechanic."
    )
    constraints = "\n".join(state["architecture_plan"].get('constraints', []))

    # [修改] 注入長期記憶 (core_guidelines)
    guidelines_str = "\n".join([f"- {g}" for g in state.get("core_guidelines", [])])
    memory_injection = f"\n[歷史避坑指南 (絕對遵守)]:\n{guidelines_str}\n" if guidelines_str else ""

    full_constraints = f"{constraints}\n\n{complexity_constraints}\n{memory_injection}"

    response = agents.get_programmer_chain().invoke({
        "architecture_plan": state["architecture_plan"],
        "review_feedback": state["plan_feedback"],
        "constraints": full_constraints,
        "math_context": math_injection
    })

    content = response.content if hasattr(response, 'content') else str(response)
    cleaned_code = clean_code_content(content)

    for imp in guaranteed_imports:
        if imp not in cleaned_code:
            log_callback(f"[Failsafe] LLM forgot to import '{imp}'. Auto-injecting...")
            if "import arcade" in cleaned_code:
                cleaned_code = cleaned_code.replace("import arcade", f"import arcade\n{imp}")
            else:
                cleaned_code = f"import arcade\n{imp}\n" + cleaned_code

    log_callback("[Test] Generating Fuzzer logic snippet...")
    fuzzer_response = agents.get_fuzzer_chain().invoke({"gdd": state["gdd"]})
    fuzzer_logic = fuzzer_response.content if hasattr(fuzzer_response, 'content') else str(fuzzer_response)
    cleaned_fuzzer_logic = clean_code_content(fuzzer_logic)

    project_files = {"game.py": cleaned_code, "fuzz_logic.py": cleaned_fuzzer_logic}
    for t_file, code in template_code_blocks:
        project_files[t_file] = code

    save_generated_files(project_files, work_dir)

    # [修改] 初始化第一筆 Git-like Commit
    initial_commit = {
        "version_id": f"v{len(state.get('commit_history', [])) + 1}",
        "author": "Programmer",
        "code": cleaned_code,
        "fuzzer_passed": False,
        "error_trace": None,
        "timestamp": str(datetime.now())
    }

    return {
        "current_code": cleaned_code,
        "project_files": project_files,
        "test_iterations": 0,
        "test_errors": [],
        "commit_history": state.get("commit_history", []) + [initial_commit],
        "consecutive_failures": 0,
        "is_valid": False
    }


def evaluator_node(state: GameState, agents, work_dir, log_callback):
    """
    Validates the code in order of absolute truth:
    1. Syntax -> 2. Fuzzer (Runtime) -> 3. Static Logic Review
    """
    log_callback(f"\n[Test] Starting validation round {state.get('test_iterations', 0) + 1}...")
    current_code = state["current_code"]
    main_file_path = os.path.join(work_dir, "game.py")
    lines_of_traceback_included = 10

    history = list(state.get("commit_history", []))

    # 用來封裝統一回傳錯誤邏輯的內部函式
    def return_error(error_message):
        if history:
            history[-1]["fuzzer_passed"] = False
            history[-1]["error_trace"] = error_message
        return {
            "test_errors": state.get("test_errors", []) + [error_message],
            "commit_history": history,
            "consecutive_failures": state.get("consecutive_failures", 0) + 1
        }

    # ==========================================
    # Stage A: Syntax Check
    # ==========================================
    log_callback("[Check] Running static syntax check...")
    try:
        compile(current_code, "game.py", 'exec')
        log_callback("[Check] Syntax validation passed.")
    except SyntaxError as e:
        error_msg = f"[SyntaxError] Line {e.lineno}: {e.msg}\n{e.text}"
        log_callback("[Check] Syntax error detected.")
        return return_error(error_msg)

    # ==========================================
    # Stage B: Runtime Test (Fuzzer)
    # ==========================================
    log_callback("[Test] Running fuzzer runtime tests...")
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        if root_dir not in sys.path:
            sys.path.append(root_dir)
        from src.testing.runner import run_fuzz_test

        success, error_msg = run_fuzz_test(main_file_path, duration=30)
        if not success:
            log_callback(f"[Test] Fuzzer Runtime Error: {error_msg}")
            return return_error(f"[RuntimeError] {error_msg}")
        else:
            log_callback("[Test] Fuzzer passed (No crashes for 30s).")

    except Exception as e:
        import traceback
        log_callback(f"[Error] Test runner exception: {str(e)}")
        short_error = traceback.format_exc().strip().split('\n')[-lines_of_traceback_included:]
        error_msg = f"[TestRunnerError]: {' '.join(short_error)}"
        return return_error(error_msg)

    # ==========================================
    # Stage C: Logic Review
    # ==========================================
    log_callback("[Review] Running strict API standard review...")
    review_result = agents.get_logic_reviewer_chain().invoke({"code": current_code})

    if "PASS" not in review_result:
        error_msg = f"[LogicError] {review_result}"
        log_callback(f"[Review] Logic/API Rule Violation: {review_result}")
        return return_error(error_msg)
    else:
        log_callback("[Review] Strict API validation passed.")

    log_callback("[Result] Code passed ALL validations successfully!")

    # 測試全數通過，紀錄到 Commit 中
    if history:
        history[-1]["fuzzer_passed"] = True
        history[-1]["error_trace"] = None

    return {
        "is_valid": True,
        "commit_history": history,
        "consecutive_failures": 0  # 成功則歸零
    }


def fixer_node(state: GameState, agents, prompt_compress_agents, work_dir, log_callback):
    """Memory Core: Fixes code based on historical error logs."""
    log_callback("[Fixer] Reading historical error logs and attempting fix...")
    latest_error = state["test_errors"][-1]

    history_errors = state["test_errors"][:-1]
    error_prompt = latest_error
    if history_errors:
        compressed_history = prompt_compress_agents.compress_errors(history_errors)
        error_prompt = f"[Past Failed Attempts (Do NOT repeat these mistakes)]:\n{compressed_history}\n\n[Latest Error]:\n{latest_error}"

    if "[LogicError]" in latest_error:
        response = agents.get_logic_fixer_chain().invoke({
            "code": state["current_code"],
            "error": error_prompt,
            "gdd": state["gdd"]
        })
    else:
        response = agents.get_syntax_fixer_chain().invoke({
            "code": state["current_code"],
            "error": error_prompt
        })

    updated_code = clean_code_content(response)

    with open(os.path.join(work_dir, "game.py"), "w", encoding="utf-8") as f:
        f.write(updated_code)

    new_project_files = state["project_files"]
    new_project_files["game.py"] = updated_code

    # [修改] Fixer 改完後，推進一個新 Commit
    fix_commit = {
        "version_id": f"v{len(state.get('commit_history', [])) + 1}_fix",
        "author": "Fixer",
        "code": updated_code,
        "fuzzer_passed": False,
        "error_trace": None,
        "timestamp": str(datetime.now())
    }

    return {
        "current_code": updated_code,
        "project_files": new_project_files,
        "commit_history": state.get("commit_history", []) + [fix_commit],
        "test_iterations": state.get("test_iterations", 0) + 1
    }


# ==========================================
# [新增] 兩個新節點：反思 (Reflector) 與回退 (Rollback)
# ==========================================

def reflector_node(state: GameState, agents, log_callback):
    """背景反思 Agent：從錯誤中提煉避坑指南"""
    log_callback("[Reflector] 正在分析報錯，提煉 Arcade 避坑指南...")
    latest_error = state.get("test_errors", [""])[-1]

    prompt = f"這是一個 Python Arcade 2D 遊戲的報錯：\n{latest_error[:500]}\n請用一句話總結開發者應該避免的寫法，例如 '絕對不要在 on_update 裡重新載入 Texture'。只回傳那句話。"

    try:
        # 使用 Programmer Chain 的 LLM 進行快速反思
        reflection_msg = agents.get_programmer_chain().llm.invoke(prompt).content
        new_guidelines = state.get("core_guidelines", []) + [reflection_msg]
        # 去重並保留最新的 15 條
        new_guidelines = list(dict.fromkeys(new_guidelines))[-15:]
        log_callback(f"[Reflector] 新增規則：{reflection_msg}")
    except Exception as e:
        log_callback(f"[Reflector] 反思提取失敗: {e}")
        new_guidelines = state.get("core_guidelines", [])

    return {"core_guidelines": new_guidelines}


def rollback_node(state: GameState, log_callback, work_dir):
    """Git Checkout：退回上一個可用的版本"""
    log_callback("[Rollback] 偵測到連續修復失敗，啟動時光機退回穩定版本！")
    history = state.get("commit_history", [])

    # 預設退回最原始的版本
    safe_code = history[0]["code"] if history else state.get("current_code", "")

    # 嘗試找最近一個「Fuzzer 測試通過」的 Commit
    for commit in reversed(history[:-1]):
        if commit.get("fuzzer_passed"):
            safe_code = commit["code"]
            break

    # 必須寫入實體檔案，讓後續的 Fuzzer 或 Fixer 能吃到正確的檔案
    with open(os.path.join(work_dir, "game.py"), "w", encoding="utf-8") as f:
        f.write(safe_code)

    new_project_files = state.get("project_files", {})
    new_project_files["game.py"] = safe_code

    return {
        "current_code": safe_code,
        "project_files": new_project_files,
        "consecutive_failures": 0,  # 重置計數器
        # 即使回溯，整體迭代次數還是加 1，避免無限循環
        "test_iterations": state.get("test_iterations", 0) + 1
    }

def check_design_loop(state: GameState):
    return "continue_to_asset" if state["design_iterations"] >= 2 else "back_to_cpo"


def check_plan_loop(state: GameState):
    return "continue_to_programmer" if state["plan_iterations"] >= 2 else "back_to_architect"


def check_test_loop(state: GameState):
    if state.get("is_valid"):
        return "success"
    if state.get("test_iterations", 0) >= 10:
        return "failure"
    if state.get("consecutive_failures", 0) >= 3:
        return "rollback"
    return "reflector"

def ceo_node(state: GameState, agents, log_callback):
    log_callback(f"[Design] CEO Analyzing idea: {state['user_input']}...")
    analysis = agents.get_ceo_chain().invoke({"input": state["user_input"]})
    return {"ceo_analysis": analysis, "design_iterations": 0, "design_feedback": "None"}


def cpo_node(state: GameState, agents, log_callback):
    log_callback(f"[Design] CPO Drafting GDD (Round {state['design_iterations'] + 1})...")
    gdd = agents.get_cpo_chain().invoke({
        "idea": state["user_input"],
        "analysis": state["ceo_analysis"],
        "feedback": state["design_feedback"]
    })
    return {"gdd": gdd}


def design_reviewer_node(state: GameState, agents, log_callback):
    log_callback("[Design] Reviewer critiquing GDD...")
    feedback = agents.get_reviewer_chain().invoke({"gdd": state["gdd"]})
    return {
        "design_feedback": feedback,
        "design_iterations": state["design_iterations"] + 1
    }


def asset_node(state: GameState, provider_name, log_callback):
    log_callback("[System] Generating Assets...")
    assets = generate_assets(gdd_context=state["gdd"], provider=provider_name)
    return {"assets_json": assets}


def architect_node(state: GameState, agents, log_callback):
    log_callback(f"[Architect] Planning system architecture (Round {state['plan_iterations'] + 1})...")

    if state['plan_iterations'] == 0:
        plan = agents.get_architect_chain().invoke({
            "gdd": state["gdd"],
            "assets": state["assets_json"],
            "format_instructions": agents.json_parser.get_format_instructions()
        })
    else:
        log_callback("[Architect] Refining plan based on feedback...")
        plan_str = json.dumps(state["architecture_plan"], indent=2)
        plan = agents.get_architect_refinement_chain().invoke({
            "original_plan": plan_str,
            "feedback": state["plan_feedback"],
            "format_instructions": agents.json_parser.get_format_instructions()
        })
    return {"architecture_plan": plan}


def plan_reviewer_node(state: GameState, agents, log_callback):
    log_callback("[Architect] Plan Review...")
    plan_str = json.dumps(state["architecture_plan"], indent=2)
    feedback = agents.get_plan_reviewer_chain().invoke({"plan": plan_str})
    return {
        "plan_feedback": feedback,
        "plan_iterations": state["plan_iterations"] + 1
    }


def programmer_node(state: GameState, agents, prompt_compress_agents, work_dir, log_callback):
    math_injection = ""
    gdd_lower = state["gdd"].lower()
    if any(k in gdd_lower for k in ["pool", "billiard", "physics", "ball", "shooter", "tank"]):
        log_callback("[System] Detected Physics/Top-Down Game. Injecting Vector Math...")
        math_injection = PHYSICS_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["grid", "2048", "tetris", "snake", "puzzle", "board"]):
        log_callback("[System] Detected Grid-Based Game. Injecting Grid Math...")
        math_injection = GRID_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["jump", "platform", "gravity", "flappy", "mario"]):
        log_callback("[System] Detected Platformer. Injecting Gravity Logic...")
        math_injection = PLATFORMER_CHEAT_SHEET

    # ==========================================
    # AI Template Decision & Injection (Using Chain)
    # ==========================================
    log_callback("[Programmer] AI deciding on required templates...")

    needed_templates = []
    try:
        """ 
        Change from hard coded cutting the gdd into extraction
        Original:
        resp = agents.get_template_decision_chain().invoke({"gdd": state["gdd"][:1500]})
        """
        log_callback("[Programmer] Extracting core mechanics for template decision...")
        compressed_gdd = prompt_compress_agents.get_gdd_mechanics_extractor().invoke({"gdd": state["gdd"]})
        resp = agents.get_template_decision_chain().invoke({"gdd": compressed_gdd})

        match = re.search(r'\[.*?\]', resp, re.DOTALL)
        if match:
            parsed_list = json.loads(match.group(0))
            needed_templates = [t for t in parsed_list if t in ["menu.py", "camera.py", "asset_manager.py"]]
        if not needed_templates:
            needed_templates = ["asset_manager.py", "camera.py", "menu.py"]  # Fallback
    except Exception as e:
        log_callback(f"[Warning] Template decision failed, using defaults. Error: {e}")
        needed_templates = ["asset_manager.py", "camera.py", "menu.py"]

    log_callback(f"[Programmer] Selected templates: {needed_templates}")

    template_code_blocks = []
    guaranteed_imports = []  # 儲存必須出現的 imports
    template_instructions = ""

    # Parse template folder path
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    template_dir = os.path.join(root_dir, "src", "generation", "../template")

    for t_file in needed_templates:
        t_path = os.path.join(template_dir, t_file)
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                template_code_blocks.append(
                    [t_file, f.read()]
                )

            # Give API Usage constraint (變得極度明確)
            if "asset_manager" in t_file:
                guaranteed_imports.append("from asset_manager import AssetManager")
                template_instructions += (
                    "- **Asset Loading (MANDATORY)**: NEVER use `arcade.load_texture`. ALWAYS use `AssetManager` like this:\n"
                    "  `self.texture = AssetManager.get_texture('player.png', fallback_color=arcade.color.RED, width=32, height=32)`\n"
                )
            elif "camera" in t_file:
                guaranteed_imports.append("from camera import FollowCamera")
                template_instructions += (
                    "- **Scrolling (MANDATORY)**: Use `FollowCamera` for scrolling levels. Usage:\n"
                    "  * Init: `self.camera = FollowCamera(SCREEN_WIDTH, SCREEN_HEIGHT, map_width, map_height)`\n"
                    "  * Draw: Call `self.camera.use()` before drawing world sprites. Call `self.ui_camera.use()` for HUD.\n"
                    "  * Update: Call `self.camera.update_to_target(self.player)` in `on_update`.\n"
                )
            elif "menu" in t_file:
                guaranteed_imports.append("from menu import PauseView")
                template_instructions += (
                    "- **Pause System (MANDATORY)**: DO NOT write `self.paused = True`. Instead, handle ESC key like this:\n"
                    "  `if key == arcade.key.ESCAPE: self.window.show_view(PauseView(self))`\n"
                )
        else:
            log_callback(f"[Warning] Template file not found: {t_path}")

    imports_str = "\n".join(guaranteed_imports)
    template_injection_prompt = ""

    if template_instructions:
        template_injection_prompt = (
            "\n=======================================================\n"
            "🔥 CRITICAL: PRE-BUILT MODULES REQUIREMENT 🔥\n"
            "=======================================================\n"
            "I have already created the template files for you. You MUST use them in `game.py`!\n\n"
            "1. YOU MUST PUT THESE IMPORTS AT THE VERY TOP OF `game.py`:\n"
            "```python\n"
            f"{imports_str}\n"
            "```\n\n"
            "2. YOU MUST FOLLOW THESE IMPLEMENTATION RULES:\n"
            f"{template_instructions}\n"
            "Failure to use these classes will result in immediate system crash!\n"
            "=======================================================\n"
        )
    # ==========================================

    log_callback("[Programmer] Implementing game.py with RAG, Math & Templates...")
    complexity_constraints = (
        "1. Write verbose code with detailed comments.\n"
        "2. Implement at least 3 different enemy types or obstacles if applicable.\n"
        "3. Include a 'ParticleManager' class for visual effects.\n"
        "4. ABSOLUTELY NO ABBREVIATED CODE. WRITE EVERY LINE.\n"
        "5. Implement a proper Game Over view and Restart mechanic."
    )
    constraints = "\n".join(state["architecture_plan"].get('constraints', []))
    full_constraints = f"{constraints}\n\n{complexity_constraints}"

    response = agents.get_programmer_chain().invoke({
        "architecture_plan": state["architecture_plan"],
        "review_feedback": state["plan_feedback"],
        "constraints": full_constraints,
        "math_context": math_injection
    })

    content = response.content if hasattr(response, 'content') else str(response)
    cleaned_code = clean_code_content(content)

    # ==========================================
    # [NEW] Failsafe: 自動補全 LLM 漏掉的 Imports
    # ==========================================
    for imp in guaranteed_imports:
        if imp not in cleaned_code:
            log_callback(f"[Failsafe] LLM forgot to import '{imp}'. Auto-injecting...")
            if "import arcade" in cleaned_code:
                # 插入在 import arcade 之後
                cleaned_code = cleaned_code.replace("import arcade", f"import arcade\n{imp}")
            else:
                # 如果連 import arcade 都沒有，直接加在最頂端
                cleaned_code = f"import arcade\n{imp}\n" + cleaned_code

    # Generate Fuzzer Logic
    log_callback("[Test] Generating Fuzzer logic snippet...")
    fuzzer_response = agents.get_fuzzer_chain().invoke({"gdd": state["gdd"]})
    fuzzer_logic = fuzzer_response.content if hasattr(fuzzer_response, 'content') else str(fuzzer_response)
    cleaned_fuzzer_logic = clean_code_content(fuzzer_logic)

    project_files = {"game.py": cleaned_code, "fuzz_logic.py": cleaned_fuzzer_logic}
    for t_file, code in template_code_blocks:
        project_files[t_file] = code

    # Save files to disk for testing
    save_generated_files(project_files, work_dir)

    return {
        "current_code": cleaned_code,
        "project_files": project_files,
        "test_iterations": 0,
        "test_errors": [],
        "is_valid": False
    }


def evaluator_node(state: GameState, agents, work_dir, log_callback):
    """
    Validates the code in order of absolute truth:
    1. Syntax -> 2. Fuzzer (Runtime) -> 3. Static Logic Review
    """
    log_callback(f"\n[Test] Starting validation round {state['test_iterations'] + 1}...")
    current_code = state["current_code"]
    main_file_path = os.path.join(work_dir, "game.py")
    lines_of_traceback_included = 10
    # ==========================================
    # Stage A: Syntax Check (Fastest, catches typos)
    # ==========================================
    log_callback("[Check] Running static syntax check...")
    try:
        compile(current_code, "game.py", 'exec')
        log_callback("[Check] Syntax validation passed.")
    except SyntaxError as e:
        error_msg = f"[SyntaxError] Line {e.lineno}: {e.msg}\n{e.text}"
        log_callback("[Check] Syntax error detected.")
        return {"test_errors": [error_msg]}

    # ==========================================
    # Stage B: Runtime Test (Fuzzer) - THE GROUND TRUTH
    # ==========================================
    log_callback("[Test] Running fuzzer runtime tests...")
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        if root_dir not in sys.path:
            sys.path.append(root_dir)
        from src.testing.runner import run_fuzz_test

        success, error_msg = run_fuzz_test(main_file_path, duration=30)
        if not success:
            log_callback(f"[Test] Fuzzer Runtime Error: {error_msg}")
            # Fuzzer errors are routed to the powerful Syntax/Traceback Fixer
            return {"test_errors": [f"[RuntimeError] {error_msg}"]}
        else:
            log_callback("[Test] Fuzzer passed (No crashes for 30s).")

    except Exception as e:
        import traceback
        log_callback(f"[Error] Test runner exception: {str(e)}")
        short_error = traceback.format_exc().strip().split('\n')[-lines_of_traceback_included:]
        error_msg = f"[TestRunnerError]: {' '.join(short_error)}"
        return {"test_errors": [error_msg]}

    # ==========================================
    # Stage C: Logic Review (Static Analysis)
    # ==========================================
    # Only runs if the game actually survives the Fuzzer!
    log_callback("[Review] Running strict API standard review...")
    review_result = agents.get_logic_reviewer_chain().invoke({"code": current_code})

    if "PASS" not in review_result:
        error_msg = f"[LogicError] {review_result}"
        log_callback(f"[Review] Logic/API Rule Violation: {review_result}")
        # Logic Errors are routed to the Logic Fixer
        return {"test_errors": [error_msg]}
    else:
        log_callback("[Review] Strict API validation passed.")

    log_callback("[Result] Code passed ALL validations successfully!")
    return {"is_valid": True}


def fixer_node(state: GameState, agents, prompt_compress_agents, work_dir, log_callback):
    """Memory Core: Fixes code based on historical error logs."""
    log_callback("[Fixer] Reading historical error logs and attempting fix...")
    latest_error = state["test_errors"][-1]

    # Concatenate history to prevent the agent from repeating mistakes
    history_errors = state["test_errors"][:-1]
    error_prompt = latest_error
    if history_errors:
        compressed_history = prompt_compress_agents.compress_errors(history_errors)
        error_prompt = f"[Past Failed Attempts (Do NOT repeat these mistakes)]:\n{compressed_history}\n\n[Latest Error]:\n{latest_error}"

    # Route to appropriate fixer chain based on error type
    if "[LogicError]" in latest_error:
        response = agents.get_logic_fixer_chain().invoke({
            "code": state["current_code"],
            "error": error_prompt,
            "gdd": state["gdd"]
        })
    else:
        response = agents.get_syntax_fixer_chain().invoke({
            "code": state["current_code"],
            "error": error_prompt
        })

    updated_code = clean_code_content(response)

    # Update file on disk for the next Fuzzer run
    with open(os.path.join(work_dir, "game.py"), "w", encoding="utf-8") as f:
        f.write(updated_code)

    # Update project files in state
    new_project_files = state["project_files"]
    new_project_files["game.py"] = updated_code

    return {
        "current_code": updated_code,
        "project_files": new_project_files,
        "test_iterations": state["test_iterations"] + 1
    }
