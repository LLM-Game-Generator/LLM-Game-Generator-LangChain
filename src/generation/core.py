import os
from src.generation.chains import ArcadeAgentChain
from src.generation.asset_gen import generate_assets
from src.utils import clean_code_content, save_generated_files
from src.config import config
from src.testing.runner import run_fuzz_test


def run_design_phase(user_input, log_callback=print, provider="openai", model=None):
    """
    執行設計階段：CEO -> CPO -> Reviewer 循環
    """
    agents = ArcadeAgentChain(provider, model)

    log_callback(f"[Design] CEO Analyzing idea: {user_input}...")
    ceo_analysis = agents.get_ceo_chain().invoke({"input": user_input})

    # CPO & Reviewer Loop
    feedback = "None"
    final_gdd = ""

    log_callback("[Design] CPO Drafting GDD...")
    # Review for 2 times
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
    [NEW] 執行架構規劃階段 (含 Plan Review Loop)
    確保在寫代碼前，架構圖符合 Arcade 2.x API 規範。
    """
    agents = ArcadeAgentChain(provider, model)

    log_callback("[Architect] Planning system architecture...")

    # 1. Initial Plan
    plan = agents.get_architect_chain().invoke({
        "gdd": gdd_context,
        "assets": asset_json,
        "format_instructions": agents.json_parser.get_format_instructions()
    })

    # 2. Plan Review Loop (Optional but recommended)
    # 這裡可以加入一個簡單的 Review 步驟，讓 Architect 自我修正
    log_callback("[Reviewer] Validating architecture plan...")
    review_feedback = agents.get_plan_reviewer_chain().invoke({"plan": str(plan)})

    # 將 Review 意見附加回 Plan 中 (這裡簡化處理，直接傳給 Programmer)
    return plan, review_feedback


def run_production_pipeline(gdd_context, asset_json, log_callback=print, provider="openai", model=None):
    """
    執行生產階段，強制產出單一 game.py 檔案。
    現在包含 Plan Review 流程。
    """
    agents = ArcadeAgentChain(provider, model)

    # 1. Plan Phase with Review
    plan, review_feedback = run_plan_phase(gdd_context, asset_json, log_callback, provider, model)

    # 2. Single file generation with constraints & review feedback
    log_callback("[Programmer] Implementing game.py (integrating logic)...")

    # 組合約束條件與 Review 意見
    complexity_constraints = (
        "1. Write verbose code with detailed comments.\n"
        "2. Implement at least 3 different enemy types or obstacles if applicable.\n"
        "3. Include a 'ParticleManager' class for visual effects.\n"
        "4. ABSOLUTELY NO ABBREVIATED CODE. WRITE EVERY LINE."
    )
    constraints = "\n".join(plan.get('constraints', []))
    full_constraints = f"{constraints}\n\n{complexity_constraints}"

    response = agents.get_programmer_chain().invoke({
        "architecture_plan": plan.get('architecture', ''),
        "review_feedback": review_feedback,
        "constraints": full_constraints
    })

    # Get the content and clean it
    content = response.content if hasattr(response, 'content') else str(response)
    cleaned_code = clean_code_content(content)

    return {"game.py": cleaned_code}


def run_test_and_fix_phase(project_files, work_dir, log_callback=print, provider="openai", model=None):
    """
    執行測試與修復階段 (Fuzzer + Static Analysis)
    """
    agents = ArcadeAgentChain(provider, model)

    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    main_filename = "game.py"
    main_file_path = os.path.join(work_dir, main_filename)

    save_generated_files(project_files, work_dir)

    if main_filename not in project_files:
        log_callback(f"[Test] {main_filename} not found. Skipping tests.")
        return project_files

    # --- 1. Runtime Fuzzing Loop ---
    max_retries = 3
    for attempt in range(max_retries):
        log_callback(f"[Test] Running Fuzzer (Attempt {attempt + 1}/{max_retries})...")

        success, error_msg = run_fuzz_test(main_file_path, duration=5)

        if success:
            log_callback("[Test] Fuzzer Passed (Runtime Safe).")
            break

        log_callback(f"[Test] Runtime Crash Detected:\n{error_msg}")
        log_callback("[Fixer] Fixing Syntax/Runtime errors...")

        with open(main_file_path, "r", encoding="utf-8") as f:
            broken_code = f.read()

        fixed_response = agents.get_syntax_fixer_chain().invoke({
            "code": broken_code,
            "error": error_msg
        })

        cleaned_fixed_code = clean_code_content(fixed_response)
        project_files[main_filename] = cleaned_fixed_code

        with open(main_file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_fixed_code)

        log_callback("[Fixer] Code patched and saved.")

    # --- 2. Static Logic Review Loop ---
    log_callback("[Review] Running Static Logic Analysis...")

    current_code = project_files.get(main_filename, "")
    review_result = agents.get_logic_reviewer_chain().invoke({"code": current_code})

    if "PASS" in review_result:
        log_callback("[Review] Code complies with Arcade 2.x standards.")
    else:
        log_callback(f"[Review] Issues found: {review_result}")
        log_callback("[Fixer] Fixing logic/API issues...")

        logic_fixed_response = agents.get_logic_fixer_chain().invoke({
            "code": current_code,
            "error": review_result
        })

        final_code = clean_code_content(logic_fixed_response)
        project_files[main_filename] = final_code

        with open(main_file_path, "w", encoding="utf-8") as f:
            f.write(final_code)

        log_callback("[Fixer] Logic fixed.")

    return project_files


def run_full_generator_pipeline(user_input, log_callback=print, provider="openai"):
    """
    [Unified Entry Point]
    Encapsulates the entire generation process: Design -> Asset -> Production -> Test.
    """
    # 1. Design Phase
    gdd = run_design_phase(user_input, log_callback, provider)

    # 2. Asset Phase
    log_callback("[System] Generating Assets...")
    assets = generate_assets(gdd, provider=provider)

    # 3. Production Phase (Now includes Plan Review)
    project_files = run_production_pipeline(gdd, assets, log_callback, provider)

    # 4. Test & Fix Phase
    log_callback("[System] Starting Test & Fix Loop...")
    output_path = os.path.join(config.OUTPUT_DIR, "generated_game")
    project_files = run_test_and_fix_phase(project_files, output_path, log_callback, provider)

    return project_files