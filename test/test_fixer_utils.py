import sys
import os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)
from src.generation.core import apply_deterministic_fix
from src.generation.core import e

def test_basic_replacement():
    """測試最基本的行號替換邏輯"""
    original = (
        "def on_draw(self):\n"
        "    self.clear()\n"  # Line 2
        "    self.camera.use()\n"  # Line 3
        "    # draw things\n"
    )

    # 預期 LLM 給的修正程式碼
    replacement = "    arcade.start_render()\n    self.camera.use()"

    # 替換第 2 到第 3 行
    result = apply_deterministic_fix(original, start_line=2, end_line=3, replacement=replacement)

    expected = (
        "def on_draw(self):\n"
        "    arcade.start_render()\n"
        "    self.camera.use()\n"
        "    # draw things\n"
    )
    assert result.strip() == expected.strip(), "基本替換邏輯錯誤"


def test_markdown_stripping():
    """測試是否能正確剝除 LLM 雞婆加上的 Markdown 標記"""
    original = (
        "x = 1\n"
        "y = 2\n"  # Line 2
        "z = 3\n"
    )

    # LLM 帶有 Markdown 的暴力輸出
    replacement = "```python\ny = 20\n```"

    result = apply_deterministic_fix(original, start_line=2, end_line=2, replacement=replacement)

    expected = (
        "x = 1\n"
        "y = 20\n"
        "z = 3\n"
    )
    assert result.strip() == expected.strip(), "無法正確清除 Markdown 標記"


def test_multiline_to_single_line():
    """測試多行錯誤被合併成單行修正的情況"""
    original = (
        "def bad_func():\n"
        "    a = 1\n"  # Line 2
        "    b = 2\n"  # Line 3
        "    c = a + b\n"  # Line 4
        "    return c\n"
    )

    # 直接一行搞定
    replacement = "    return 3"

    result = apply_deterministic_fix(original, start_line=2, end_line=4, replacement=replacement)

    expected = (
        "def bad_func():\n"
        "    return 3\n"
        "    return c\n"  # 注意：原本第5行保留
    )
    assert result.strip() == expected.strip(), "多行縮減為單行時發生錯誤"