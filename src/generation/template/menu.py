import arcade
import arcade.gui


# 模擬一個全域設定，儲存音量大小 (0.0 到 1.0)
class GlobalSettings:
    volume = 0.5


class PauseView(arcade.View):
    """
    遊戲暫停視圖 (Pause Menu)
    """

    def __init__(self, game_view: arcade.View):
        super().__init__()
        self.game_view = game_view  # 保存原來的遊戲視圖，以便稍後恢復

        # 初始化 GUI 管理器
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        # 建立一個垂直排列的 Box 來放按鈕
        self.v_box = arcade.gui.UIBoxLayout()

        # 建立按鈕
        resume_button = arcade.gui.UIFlatButton(text="Resume", width=200)
        settings_button = arcade.gui.UIFlatButton(text="Settings", width=200)
        quit_button = arcade.gui.UIFlatButton(text="Exit", width=200)

        # 綁定點擊事件
        resume_button.on_click = self.on_click_resume
        settings_button.on_click = self.on_click_settings
        quit_button.on_click = self.on_click_quit

        # 將按鈕加入 Box，並設定間距
        self.v_box.add(resume_button.with_space_around(bottom=20))
        self.v_box.add(settings_button.with_space_around(bottom=20))
        self.v_box.add(quit_button)

        # 將 Box 置中對齊加入管理器
        self.manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center_x",
                anchor_y="center_y",
                child=self.v_box
            )
        )

    def on_show_view(self):
        """當切換到這個 View 時觸發"""
        arcade.set_background_color((0, 0, 0, 150))  # 半透明黑色背景

    def on_draw(self):
        """繪製畫面"""
        self.clear()

        # 先畫出原本的遊戲畫面 (在背景)
        self.game_view.on_draw()

        # 畫一層半透明遮罩
        arcade.draw_lrtb_rectangle_filled(
            left=0, right=self.window.width,
            top=self.window.height, bottom=0,
            color=(0, 0, 0, 150)
        )

        # 畫出 GUI 按鈕
        self.manager.draw()

    def on_key_press(self, key, modifiers):
        """按下 ESC 恢復遊戲"""
        if key == arcade.key.ESCAPE:
            self.on_click_resume(None)

    def on_click_resume(self, event):
        # 停用目前的 GUI 並切換回遊戲
        self.manager.disable()
        self.window.show_view(self.game_view)

    def on_click_settings(self, event):
        # 切換到設定視圖
        settings_view = SettingsView(self)
        self.manager.disable()
        self.window.show_view(settings_view)

    def on_click_quit(self, event):
        arcade.close_window()


class SettingsView(arcade.View):
    """
    設定視圖 (調整音量)
    """

    # [修正] 將 pause_view 的型別從 arcade.View 改為確切的 PauseView
    def __init__(self, pause_view: PauseView):
        super().__init__()
        self.pause_view = pause_view

        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.v_box = arcade.gui.UIBoxLayout()

        # 顯示當前音量的文字標籤
        self.volume_label = arcade.gui.UILabel(
            text=f"Current Volume: {int(GlobalSettings.volume * 100)}%",
            text_color=arcade.color.WHITE,
            font_size=20
        )

        vol_up_btn = arcade.gui.UIFlatButton(text="+ Volume", width=200)
        vol_down_btn = arcade.gui.UIFlatButton(text="- Volume", width=200)
        back_btn = arcade.gui.UIFlatButton(text="Back", width=200)

        vol_up_btn.on_click = self.on_vol_up
        vol_down_btn.on_click = self.on_vol_down
        back_btn.on_click = self.on_back

        self.v_box.add(self.volume_label.with_space_around(bottom=20))
        self.v_box.add(vol_up_btn.with_space_around(bottom=10))
        self.v_box.add(vol_down_btn.with_space_around(bottom=20))
        self.v_box.add(back_btn)

        self.manager.add(
            arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y", child=self.v_box)
        )

    def on_draw(self):
        self.clear()
        self.pause_view.game_view.on_draw()  # 保持遊戲畫面在最底層
        arcade.draw_lrtb_rectangle_filled(0, self.window.width, self.window.height, 0, (0, 0, 0, 200))
        self.manager.draw()

    def update_label(self):
        self.volume_label.text = f"Current Volume: {int(GlobalSettings.volume * 100)}%"

    def on_vol_up(self, event):
        GlobalSettings.volume = min(1.0, GlobalSettings.volume + 0.1)
        self.update_label()

    def on_vol_down(self, event):
        GlobalSettings.volume = max(0.0, GlobalSettings.volume - 0.1)
        self.update_label()

    def on_back(self, event):
        self.manager.disable()
        self.pause_view.manager.enable()  # 重新啟用暫停選單的按鈕
        self.window.show_view(self.pause_view)