import arcade
import os
from pathlib import Path


class AssetManager:
    """
    Arcade Asset Manager.
    Provides safe resource loading mechanisms to prevent crashes when files are missing.
    """
    _textures = {}
    _sounds = {}

    @classmethod
    def get_texture(cls, path: str, fallback_color=arcade.color.MAGENTA, width=32, height=32) -> arcade.Texture:
        """
        Safely load a texture. Generates a solid color square if not found.
        """
        if path in cls._textures:
            return cls._textures[path]

        try:
            # [Fix] Use pathlib to handle OS specific separators cleanly
            # and resolve the IDE type hint warning (forces it to be a string)
            safe_path = str(Path(path))

            if not os.path.exists(safe_path):
                raise FileNotFoundError(f"File not found: {safe_path}")

            texture = arcade.load_texture(safe_path)
            cls._textures[path] = texture
            return texture

        except Exception as e:
            print(f"[Resource Warning] Failed to load image: {path}, using fallback. Error: {e}")
            # Dynamically create a solid color texture as a fallback
            fallback_texture = arcade.make_soft_square_texture(width, fallback_color, outer_alpha=255)
            cls._textures[path] = fallback_texture
            return fallback_texture

    @classmethod
    def get_sound(cls, path: str):
        """
        Safely load a sound. Returns None if not found.
        """
        if path in cls._sounds:
            return cls._sounds[path]

        try:
            safe_path = str(Path(path))
            if not os.path.exists(safe_path):
                raise FileNotFoundError(f"File not found: {safe_path}")

            sound = arcade.load_sound(safe_path)
            cls._sounds[path] = sound
            return sound

        except Exception as e:
            print(f"[Resource Warning] Failed to load sound: {path}. Error: {e}")
            cls._sounds[path] = None
            return None

    @classmethod
    def play_sound(cls, path: str, volume: float = 1.0):
        """
        Safely play a sound. Best used with GlobalSettings or config.
        """
        sound = cls.get_sound(path)
        if sound:
            arcade.play_sound(sound, volume=volume)