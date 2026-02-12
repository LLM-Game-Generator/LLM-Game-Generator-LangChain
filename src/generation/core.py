import os
import json
import sys
from src.generation.chains import ArcadeAgentChain
from src.generation.asset_gen import generate_assets
from src.utils import clean_code_content, save_generated_files
from src.config import config
from src.prompts.game_logic_cheat_sheet import (
    PHYSICS_MATH_CHEAT_SHEET,
    GRID_MATH_CHEAT_SHEET,
    PLATFORMER_CHEAT_SHEET
)


def run_design_phase(user_input, log_callback=print, provider="openai", model=None):
    agents = ArcadeAgentChain(provider, model)

    log_callback(f"[Design] CEO Analyzing idea: {user_input}...")
    ceo_analysis = agents.get_ceo_chain().invoke({"input": user_input})

    feedback = "None"
    final_gdd = ""

    log_callback("[Design] CPO Drafting GDD...")
    for i in range(2):
        final_gdd = agents.get_cpo_chain().invoke({
            "idea": user_input,
            "analysis": ceo_analysis,
            "feedback": feedback
        })
        log_callback(f"[Design] Reviewer critiquing round {i + 1}...")
        feedback = agents.get_reviewer_chain().invoke({"gdd": final_gdd})

    return final_gdd


def run_plan_phase(gdd_context, asset_json, log_callback=print, provider="openai", model=None):
    """
    Execute Planning Phase with Iterative Review Loop (Core Logic Ported)
    Plan -> Review -> Refine -> Review -> Refine
    """
    agents = ArcadeAgentChain(provider, model)

    log_callback("[Architect] Initializing system architecture...")

    # 1. Initial Plan
    current_plan = agents.get_architect_chain().invoke({
        "gdd": gdd_context,
        "assets": asset_json,
        "format_instructions": agents.json_parser.get_format_instructions()
    })

    # 2. Review & Refine Loop (2 Attempts)
    review_feedback = "None"

    for attempt in range(2):
        log_callback(f"[Architect] Plan Review Round {attempt + 1}/2...")

        # Convert plan to string for the reviewer
        plan_str = json.dumps(current_plan, indent=2)

        # Call Reviewer
        review_feedback = agents.get_plan_reviewer_chain().invoke({"plan": plan_str})

        # Call Refinement Agent
        log_callback(f"[Architect] Refining plan based on feedback...")
        current_plan = agents.get_architect_refinement_chain().invoke({
            "original_plan": plan_str,
            "feedback": review_feedback,
            "format_instructions": agents.json_parser.get_format_instructions()
        })

    log_callback("[Architect] Final Architecture Locked.")
    return current_plan, review_feedback


def run_production_pipeline(gdd_context, asset_json, log_callback=print, provider="openai", model=None):
    agents = ArcadeAgentChain(provider, model)

    # 1. Plan Phase with Loop
    plan, review_feedback = run_plan_phase(gdd_context, asset_json, log_callback, provider, model)

    # 2. Logic Injection (Based on Game Type)
    math_injection = ""
    gdd_lower = gdd_context.lower()

    if any(k in gdd_lower for k in ["pool", "billiard", "physics", "ball", "shooter", "tank"]):
        log_callback("💡 Detected Physics/Top-Down Game. Injecting Vector Math...")
        math_injection = PHYSICS_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["grid", "2048", "tetris", "snake", "puzzle", "board"]):
        log_callback("💡 Detected Grid-Based Game. Injecting Grid Math...")
        math_injection = GRID_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["jump", "platform", "gravity", "flappy", "mario"]):
        log_callback("💡 Detected Platformer. Injecting Gravity Logic...")
        math_injection = PLATFORMER_CHEAT_SHEET

    # 3. Programmer Phase
    log_callback("[Programmer] Implementing game.py with RAG & Math Tools...")

    complexity_constraints = (
        "1. Write verbose code with detailed comments.\n"
        "2. Implement at least 3 different enemy types or obstacles if applicable.\n"
        "3. Include a 'ParticleManager' class for visual effects.\n"
        "4. ABSOLUTELY NO ABBREVIATED CODE. WRITE EVERY LINE.\n"
        "5. Implement a proper Game Over view and Restart mechanic."
    )

    constraints = "\n".join(plan.get('constraints', []))
    full_constraints = f"{constraints}\n\n{complexity_constraints}"

    response = agents.get_programmer_chain().invoke({
        "architecture_plan": plan.get('architecture', ''),
        "review_feedback": review_feedback,
        "constraints": full_constraints,
        "math_context": math_injection
    })

    content = response.content if hasattr(response, 'content') else str(response)
    cleaned_code = clean_code_content(content)

    return {"game.py": cleaned_code}


def run_test_and_fix_phase(project_files, work_dir, log_callback=print, provider="openai", model=None, gdd: str = None):
    agents = ArcadeAgentChain(provider, model)

    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    main_filename = "game.py"
    main_file_path = os.path.join(work_dir, main_filename)

    save_generated_files(project_files, work_dir)

    if main_filename not in project_files:
        log_callback(f"[Test] {main_filename} not found. Skipping tests.")
        return project_files

    # --- 0. Generate Fuzzer Logic ---
    log_callback("[Test] Generating Fuzzer logic snippet...")

    fuzzer_response = agents.get_fuzzer_chain().invoke({"gdd": gdd})
    fuzzer_logic = fuzzer_response.content if hasattr(fuzzer_response, 'content') else str(fuzzer_response)

    cleaned_fuzzer_logic = clean_code_content(fuzzer_logic)
    fuzzer_file_path = os.path.join(work_dir, "fuzz_logic.py")
    with open(fuzzer_file_path, "w", encoding="utf-8") as f:
        f.write(cleaned_fuzzer_logic)
    project_files["fuzz_logic.py"] = cleaned_fuzzer_logic

    # --- 1. Runtime Fuzzing Loop ---
    max_retries = 5
    is_valid = False

    while (not is_valid) and (max_retries > 0):
        current_code = project_files.get(main_filename, "")
        log_callback(f"\n[Test] 開始新一輪驗證 (剩餘嘗試次數: {max_retries})")

        # --- 階段 A: 語法檢查 (Syntax Check) ---
        log_callback("[Check] 執行靜態語法檢查...")
        try:
            compile(current_code, main_filename, 'exec')
            log_callback("✅ 語法正確")
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}\n{e.text}"
            log_callback(f"❌ 語法錯誤: {error_msg} (嘗試修復中...)")

            syntax_fixed_response = agents.get_syntax_fixer_chain().invoke({
                "code": current_code,
                "error": error_msg
            })

            updated_code = clean_code_content(syntax_fixed_response)
            project_files[main_filename] = updated_code
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(updated_code)

            max_retries -= 1
            log_callback("[Fixer] 語法已修復，重新開始驗證流程。")
            continue

        # --- 階段 B: 邏輯檢查 (Logic Review) ---
        log_callback("[Review] 執行邏輯與 API 標準檢查...")
        review_result = agents.get_logic_reviewer_chain().invoke({"code": current_code})

        if "PASS" not in review_result:
            log_callback(f"❌ 邏輯錯誤: {review_result} (嘗試修復中...)")

            logic_fixed_response = agents.get_logic_fixer_chain().invoke({
                "code": current_code,
                "error": review_result,
                "gdd": gdd
            })

            updated_code = clean_code_content(logic_fixed_response)
            project_files[main_filename] = updated_code
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(updated_code)

            max_retries -= 1
            log_callback("[Fixer] 邏輯已修復，重新開始驗證流程。")
            continue

        log_callback("✅ 邏輯正確")

        # --- 階段 C: 運行時測試 (Fuzzer Test) ---
        log_callback("[Test] 執行 Fuzzer 運行測試...")

        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            if root_dir not in sys.path:
                sys.path.append(root_dir)
            from src.testing.runner import run_fuzz_test

            # 這裡的 duration 可以根據 config 調整
            success, error_msg = run_fuzz_test(main_file_path, duration=30)
        except Exception as e:
            log_callback(f"[Error] 測試執行器異常: {str(e)}")
            break

        if not success:
            log_callback(f"❌ 運行時錯誤 (Fuzzer): {error_msg} (嘗試修復中...)")

            # 運行時崩潰通常也由語法修復鏈處理，或您可以定義專門的 runtime fixer
            fixed_response = agents.get_syntax_fixer_chain().invoke({
                "code": current_code,
                "error": error_msg
            })

            updated_code = clean_code_content(fixed_response)
            project_files[main_filename] = updated_code
            with open(main_file_path, "w", encoding="utf-8") as f:
                f.write(updated_code)

            max_retries -= 1
            log_callback("[Fixer] 運行錯誤已修復，重新開始驗證流程。")
            continue

        log_callback("✅ 運行功能正確")

        # 通過所有關卡
        is_valid = True

    # --- 2. 結束處理 ---
    if is_valid:
        log_callback("[Result] RESULT_SUCCESS: 程式碼通過所有驗證！")
    else:
        log_callback("[Result] RESULT_FAIL: 已達最大重試次數，驗證失敗。")

    return project_files

def run_full_generator_pipeline(user_input, log_callback=print, provider="openai"):
    # 1. Design Phase
    gdd = run_design_phase(
        user_input=user_input,
        log_callback=log_callback,
        provider=provider
    )

    # 2. Asset Phase
    log_callback("[System] Generating Assets...")
    assets = generate_assets(gdd_context=gdd, provider=provider)

    # 3. Production Phase (Now includes Iterative Planning & Math Injection)
    project_files = run_production_pipeline(
        gdd_context=gdd,
        asset_json=assets,
        log_callback=log_callback,
        provider=provider
    )

    # 4. Test & Fix Phase
    log_callback("[System] Starting Test & Fix Loop...")
    output_path = os.path.join(config.OUTPUT_DIR, "generated_game")
    project_files = run_test_and_fix_phase(
        project_files=project_files,
        work_dir=output_path,
        log_callback=log_callback,
        provider=provider,
        model=None,
        gdd=gdd
    )

    return project_files