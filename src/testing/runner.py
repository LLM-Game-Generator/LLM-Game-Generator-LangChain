import os
import re
import subprocess
import sys
import textwrap


def get_dynamic_fuzz_logic(game_file_path: str) -> str:
    """
    尋找動態 Fuzz 邏輯。Arcade 2.x 版本應呼叫 window 的方法。
    """
    dir_path = os.path.dirname(game_file_path)
    logic_path = os.path.join(dir_path, "fuzz_logic.py")

    default_logic = """
# Random Mouse Press (Arcade 2.x Style)
if _monkey_random.random() < 0.05:
    _mx = _monkey_random.randint(0, self.width)
    _my = _monkey_random.randint(0, self.height)
    self.on_mouse_press(_mx, _my, arcade.MOUSE_BUTTON_LEFT, 0)
    self.on_mouse_release(_mx, _my, arcade.MOUSE_BUTTON_LEFT, 0)

# Random Key Press
if _monkey_random.random() < 0.05:
    _keys = [arcade.key.SPACE, arcade.key.LEFT, arcade.key.RIGHT, arcade.key.UP, arcade.key.DOWN]
    _k = _monkey_random.choice(_keys)
    self.on_key_press(_k, 0)
    """

    if os.path.exists(logic_path):
        try:
            with open(logic_path, "r", encoding="utf-8") as f:
                content = f.read()
                return content
        except Exception:
            return default_logic

    return default_logic


def inject_monkey_bot(code_content: str, bot_logic: str) -> str:
    """
    將 Monkey Bot 注入 Arcade 2.x 的 on_update 方法中。
    修復：若無 on_update，則自動建立一個。
    """
    # 預處理
    lines = bot_logic.splitlines()
    filtered_lines = [line for line in lines if
                      not any(line.strip().startswith(s) for s in ["import arcade", "import random"])]
    bot_logic = "\n".join(filtered_lines)
    bot_logic = textwrap.dedent(bot_logic).strip()

    bot_logic = bot_logic.replace("window.", "self.")
    bot_logic = bot_logic.replace("random.", "_monkey_random.")

    monkey_bot_template = """
    def on_update(self, delta_time):
        # --- [INJECTED MONKEY BOT START] ---
        try:
            import random as _monkey_random
{indented_logic}
        except Exception as _e:
            pass 
        # --- [INJECTED MONKEY BOT END] ---
"""

    # 1. 嘗試尋找現有的注入點
    patterns = [
        r"def\s+on_update\s*\(\s*self\s*,\s*delta_time[^)]*\)\s*:",
        r"def\s+update\s*\(\s*self\s*,\s*delta_time[^)]*\)\s*:",
        r"def\s+update\s*\(\s*self\s*\)\s*:"
    ]

    for pattern in patterns:
        match = re.search(pattern, code_content)
        if match:
            # 如果找到了，就插入邏輯（去掉 template 的 def 行）
            insertion_point = match.end()
            pure_logic = textwrap.indent(bot_logic, "            ")
            # 這裡我們不使用完整 template，只取邏輯部分
            inject_payload = f"\n        # --- [INJECTED] ---\n        try:\n            import random as _monkey_random\n{pure_logic}\n        except: pass\n"
            return code_content[:insertion_point] + inject_payload + code_content[insertion_point:]

    # 2. 如果沒找到 on_update，則在類別定義後強行插入一個新的 on_update
    class_pattern = r"class\s+\w+\s*\(\s*arcade\.Window\s*\)\s*:"
    class_match = re.search(class_pattern, code_content)
    if class_match:
        insertion_point = class_match.end()
        indented_logic = textwrap.indent(bot_logic, "            ")
        new_method = monkey_bot_template.replace("{indented_logic}", indented_logic)
        return code_content[:insertion_point] + "\n" + new_method + code_content[insertion_point:]

    return code_content

def run_fuzz_test(file_path: str, duration: int = 15) -> tuple[bool, str]:
    """
    執行 Fuzz 測試並回傳結果。
    """
    try:
        if not os.path.exists(file_path):
            return False, "檔案不存在"

        with open(file_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        # 獲取並注入邏輯
        bot_logic = get_dynamic_fuzz_logic(file_path)
        fuzzed_code = inject_monkey_bot(original_code, bot_logic)

        # 建立暫存檔執行測試
        temp_file = file_path.replace(".py", "_fuzz_temp.py")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(fuzzed_code)

        env = os.environ.copy()
        env["SDL_AUDIODRIVER"] = "dummy"  # 避免音效輸出錯誤

        cmd = [sys.executable, temp_file]
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env
        )

        try:
            # 等待指定時間，若沒崩潰則視為通過
            stdout, stderr = process.communicate(timeout=duration)
        except subprocess.TimeoutExpired:
            process.kill()
            if os.path.exists(temp_file): os.remove(temp_file)
            return True, "Fuzz Test Passed: 遊戲在壓力測試中存活。"

        if os.path.exists(temp_file): os.remove(temp_file)

        if process.returncode != 0:
            error_msg = stderr
            if "Traceback" in stderr:
                error_msg = "Traceback" + stderr.split("Traceback")[-1]
            return False, f"Arcade 運行崩潰: {error_msg}"

        return True, "Fuzz Test Passed."
    except Exception as e:
        return False, f"Fuzzer 執行異常: {str(e)}"


if __name__ == "__main__":
    file_path = "/mnt/d/NCKU/CSIE-Project/LLM-Game-Generator-LangChain/output_games/generated_game/game.py"
    success, msg = run_fuzz_test(file_path, 10)
    print(success, msg)