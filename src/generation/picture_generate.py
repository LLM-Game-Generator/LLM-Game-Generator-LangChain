import json
from urllib import request, error
import os
import time
import random
import io

from PIL import Image
from rembg import remove
from src.generation.create_hitbox import generate_hitbox
from src.config import config

BASE_URL = config.COMFYUI_BASE_URL


def picture_generate(name, description, size, log_callback=print):
    # ==========================================
    # [防呆 1] 強制轉型，避免字串引發崩潰
    # ==========================================
    try:
        w = int(size[0])
        h = int(size[1])
        size = [w, h]
    except (ValueError, TypeError):
        log_callback(f"[PicGen] [Warning] Invalid size format {size} for '{name}'. Using default [64, 64].")
        size = [64, 64]

    # ==========================================
    # [防呆 2] 提早設定存檔路徑，並檢查是否已存在 (避免重複生成)
    # ==========================================
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pic_dir = os.path.join(project_root, config.TIMESTAMP_OUTPUT_DIR, "picture")
    hitbox_dir = os.path.join(project_root, config.TIMESTAMP_OUTPUT_DIR, "hitbox")

    os.makedirs(pic_dir, exist_ok=True)
    os.makedirs(hitbox_dir, exist_ok=True)

    pic_path = os.path.join(pic_dir, name + ".png")
    hitbox_path = os.path.join(hitbox_dir, name + ".json")

    # 如果圖片和碰撞箱都已經存在，代表 AssetGen 階段已經做過了，AST 階段直接跳過以節省時間！
    if os.path.exists(pic_path) and os.path.exists(hitbox_path):
        log_callback(f"[PicGen] Asset '{name}' already exists. Skipping double generation to save time.")
        return

    log_callback(f"[PicGen] Name: {name} | Description: {description} | Size: {size}")

    if size[0] < 32 and size[1] < 32:  # 圖片極小 (w < 32 AND h < 32)
        log_callback(f"[PicGen] {name} is too small ({size}), using fall back.")
        return

    # ---------- 等比例放大到 >= 512 ----------
    original_size = size.copy()  # 記住原尺寸
    w, h = size
    scale = max(512 / w, 512 / h) if (w < 512 or h < 512) else 1
    scale = min(scale, 8.0)  # 加上縮放上限

    # ==========================================
    # [防呆 3] 確保丟給 ComfyUI 的寬高絕對是 8 的倍數
    # ==========================================
    final_w = int((w * scale) // 8) * 8
    final_h = int((h * scale) // 8) * 8

    final_w = max(64, final_w)
    final_h = max(64, final_h)
    size = [final_w, final_h]

    if size[0] > 2048 or size[1] > 2048:  # 圖片特殊 (長寬比超過4倍)
        log_callback(f"[PicGen] {name} is too large ({size}), using fall back.")
        return

    # ---------- 送到 ComfyUI Queue ----------
    try:
        with open("./src/generation/comfyUI_prompt.json", "r", encoding="utf-8") as f:
            prompt_json = json.load(f)
    except Exception as e:
        log_callback(f"[PicGen] [Error] Failed to read comfyUI_prompt.json: {e}")
        return

    prompt_json["7"]["inputs"]["text"] = description  # positive prompt
    prompt_json["8"]["inputs"]["text"] = "blurry, lowres, watermark"  # negative prompt
    prompt_json["9"]["inputs"]["width"] = size[0]  # size
    prompt_json["9"]["inputs"]["height"] = size[1]

    # ==========================================
    # [防呆 4] 加入隨機種子，防止 ComfyUI 發現 Prompt 一樣就直接讀 Cache 導致沒輸出
    # ==========================================
    if "4" in prompt_json and "inputs" in prompt_json["4"]:
        prompt_json["4"]["inputs"]["seed"] = random.randint(1, 99999999999999)

    data = json.dumps({"prompt": prompt_json}).encode("utf-8")
    req = request.Request(f"{BASE_URL}/prompt", data=data, headers={"Content-Type": "application/json"})

    # ==========================================
    # [防呆 5] 網路錯誤防護 (ComfyUI 沒開時不會讓伺服器當機)
    # ==========================================
    try:
        response = request.urlopen(req)
        prompt_id = json.loads(response.read())["prompt_id"]
    except error.URLError as e:
        log_callback(f"[PicGen] [Error] 無法連線到 ComfyUI ({e.reason})。跳過此圖片生成。")
        return

    # ---------- 等待生成完成 ----------
    while True:
        history_url = f"{BASE_URL}/history/{prompt_id}"
        try:
            response = request.urlopen(history_url)
            history = json.loads(response.read())
            if prompt_id in history:
                history = history[prompt_id]
                break
        except error.URLError:
            log_callback(f"[PicGen] [Error] 等待生成時失去 ComfyUI 連線。跳過。")
            return
        time.sleep(1)

    # ---------- 取得圖片 filename ----------
    outputs = history.get("outputs", {})
    filename = None
    for node_id, node in outputs.items():
        if "images" in node and node["images"]:
            filename = node["images"][0]["filename"]
            break

    # ==========================================
    # [防呆 6] 如果真的沒有抓到圖，優雅地跳過，不要觸發 500 Error
    # ==========================================
    if not filename:
        log_callback(
            f"[PicGen] [Warning] No image found in history outputs for '{name}'. Maybe cached or failed. Skipping.")
        return

    # ---------- 去白色背景 ----------
    url = f"{BASE_URL}/view?filename={filename}&type=output"
    try:
        response = request.urlopen(url)
        raw_data = response.read()
    except error.URLError as e:
        log_callback(f"[PicGen] [Error] 無法下載生成的圖片 ({e.reason})。跳過。")
        return

    output_no_bg = remove(raw_data)

    # ---------- 縮回原尺寸 ----------
    img = Image.open(io.BytesIO(output_no_bg)).convert("RGBA")
    img = img.resize((original_size[0], original_size[1]), Image.Resampling.NEAREST)

    img.save(pic_path, "PNG")
    log_callback(f"[PicGen] Picture saved to: {pic_path} | Size: {img.size}")

    # ---------- 生成 Hitbox ----------
    try:
        hitbox_coordinates = generate_hitbox(img, sampling=1)
        with open(hitbox_path, "w") as f:
            json.dump(hitbox_coordinates, f)
        log_callback(f"[PicGen] Hitbox saved to: {hitbox_path}")
    except Exception as e:
        log_callback(f"[PicGen] [Warning] Failed to generate hitbox for {name}: {e}")