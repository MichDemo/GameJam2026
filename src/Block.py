from ursina import *

# Ostre piksele dla pixel artu
Texture.default_filtering = 'nearest'

class Block(Entity):
    GRID_WIDTH = 4
    GRID_HEIGHT = 3

    def __init__(self, position=(0, 0), size=(1, 1), hex_color="#ffffff", tile_indices=None, has_collision=True, **kwargs):
        self.hex_color = hex_color
        self.size_x = int(size[0])
        self.size_y = int(size[1])
        
        self.tile_indices = tile_indices if tile_indices else [0] * (self.size_x * self.size_y)
        self.has_collision = has_collision 
        self.visual_tiles = []
        
        super().__init__(position=position, scale=(1, 1, 1), **kwargs)

        self.generate_tiles()
        self.update_collider() # Inicjalizacja kolizji
        
        self.editor_type = "block"

    def update_collider(self):
        """Metoda tworząca lub usuwająca collider w zależności od flagi has_collision."""
        if self.has_collision:
            if not self.collider:
                self.collider = BoxCollider(
                    self, 
                    center=((self.size_x - 1) / 2, (self.size_y - 1) / 2, 0), 
                    size=(self.size_x, self.size_y, 1)
                )
            self.alpha = 1.0 # Pełna widoczność dla kolizyjnych
        else:
            self.collider = None
            self.alpha = 0.6 # Półprzezroczystość dla dekoracji (duchów)

    def toggle_collision(self):
        """Przełącznik stanu kolizji."""
        self.has_collision = not self.has_collision
        self.update_collider()

    def generate_tiles(self):
        for tile in self.visual_tiles: destroy(tile)
        self.visual_tiles.clear()

        for i, idx in enumerate(self.tile_indices):
            x = i % self.size_x
            y = i // self.size_x
            
            tx = idx % self.GRID_WIDTH
            ty = (self.GRID_HEIGHT - 1) - (idx // self.GRID_WIDTH)

            tile = Entity(
                parent=self,
                model='quad',
                texture='../assets/textures/SEWER_SPRITESHEET.png',
                position=(x, y, 0),
                scale=(1, 1, 1),
                tileset_size=[self.GRID_WIDTH, self.GRID_HEIGHT],
                tile_coordinate=(tx, ty)
            )
            self.visual_tiles.append(tile)

    def change_tile_at(self, local_x, local_y, index):
        if 0 <= local_x < self.size_x and 0 <= local_y < self.size_y:
            flat_index = local_x + (local_y * self.size_x)
            self.tile_indices[flat_index] = index
            self.generate_tiles()

    @property
    def scale_x(self): return self.size_x
    @property
    def scale_y(self): return self.size_y