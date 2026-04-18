import arcade
from test_asset_manager import *

# --- 測試區：直接把 LLM 生成的 list 貼在這裡 ---
# 這是方便複製黏貼的格式，座標是以 (0, 0) 為中心
TEST_HITBOX = [[-13.0, -3.0], [-12.0, -2.0], [-10.0, -2.0], [-9.0, 0.0], [-7.0, 0.0], [-6.0, 1.0], [-5.0, 3.0], [-4.0, 4.0], [-2.0, 4.0], [-1.0, 12.0], [0.0, 12.0], [1.0, 4.0], [4.0, 4.0], [5.0, 3.0], [6.0, 1.0], [7.0, 1.0], [8.0, 0.0], [9.0, -2.0], [12.0, -2.0], [0.0, 11.0], [0.0, 8.0], [0.0, 5.0], [5.0, 2.0], [8.0, -1.0], [12.0, -3.0], [12.0, -6.0], [12.0, -8.0], [9.0, -9.0], [9.0, -11.0], [8.0, -12.0], [7.0, -13.0], [11.0, -8.0], [10.0, -8.0], [6.0, -13.0], [3.0, -13.0], [0.0, -13.0], [-3.0, -13.0], [-6.0, -13.0], [-7.0, -13.0], [-8.0, -12.0], [-9.0, -12.0], [-10.0, -11.0], [-11.0, -8.0], [-12.0, -8.0], [-13.0, -7.0], [-10.0, -10.0], [-10.0, -9.0], [-13.0, -6.0], [-13.0, -4.0], [-9.0, -1.0], [-5.0, 2.0], [-1.0, 5.0], [-1.0, 8.0], [-1.0, 11.0]]
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 900
SCREEN_TITLE = "Hitbox 測試工具"
MOVEMENT_SPEED = 5

class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.LIGHT_CORAL)
        self.texture = AssetManager.get_texture('atank', fallback_color=arcade.color.GREEN, width=32, height=32)
        self.hit_box = TEST_HITBOX
        self.player_x = SCREEN_WIDTH // 2
        self.player_y = SCREEN_HEIGHT // 2
        self.change_x = 0
        self.change_y = 0

        self.obstacle_x = 300
        self.obstacle_y = 600
        self.obstacle_size = 100  # 正方形邊長

    def check_collision_with_box(self, abs_points):
        half = self.obstacle_size / 2
        left = self.obstacle_x - half
        right = self.obstacle_x + half
        bottom = self.obstacle_y - half
        top = self.obstacle_y + half

        for x, y in abs_points:
            if left <= x <= right and bottom <= y <= top:
                return True
        return False

    def on_draw(self):
        arcade.start_render()
        arcade.draw_texture_rectangle(self.player_x, self.player_y, self.texture.width, self.texture.height, self.texture)

        arcade.draw_rectangle_filled(self.obstacle_x, self.obstacle_y, self.obstacle_size, self.obstacle_size, arcade.color.DARK_RED)

        # 1. 繪製中心輔助線 (十字線)，方便對齊
        arcade.draw_line(self.player_x - 5, self.player_y, self.player_x + 5, self.player_y, arcade.color.GRAY)
        arcade.draw_line(self.player_x, self.player_y - 5, self.player_x, self.player_y + 5, arcade.color.GRAY)

        # 2. 將相對座標轉換為畫面上的絕對座標
        # 使用串列導引 (List Comprehension) 快速轉換
        abs_points = [(x * 8 + self.player_x, y * 8 + self.player_y) for x, y in TEST_HITBOX]

        # 3. 繪製 Hitbox 邊框 (非塗滿)
        collision = self.check_collision_with_box(abs_points)
        color = arcade.color.YELLOW if collision else arcade.color.BLUE

        arcade.draw_polygon_outline(abs_points, color, line_width=2)
        
        # 繪製頂點小圓點 (方便確認點的位置)
        for px, py in abs_points:
            arcade.draw_circle_filled(px, py, 3, arcade.color.BLACK)

        # 4. 顯示目前測試的座標文字
        arcade.draw_text(f"Current Hitbox: {TEST_HITBOX}", 10, 20, arcade.color.WHITE, 12)

    def on_update(self, delta_time):
        self.player_x += self.change_x
        self.player_y += self.change_y

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W: self.change_y = MOVEMENT_SPEED
        elif key == arcade.key.S: self.change_y = -MOVEMENT_SPEED
        elif key == arcade.key.A: self.change_x = -MOVEMENT_SPEED
        elif key == arcade.key.D: self.change_x = MOVEMENT_SPEED

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.W, arcade.key.S): self.change_y = 0
        if key in (arcade.key.A, arcade.key.D): self.change_x = 0

def main():
    MyGame()
    arcade.run()

if __name__ == "__main__":
    main()