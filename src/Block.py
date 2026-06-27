from ursina import *

Texture.default_filtering = 'nearest'

class Block(Entity):
    # Twój spritesheet ma układ 4x3
    GRID_WIDTH = 4
    GRID_HEIGHT = 3

    def __init__(
        self,
        position=(0, 0),
        size=(1, 1),
        hex_color=None,
        block_color=color.white,
        tile_x=0,       
        tile_y=0,       
        **kwargs
    ):
        self.hex_color = self.normalize_hex(hex_color) if hex_color else self.color_to_hex(block_color)
        visual_color = self.hex_to_ursina_color(self.hex_color) if hex_color else block_color

        width = float(size[0])
        height = float(size[1])

        # Używamy standardowego modelu 'plane', który w Ursinie jest czystym, płaskim 2D meshem (1x1 wierzchołków)
        # Obracamy go o -90 stopni w osi X, aby patrzył prosto na kamerę ortograficzną edytora
        super().__init__(
            model='plane',
            position=(float(position[0]), float(position[1]), 0),
            scale=(width, height, 1),
            rotation_x=-90,
            color=visual_color,
            **kwargs
        )

        self.tile_x = tile_x
        self.tile_y = tile_y
        
        # Wczytujemy spritesheet
        self.texture = Texture('../assets/textures/SEWER_SPRITESHEET.png')
        
        # Bezpiecznie mapujemy współrzędne UV kafelka
        self.update_tile_mapping()

        # Generujemy kolizor typu box na bazie aktualnej skali encji
        self.collider = 'box'

    def update_tile_mapping(self):
        """Metoda precyzyjnie zmieniająca UV siatki 'plane' bez wywoływania błędów struktury"""
        if not self.model:
            return

        step_x = 1.0 / self.GRID_WIDTH
        step_y = 1.0 / self.GRID_HEIGHT

        # Wyznaczamy granice wyciętego kafelka
        u_min = self.tile_x * step_x
        u_max = u_min + step_x
        v_min = self.tile_y * step_y
        v_max = v_min + step_y

        # Model 'plane' w Ursinie ma dokładnie 4 wierzchołki ułożone w standardowej strukturze
        self.model.uvs = [
            (u_min, v_min),  
            (u_max, v_min),  
            (u_max, v_max),  
            (u_min, v_max)   
        ]
        
        # Odświeżamy geometrię
        self.model.generate()

    @staticmethod
    def normalize_hex(hex_value):
        if hex_value is None: return "#ffffff"
        value = str(hex_value).strip()
        if not value.startswith("#"): value = "#" + value
        if len(value) != 7: return "#ffffff"
        try:
            int(value[1:3], 16); int(value[3:5], 16); int(value[5:7], 16)
        except ValueError: return "#ffffff"
        return value.lower()

    @staticmethod
    def hex_to_ursina_color(hex_value):
        value = Block.normalize_hex(hex_value)
        r = int(value[1:3], 16); g = int(value[3:5], 16); b = int(value[5:7], 16)
        return color.rgb(r, g, b)

    @staticmethod
    def color_to_hex(ursina_color):
        try:
            r = int(max(0, min(1, ursina_color.r)) * 255)
            g = int(max(0, min(1, ursina_color.g)) * 255)
            b = int(max(0, min(1, ursina_color.b)) * 255)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception: return "#ffffff"

    def set_hex_color(self, hex_value):
        self.hex_color = self.normalize_hex(hex_value)
        self.color = self.hex_to_ursina_color(self.hex_color)

    def set_size_cells(self, width_cells, height_cells):
        self.scale = (max(1, int(width_cells)), max(1, int(height_cells)), 1)
        self.collider = 'box'

    def get_size_2d(self): return Vec2(self.scale_x, self.scale_y)
    def get_position_2d(self): return Vec2(self.x, self.y)