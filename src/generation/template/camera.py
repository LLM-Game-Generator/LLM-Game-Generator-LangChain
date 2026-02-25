import arcade
from pyglet.math import Vec2


class FollowCamera:
    """
    通用跟隨攝影機
    封裝了 arcade.Camera，並提供邊界限制(Clamp)與平滑移動(Lerp)功能。
    """

    def __init__(self, viewport_width: int, viewport_height: int, map_width: int, map_height: int):
        self.camera = arcade.Camera(viewport_width, viewport_height)
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.map_width = map_width
        self.map_height = map_height

    def use(self):
        """啟用攝影機 (在 on_draw 時呼叫)"""
        self.camera.use()

    def update_to_target(self, target_sprite: arcade.Sprite, smoothing: float = 0.1):
        """
        每幀呼叫，讓攝影機平滑跟隨目標 (如玩家)。
        :param target_sprite: 要跟隨的目標 sprite
        :param smoothing: 平滑度 (1.0 為瞬間移動，0.1 為平滑跟隨)
        """
        # 1. 計算如果將玩家放在畫面正中央，攝影機的左下角座標應該在哪裡
        screen_center_x = target_sprite.center_x - (self.camera.viewport_width / 2)
        screen_center_y = target_sprite.center_y - (self.camera.viewport_height / 2)

        # 2. 邊界限制 (Clamp) - 確保鏡頭不會拍到地圖外面的黑邊
        if screen_center_x < 0:
            screen_center_x = 0
        if screen_center_y < 0:
            screen_center_y = 0

        # 如果地圖比視窗大，才限制最大邊界
        max_x = max(0, self.map_width - self.viewport_width)
        max_y = max(0, self.map_height - self.viewport_height)

        if screen_center_x > max_x:
            screen_center_x = max_x
        if screen_center_y > max_y:
            screen_center_y = max_y

        # 3. 移動攝影機 (Arcade 內建平滑插值)
        target_position = Vec2(screen_center_x, screen_center_y)
        self.camera.move_to(target_position, smoothing)