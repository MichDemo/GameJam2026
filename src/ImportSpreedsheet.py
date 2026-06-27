from ursina import *

# Ostre piksele dla pixel artu
Texture.default_filtering = 'nearest'

class Block(Entity):
    # Definiujemy rozmiar siatki spritesheeta (np. 4 kolumny na 4 wiersze)
    GRID_SIZE = 4
    TILE_SIZE = 1.0 / GRID_SIZE # 0.25

    def __init__(self, position, tile_x=0, tile_y=0):
        super().__init__(
            model='quad',  # Płaski model idealny do gier 2D
            texture='assets/textures/SEWER_SPRITESHEET.png', # ścieżka z obraz.png
            position=position,
            scale=(1, 1), # Rozmiar bloku w świecie gry
            
            # Skalujemy teksturę do rozmiaru jednego kafelka
            texture_scale=(self.TILE_SIZE, self.TILE_SIZE),
            
            # Przesuwamy okno na konkretny kafelek (tile_x, tile_y)
            texture_offset=(tile_x * self.TILE_SIZE, tile_y * self.TILE_SIZE),
            
            collider='box' # Jeśli postać ma na nim stawać
        )