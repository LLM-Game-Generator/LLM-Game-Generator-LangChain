import subprocess
import time
import sys
import os


def run_fuzz_test(script_path: str, duration: int = 5) -> tuple[bool, str]:
    """
    執行遊戲腳本並進行壓力測試 (Fuzz Test)。

    Args:
        script_path (str): 遊戲主程式 (game.py) 的絕對路徑。
        duration (int): 測試持續時間 (秒)。

    Returns:
        tuple[bool, str]: (是否通過, 錯誤訊息)
    """
    # 確保路徑是絕對路徑
    script_path = os.path.abspath(script_path)

    if not os.path.exists(script_path):
        return False, f"File not found: {script_path}"

    # 準備執行指令
    cmd = [sys.executable, script_path]

    # 設定工作目錄為腳本所在目錄 (避免找不到 assets)
    cwd = os.path.dirname(script_path)

    process = None
    try:
        # 啟動子進程執行遊戲
        # capture_output=True 會同時捕捉 stdout 和 stderr
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # 讓輸出直接為字串而非 bytes
            encoding='utf-8',
            errors='replace'  # 防止編碼錯誤導致 Runner 崩潰
        )

        start_time = time.time()

        # 迴圈監控
        while time.time() - start_time < duration:
            # 檢查進程是否已結束
            ret_code = process.poll()

            if ret_code is not None:
                # 進程已結束
                stdout, stderr = process.communicate()

                if ret_code != 0:
                    # 非 0 代表發生錯誤 (Crash)
                    error_msg = f"Runtime Crash (Exit Code {ret_code}):\n{stderr}"
                    # 有時候錯誤訊息會在 stdout，視框架而定，兩者都抓比較保險
                    if not stderr.strip():
                        error_msg += f"\nLast Output:\n{stdout}"
                    return False, error_msg
                else:
                    # 正常退出 (可能是遊戲視窗被關閉，但在自動測試中通常算 Pass)
                    return True, "Process exited normally within duration."

            # 暫停一下避免 CPU 飆高
            time.sleep(0.5)

        # 如果跑完 duration 時間還沒掛掉，代表測試通過
        # 溫柔地關閉視窗
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()  # 強制殺死

        return True, "Fuzzer Passed (Run stable for full duration)."

    except Exception as e:
        if process and process.poll() is None:
            process.kill()
        return False, f"Runner Exception: {str(e)}"