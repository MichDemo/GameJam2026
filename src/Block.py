from ursina import *

# Ostre piksele dla pixel artu
Texture.default_filtering = 'nearest'

class Block(Entity):
    GRID_WIDTH = 4
    GRID_HEIGHT = 3

    def __init__(self, position=(0, 0), size=(1, 1), hex_color="#ffffff", tile_index=0, **kwargs):
        self.hex_color = hex_color
        self.tile_index = tile_index
        self.size_x = int(size[0])
        self.size_y = int(size[1])
        
        # Lista przechowująca wizualne kafelki 1x1 wewnątrz tego bloku
        self.visual_tiles = []

        # Tworzymy główny obiekt (pusty model/kontener), który trzyma pozycję i collider
        super().__init__(
            position=(position[0], position[1], 0),
            scale=(1, 1, 1), # Skala rodzica zostaje 1x1, żeby pod-obiekty nie były deformowane
            color=color.white,
            **kwargs
        )

        # Generujemy kafelki 1x1 w strukturze siatki
        self.generate_tiles()

        self.editor_type = "block"
        
        # Jedna wspólna, duża kolizja na całą wielkość bloku (przesunięta odpowiednio)
        # Ponieważ pivot w Ursinie dla quada jest na środku, wyliczamy idealny box kolizji:
        self.collider = BoxCollider(
            self, 
            center=( (self.size_x - 1) / 2, (self.size_y - 1) / 2, 0 ), 
            size=(self.size_x, self.size_y, 1)
        )

    def generate_tiles(self):
        """Czyści stare i generuje siatkę pojedynczych kafelków 1x1 na podstawie rozmiaru bloku"""
        for tile in self.visual_tiles:
            destroy(tile)
        self.visual_tiles.clear()

        # Przeliczamy koordynaty ze spritesheeta
        tx = self.tile_index % self.GRID_WIDTH
        ty = (self.GRID_HEIGHT - 1) - (self.tile_index // self.GRID_WIDTH)

        # Pętla generująca kafelki 1x1
        for x in range(self.size_x):
            for y in range(self.size_y):
                tile = Entity(
                    parent=self, # Przypisujemy do głównego bloku jako rodzica
                    model='quad',
                    texture='../assets/textures/SEWER_SPRITESHEET.png',
                    position=(x, y, 0),
                    scale=(1, 1, 1),
                    tileset_size=[self.GRID_WIDTH, self.GRID_HEIGHT],
                    tile_coordinate=(tx, ty)
                )
                self.visual_tiles.append(tile)

    def change_tile(self, index):
        """Metoda wywoływana przez pędzel w edytorze - zmienia teksturę we wszystkich pod-kafelkach"""
        self.tile_index = index
        tx = index % self.GRID_WIDTH
        ty = (self.GRID_HEIGHT - 1) - (index // self.GRID_WIDTH)

        for tile in self.visual_tiles:
            tile.tile_coordinate = (tx, ty)

    # Te właściwości są potrzebne edytorowi, aby prawidłowo zapisywać mapę oraz przesuwać obiekty
    @property
    def scale_x(self): return self.size_x
    @property
    def scale_y(self): return self.size_y