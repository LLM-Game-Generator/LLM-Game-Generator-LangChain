import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.generation.picture_generate import picture_generate

picture_generate('atank', 'an blue tank', [32, 32])    