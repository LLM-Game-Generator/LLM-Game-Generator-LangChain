import arcade
import random


class InfiniteMapManager:
    """
    無限地圖管理器 (Infinite Map Manager)
    使用區塊 (Chunk) 系統來動態生成和卸載地圖物件，實現無限探索。
    """

    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self.active_chunks = {}  # 儲存已生成的區塊 {(cx, cy): SpriteList}
        self.visible_chunks = []  # 目前可見需要繪製的區塊

    def get_chunk_coords(self, x: float, y: float) -> tuple[int, int]:
        """將世界座標轉換為區塊座標"""
        return int(x // self.chunk_size), int(y // self.chunk_size)

    def _create_default_chunk(self, cx: int, cy: int) -> arcade.SpriteList:
        """
        預設的區塊生成邏輯。
        當 AI 或開發者沒有提供自訂生成器時，預設會散佈一些簡單的環境方塊。
        """
        chunk_sprites = arcade.SpriteList()
        # 隨機在區塊內散佈一些裝飾物
        for _ in range(5):
            pos_x = cx * self.chunk_size + random.randint(0, self.chunk_size)
            pos_y = cy * self.chunk_size + random.randint(0, self.chunk_size)

            # 使用純色方塊作為預設地形，確保即使沒圖片也不會崩潰
            tile = arcade.SpriteSolidColor(32, 32, arcade.color.FOREST_GREEN)
            tile.center_x = pos_x
            tile.center_y = pos_y
            chunk_sprites.append(tile)

        return chunk_sprites

    def update(self, player_x: float, player_y: float, view_distance: int = 1):
        """
        根據玩家位置動態加載周圍的區塊。應該在 on_update 中呼叫。
        :param view_distance: 玩家周圍要載入多少個區塊的半徑 (1 代表 3x3 九宮格)
        """
        current_cx, current_cy = self.get_chunk_coords(player_x, player_y)
        needed_chunks = set()

        # 計算當前視野內需要的區塊座標
        for dx in range(-view_distance, view_distance + 1):
            for dy in range(-view_distance, view_distance + 1):
                needed_chunks.add((current_cx + dx, current_cy + dy))

        # 生成缺失的區塊
        for chunk_coord in needed_chunks:
            if chunk_coord not in self.active_chunks:
                self.active_chunks[chunk_coord] = self._create_default_chunk(*chunk_coord)

        # 更新要繪製的區塊清單 (為了效能，每次 draw 只畫在視野內的)
        self.visible_chunks = [self.active_chunks[c] for c in needed_chunks if c in self.active_chunks]

    def draw(self):
        """繪製所有可見的區塊。應該在 on_draw 中呼叫。"""
        for chunk_sprites in self.visible_chunks:
            chunk_sprites.draw()