import arcade
from menu import PauseView
from camera import FollowCamera
from asset_manager import AssetManager

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
MAP_WIDTH = 2000
MAP_HEIGHT = 2000

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.AMAZON)

        # 測試 1: 攝影機 (初始化世界大小為 2000x2000)
        self.camera = FollowCamera(SCREEN_WIDTH, SCREEN_HEIGHT, MAP_WIDTH, MAP_HEIGHT)
        self.ui_camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

        # 測試 2: 資源管理器 (故意給一個不存在的路徑，看看會不會自動產生黃色方塊)
        player_texture = AssetManager.get_texture("fake_player.png", fallback_color=arcade.color.YELLOW)
        self.player = arcade.Sprite(texture=player_texture)
        self.player.center_x = 400
        self.player.center_y = 300
        self.player.change_x = 0
        self.player.change_y = 0

        # 隨機產生一些障礙物當作背景參考，才能看出攝影機有在移動
        self.walls = arcade.SpriteList()
        for i in range(30):
            wall_tex = AssetManager.get_texture(f"fake_wall_{i}.png", fallback_color=arcade.color.DARK_GRAY)
            wall = arcade.Sprite(texture=wall_tex)
            wall.center_x = (i * 150) % MAP_WIDTH
            wall.center_y = (i * 220) % MAP_HEIGHT
            self.walls.append(wall)

    def on_draw(self):
        self.clear()

        # 啟動跟隨攝影機畫地圖與玩家
        self.camera.use()
        self.walls.draw()
        self.player.draw()

        # 啟動 UI 攝影機畫固定在畫面上的文字
        self.ui_camera.use()
        arcade.draw_text("Press WASD/Arrows to move. Press ESC for Menu.", 10, 10, arcade.color.WHITE, 16)

    def on_update(self, delta_time):
        # 移動玩家
        self.player.center_x += self.player.change_x
        self.player.center_y += self.player.change_y

        # 邊界限制 (不讓玩家跑出地圖)
        if self.player.left < 0: self.player.left = 0
        if self.player.right > MAP_WIDTH: self.player.right = MAP_WIDTH
        if self.player.bottom < 0: self.player.bottom = 0
        if self.player.top > MAP_HEIGHT: self.player.top = MAP_HEIGHT

        # 讓攝影機跟隨玩家
        self.camera.update_to_target(self.player, smoothing=0.1)

    def on_key_press(self, key, modifiers):
        speed = 5
        if key in (arcade.key.UP, arcade.key.W):
            self.player.change_y = speed
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.player.change_y = -speed
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.player.change_x = -speed
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.player.change_x = speed
        elif key == arcade.key.ESCAPE:
            # 測試 3: 暫停選單 (把目前的 GameView 傳遞給 PauseView 覆蓋上去)
            pause_view = PauseView(self)
            self.window.show_view(pause_view)

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.UP, arcade.key.W, arcade.key.DOWN, arcade.key.S):
            self.player.change_y = 0
        elif key in (arcade.key.LEFT, arcade.key.A, arcade.key.RIGHT, arcade.key.D):
            self.player.change_x = 0

def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "Template Tester")
    game_view = GameView()
    window.show_view(game_view)
    arcade.run()

if __name__ == "__main__":
    main()