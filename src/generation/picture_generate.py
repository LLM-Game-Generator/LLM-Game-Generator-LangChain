import json
from urllib import request
import os
import time
from PIL import Image

# BASE_URL = "https://interactions-articles-minister-living.trycloudflare.com"
BASE_URL = "http://127.0.0.1:8188"

# 將 prompt 送到 ComfyUI，並回傳 prompt_id
def queue_prompt(description, size):
    with open("./src/generation/comfyUI_prompt.json", "r", encoding="utf-8") as f:
        prompt_json = json.load(f)
    
    prompt_json["7"]["inputs"]["text"] = description
    prompt_json["8"]["inputs"]["text"] = "blurry, lowres, watermark"  # negative prompt
    prompt_json["9"]["inputs"]["width"] = size[0]
    prompt_json["9"]["inputs"]["height"] = size[1]

    data = json.dumps({"prompt": prompt_json}).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    response = request.urlopen(req)
    result = json.loads(response.read())
    return result["prompt_id"]

# 等待 ComfyUI 生成圖片完成
def wait_for_image(prompt_id):
    while True:
        history_url = f"{BASE_URL}/history/{prompt_id}"
        response = request.urlopen(history_url)
        history = json.loads(response.read())
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(1)

# 下載 ComfyUI 輸出的圖片
def download_image(filename, save_as=None):
    base_dir = os.getcwd()
    save_dir = os.path.join(base_dir, "output")
    os.makedirs(save_dir, exist_ok=True)

    url = f"{BASE_URL}/view?filename={filename}&type=output"
    response = request.urlopen(url)

    # 如果有指定 save_as，存成你想要的名字
    save_path = os.path.join(save_dir, save_as if save_as else filename)
    with open(save_path, "wb") as f:
        f.write(response.read())
    print("Saved to:", save_path)
    return save_path

def get_image_filename(history):
    outputs = history.get("outputs", {})
    for node_id, node in outputs.items():
        if "images" in node and node["images"]:
            return node["images"][0]["filename"]
    # 如果找不到
    raise ValueError("No image found in history outputs")

def picture_generate(name, description, size):
    print(name)
    print(description)
    print(size)

    # 記住原尺寸
    original_size = size.copy()
    # ---------- 等比例放大到 >=512 ----------
    w, h = size
    scale = max(512 / w, 512 / h) if (w < 512 or h < 512) else 1
    size = [int(w * scale), int(h * scale)]

    prompt_id = queue_prompt(description, size)
    history = wait_for_image(prompt_id)

    # 取 ComfyUI 生成的圖片 filename
    original_filename = get_image_filename(history)

    # 圖片存檔
    filename = f"{name}.png"
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    save_dir = os.path.join(project_root, "output_games", "generated_game", "pictures")
    os.makedirs(save_dir, exist_ok=True)
    image_path = os.path.join(save_dir, filename)

    download_image(original_filename, save_as=image_path)

    # ---------- 縮回原尺寸 ----------
    img = Image.open(image_path)
    img = img.resize((original_size[0], original_size[1]), Image.Resampling.NEAREST)
    img.save(image_path)
    