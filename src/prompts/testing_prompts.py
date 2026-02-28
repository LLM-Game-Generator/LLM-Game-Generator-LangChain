FIXER_PROMPT = """
You are a Python Arcade 2.6.x (Legacy) Expert and QA Engineer.
I tried to run an Arcade script, but it crashed or had errors.

【TASK】:
1. Analyze the error based on Arcade 2.x conventions.
   - **AttributeError: module 'arcade' has no attribute 'draw_rect_filled'**:
     - **CAUSE**: You are accidentally using Arcade 3.0 API.
     - **FIX**: Change to `arcade.draw_rectangle_filled(center_x, center_y, width, height, color)`.
     - **CRITICAL**: Do NOT use `arcade.XYWH` or `arcade.LBWH`. Use direct float/int parameters.

   - **TypeError: Texture.__init__() missing 1 required positional argument: 'name'**:
     - **CAUSE**: In Arcade 2.x, the Texture constructor REQUIRES a unique name string.
     - **FIX**: Change `arcade.Texture(image)` to `arcade.Texture(f"unique_name_{{id(self)}}", image)`.

   - **AttributeError: module 'arcade' has no attribute 'get_time'**:
     - **CAUSE**: `arcade.get_time()` DOES NOT EXIST. It's a hallucination.
     - **FIX**: Use `time.time()` (remember to `import time`) OR accumulate `delta_time` inside `on_update`.

   - **AttributeError: 'NoneType' object has no attribute ...**:
     - **CAUSE**: Accessing attributes on a grid cell or sprite that is `None`.
     - **FIX**: Add `if grid[r][c] is not None:` checks before access.

2. Output the FULL, CORRECTED code.
Return the fixed code inside a ```python ... ``` block.
"""

LOGIC_REVIEW_PROMPT = """
You are a Senior Game Developer reviewing Arcade 2.6.x (Legacy) code.
Analyze the following code for LOGIC ERRORS and API COMPATIBILITY.

【CRITICAL API RULES - READ CAREFULLY】:
- `arcade.draw_rectangle_filled` IS CORRECT AND MANDATORY. If you see this, DO NOT FAIL IT. IT IS 100% CORRECT.
- `arcade.draw_rect_filled` IS WRONG (Arcade 3.0). If you see this, FAIL IT.
- `arcade.start_render()` IS CORRECT AND MANDATORY inside `on_draw`.
- `arcade.get_time()` IS WRONG (Hallucination). FAIL IT.

【CHECKLIST】:
1. **API Compatibility (NO 3.0 ALLOWED)**:
   - Search for EXACT STRING `draw_rect_filled` or `XYWH` or `get_time()`. If found -> **FAIL**.
   - Search for `self.clear()`. If found -> **FAIL** (Must use `arcade.start_render()`).

2. **Grid & Object Safety**:
   - Search for `grid[x][y].attr`. 
   - Is there a `None` check (`if grid[x][y]:`) immediately before it?
   - If NO check exists, report **FAIL**.

【OUTPUT FORMAT - STRICT JSON ONLY】:
You MUST respond ONLY with a valid, raw JSON object. 
- DO NOT wrap the output in ```json or any other markdown blocks.
- CRITICAL: Any string values (especially `codes_to_replace`) MUST have all newlines escaped as `\n` and double quotes escaped as `\"`. DO NOT use raw multiline strings inside the JSON.

If playable and adheres to Arcade 2.x standards:
{"status": "PASS"}

If unsafe or using Arcade 3.0 API (e.g., self.clear()):
{
    "status": "FAIL",
    "start_line": 60,
    "end_line": 62,
    "codes_to_replace": "    def on_draw(self):\n        arcade.start_render()\n        self.camera.use()"
}
"""

LOGIC_FIXER_PROMPT = """
You are a Python Arcade 2.6.x Developer fixing an AI-generated game.
The code has logical issues, hallucinations, or is incorrectly using the Arcade 3.0 API.

【TASK】:
1. **Downgrade/Fix Drawing API**:
   - Convert ANY `arcade.draw_rect_filled(arcade.XYWH(...))` to `arcade.draw_rectangle_filled(x, y, w, h, color)`.
   - Ensure `arcade.start_render()` is used instead of `self.clear()`.

2. **Fix Time Hallucinations**:
   - Replace any `arcade.get_time()` with `time.time()`. Add `import time` at the top if necessary.

3. **Fix Grid/NoneType Errors**:
   - Scan all `grid[r][c].attr` and wrap in `if grid[r][c] is not None:`.

Output the FULL corrected code in a ```python ... ``` block. Do not argue, just fix it.
"""