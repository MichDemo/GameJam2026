from ursina import *
import json
import math
import os
import tkinter as tk
from tkinter import filedialog, simpledialog

from Block import Block


class EditorObject(Entity):
    # Konfiguracja Twojego spritesheeta (4x3 kafelki)
    GRID_WIDTH = 4
    GRID_HEIGHT = 3

    def __init__(
        self,
        editor_type,
        position=(0, 0),
        size=(1, 1),
        hex_color="#ffffff",
        tile_x=0,        # Domyślna kolumna kafelka
        tile_y=0,        # Domyślny wiersz kafelka
        **kwargs
    ):
        self.editor_type = editor_type
        self.hex_color = self.normalize_hex(hex_color)
        
        # Zapisujemy informacje o wybranym kafelku bezpośrednio w obiekcie edytora
        self.tile_x = tile_x
        self.tile_y = tile_y

        # Pobieramy kolor z HEX
        visual_color = self.hex_to_ursina_color(self.hex_color)

        super().__init__(
            parent=scene,
            model="quad",
            position=(position[0], position[1], 0),
            scale=(size[0], size[1], 1),
            color=visual_color,  # Ten kolor nałoży się jako filtr/zabarwienie na teksturę!
            collider="box",
            **kwargs
        )

        # Jeśli tworzony obiekt to blok, nakładamy na niego spritesheet
        if self.editor_type == "block":
            self.texture = Texture('../assets/textures/SEWER_SPRITESHEET.png')
            # Aktualizujemy skalowanie i pozycję tekstury (żeby się ładnie kafelkowała)
            self.update_texture_mapping()

        self.rarity = "Common"
        self.speed = 5
        self.zone1 = 1.0
        self.zone2 = 3.0
        self.zone3 = 6.0
        self.rotation_time = 4.0
        self.vent_id = None
        self.target_vent_id = None
        self.vent_pair_id = None

        self.label = None
        self.create_label()

    def update_texture_mapping(self):
        """Metoda dbająca o to, by tekstura kafelkowała się przy zmianie skali bloku"""
        if self.editor_type == "block":
            step_x = 1.0 / self.GRID_WIDTH
            step_y = 1.0 / self.GRID_HEIGHT

            # Kafelkowanie: mnożymy rozmiar kafelka przez aktualną skalę obiektu w edytorze
            self.texture_scale = (step_x * self.scale_x, step_y * self.scale_y)
            # Przesunięcie na wybrany kafelek
            self.texture_offset = (self.tile_x * step_x, self.tile_y * step_y)

    def change_tile(self, tx, ty):
        """Funkcja, którą możesz wywołać w edytorze, aby zmienić kafelek zaznaczonego bloku"""
        self.tile_x = tx
        self.tile_y = ty
        self.update_texture_mapping()

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
        value = EditorObject.normalize_hex(hex_value)
        r = int(value[1:3], 16)
        g = int(value[3:5], 16)
        b = int(value[5:7], 16)
        return color.rgb(r, g, b)

    def set_hex_color(self, hex_value):
        self.hex_color = self.normalize_hex(hex_value)
        # Ursina automatycznie przemnoży teksturę przez ten kolor, dając efekt zabarwienia
        self.color = self.hex_to_ursina_color(self.hex_color)

    def create_label(self):
        # Jeśli to blok z teksturą, ukrywamy literkę "B", żeby nie zasłaniała grafiki
        if self.editor_type == "block":
            return
            
        label_text = self.editor_type.upper()[0]
        if self.editor_type == "player": label_text = "P"
        elif self.editor_type == "enemy": label_text = "EN"
        elif self.editor_type == "vent": label_text = "V"
        elif self.editor_type == "fur": label_text = "F"
        elif self.editor_type == "eye": label_text = "EY"

        self.label = Text(
            parent=self, text=label_text, origin=(0, 0),
            scale=8, color=color.black, z=-0.1
        )


class GridLevelEditor:
    SHEET_SIZE = 256
    MAPS_FOLDER = "assets/maps"

    MODE_PLAYER_PLACE = 0

    MODE_BLOCK_PLACE = 1
    MODE_BLOCK_PROPERTIES = 2
    MODE_FUR_PLACE = 3
    MODE_FUR_PROPERTIES = 4
    MODE_ENEMY_PLACE = 5
    MODE_ENEMY_PROPERTIES = 6
    MODE_EYE_PLACE = 7
    MODE_EYE_PROPERTIES = 8
    MODE_VENT_PLACE = 9

    def __init__(
        self,
        save_file="level.json",
        window_title="Grid Level Editor",
        grid_color=color.rgba(255, 255, 255, 120),
        marker_color=color.rgba(255, 255, 255, 90),
        background_color=color.black,
        camera_fov=32,
        min_camera_fov=6,
        max_camera_fov=128
    ):
        self.app = Ursina()

        window.title = window_title
        window.color = background_color
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = True
        window.fps_counter.enabled = True

        os.makedirs(self.MAPS_FOLDER, exist_ok=True)

        self.save_file = save_file
        self.grid_color = grid_color
        self.marker_color = marker_color

        self.grid_width = self.SHEET_SIZE
        self.grid_height = self.SHEET_SIZE
        self.cell_size = 1

        self.player_spawn = None

        self.blocks = []
        self.furs = []
        self.enemies = []
        self.eyes = []
        self.vents = []

        self.next_vent_id = 1
        self.next_vent_pair_id = 1
        self.pending_vent = None

        self.grid_entity = None
        self.sheet_border_entity = None

        self.show_grid = True
        self.show_marker = True

        self.current_mode = self.MODE_BLOCK_PLACE

        self.min_camera_fov = min_camera_fov
        self.max_camera_fov = max_camera_fov

        self.dragged_object = None
        self.drag_offset = Vec2(0, 0)

        camera.orthographic = True
        camera.fov = camera_fov
        camera.position = (128, 128, -20)
        camera.rotation = (0, 0, 0)
        camera.parent = scene

        self.mouse_plane = Entity(
            parent=scene,
            model="quad",
            position=(128, 128, 1),
            scale=(256, 256, 1),
            color=color.rgba(0, 0, 0, 0),
            collider="box",
            enabled=True
        )

        self.marker = Entity(
            parent=scene,
            model="quad",
            scale=(1, 1, 1),
            color=self.marker_color,
            collider=None,
            z=0.65,
            enabled=True
        )

        self.create_grid_visuals()

        self.input_handler = Entity()
        self.input_handler.input = self.input

        self.update_handler = Entity()
        self.update_handler.update = self.update

        self.help_text = Text(
            text=self.get_shortcut_text(),
            position=(-0.86, 0.46),
            origin=(-0.5, 0.5),
            scale=0.75,
            color=color.white,
            background=True
        )

        self.mode_text = Text(
            text=self.get_mode_name(),
            position=(-0.86, -0.46),
            origin=(-0.5, -0.5),
            scale=0.9,
            color=color.azure,
            background=True
        )

        self.clamp_camera_to_sheet()

    def run(self):
        self.app.run()

    def get_shortcut_text(self):
        return (
            "0: Player placement\n"
            "1: Block placement\n"
            "2: Block properties\n"
            "3: Fur placement\n"
            "4: Fur properties\n"
            "5: Enemy placement\n"
            "6: Enemy properties\n"
            "7: Eye placement\n"
            "8: Eye properties\n"
            "9: Vent placement\n"
            "LMB: place / drag / edit\n"
            "RMB: delete\n"
            "S: save map\n"
            "L: load map\n"
            "G: toggle grid\n"
            "M: toggle marker\n"
            "C: clear map\n"
            "Home: center camera\n"
            "Arrows: move camera\n"
            "Scroll: zoom"
        )

    def get_mode_name(self):
        names = {
            self.MODE_PLAYER_PLACE: "Mode 0: Player placement",
            self.MODE_BLOCK_PLACE: "Mode 1: Block placement",
            self.MODE_BLOCK_PROPERTIES: "Mode 2: Block properties",
            self.MODE_FUR_PLACE: "Mode 3: Fur placement",
            self.MODE_FUR_PROPERTIES: "Mode 4: Fur properties",
            self.MODE_ENEMY_PLACE: "Mode 5: Enemy placement",
            self.MODE_ENEMY_PROPERTIES: "Mode 6: Enemy properties",
            self.MODE_EYE_PLACE: "Mode 7: Eye placement",
            self.MODE_EYE_PROPERTIES: "Mode 8: Eye properties",
            self.MODE_VENT_PLACE: "Mode 9: Vent placement"
        }
        return names.get(self.current_mode, "Unknown mode")

    def set_mode(self, mode):
        self.current_mode = mode
        if self.mode_text:
            self.mode_text.text = self.get_mode_name()

    def ask_text(self, title, prompt, default_value=""):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        result = simpledialog.askstring(title, prompt, initialvalue=default_value, parent=root)
        root.destroy()
        return result

    def ask_open_file(self):
        os.makedirs(self.MAPS_FOLDER, exist_ok=True)
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            initialdir=os.path.abspath(self.MAPS_FOLDER),
            title="Open map JSON",
            filetypes=[("JSON map files", "*.json")]
        )
        root.destroy()
        return file_path

    def parse_vec2(self, text, fallback):
        if text is None: return fallback
        cleaned = str(text).replace("(", "").replace(")", "").replace(";", ",").replace(" ", ",")
        parts = [part for part in cleaned.split(",") if part != ""]
        if len(parts) < 2: return fallback
        try:
            return Vec2(float(parts[0]), float(parts[1]))
        except Exception:
            return fallback

    def parse_float(self, text, fallback):
        try: return float(str(text).strip())
        except Exception: return fallback

    def normalize_hex(self, text):
        if text is None: return "#ffffff"
        value = str(text).strip()
        if not value.startswith("#"): value = "#" + value
        if len(value) != 7: return "#ffffff"
        try:
            int(value[1:3], 16); int(value[3:5], 16); int(value[5:7], 16)
            return value.lower()
        except Exception:
            return "#ffffff"

    def sanitize_file_name(self, text):
        value = str(text).strip()
        if value == "": value = "level"
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            value = value.replace(char, "_")
        if not value.endswith(".json"): value += ".json"
        return value

    def split_csv(self, text):
        if text is None: return []
        return [part.strip() for part in str(text).split(",") if part.strip() != ""]

    def get_sheet_center(self): return Vec2(128, 128)
    def get_camera_aspect_ratio(self):
        try: return window.aspect_ratio
        except Exception: return 16 / 9

    def get_camera_half_view_size(self):
        half_height = camera.fov / 2
        half_width = half_height * self.get_camera_aspect_ratio()
        return Vec2(half_width, half_height)

    def clamp_camera_to_sheet(self):
        half_view = self.get_camera_half_view_size()
        min_x, max_x = half_view.x, 256 - half_view.x
        min_y, max_y = half_view.y, 256 - half_view.y
        center = self.get_sheet_center()
        if min_x > max_x: camera.x = center.x
        else: camera.x = max(min_x, min(camera.x, max_x))
        if min_y > max_y: camera.y = center.y
        else: camera.y = max(min_y, min(camera.y, max_y))
        camera.z = -20

    def center_camera_on_sheet(self):
        camera.x, camera.y, camera.z = 128, 128, -20
        self.clamp_camera_to_sheet()

    def clamp_grid_position(self, grid_x, grid_y):
        return max(0, min(int(grid_x), 255)), max(0, min(int(grid_y), 255))

    def grid_to_world(self, grid_x, grid_y):
        grid_x, grid_y = self.clamp_grid_position(grid_x, grid_y)
        return Vec2(grid_x + 0.5, grid_y + 0.5)

    def world_to_grid(self, world_x, world_y):
        return self.clamp_grid_position(math.floor(world_x), math.floor(world_y))

    def snap_world_position_to_grid(self, position):
        grid_x, grid_y = self.world_to_grid(position.x, position.y)
        return self.grid_to_world(grid_x, grid_y)

    def snap_size_to_grid(self, size):
        return Vec2(max(1, int(round(size.x))), max(1, int(round(size.y))))

    def clamp_center_to_sheet(self, center, size):
        return Vec2(max(size.x / 2, min(center.x, 256 - size.x / 2)), max(size.y / 2, min(center.y, 256 - size.y / 2)))

    def get_mouse_world_2d(self):
        if mouse.world_point is None: return None
        return Vec2(mouse.world_point.x, mouse.world_point.y)

    def get_mouse_snapped_world_position(self):
        mouse_pos = self.get_mouse_world_2d()
        if mouse_pos is None: return None
        return self.snap_world_position_to_grid(mouse_pos)

    def create_grid_visuals(self):
        self.clear_grid_visuals()
        vertices = []
        for x in range(257):
            vertices.append((x, 0, 0)); vertices.append((x, 256, 0))
        for y in range(257):
            vertices.append((0, y, 0)); vertices.append((256, y, 0))

        self.grid_entity = Entity(parent=scene, model=Mesh(vertices=vertices, mode="line", static=True), position=(0, 0, 0.9), color=self.grid_color)
        border_vertices = [(0, 0, 0), (256, 0, 0), (256, 0, 0), (256, 256, 0), (256, 256, 0), (0, 256, 0), (0, 256, 0), (0, 0, 0)]
        self.sheet_border_entity = Entity(parent=scene, model=Mesh(vertices=border_vertices, mode="line", static=True), position=(0, 0, 0.95), color=color.rgba(255, 255, 255, 230))

    def clear_grid_visuals(self):
        if self.grid_entity: destroy(self.grid_entity); self.grid_entity = None
        if self.sheet_border_entity: destroy(self.sheet_border_entity); self.sheet_border_entity = None

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        if self.grid_entity: self.grid_entity.enabled = self.show_grid
        if self.sheet_border_entity: self.sheet_border_entity.enabled = self.show_grid

    def get_all_editor_objects(self):
        objects = []
        if self.player_spawn: objects.append(self.player_spawn)
        objects.extend(self.blocks)
        objects.extend(self.furs)
        objects.extend(self.enemies)
        objects.extend(self.eyes)
        objects.extend(self.vents)
        return objects

    def get_object_under_mouse(self):
        mouse_pos = self.get_mouse_world_2d()
        if mouse_pos is None: return None
        for obj in reversed(self.get_all_editor_objects()):
            if (obj.x - obj.scale_x / 2) <= mouse_pos.x <= (obj.x + obj.scale_x / 2) and (obj.y - obj.scale_y / 2) <= mouse_pos.y <= (obj.y + obj.scale_y / 2):
                return obj
        return None

    def remove_object(self, obj):
        if obj == self.player_spawn:
            destroy(self.player_spawn); self.player_spawn = None
            return
        for collection in [self.blocks, self.furs, self.enemies, self.eyes, self.vents]:
            if obj in collection: collection.remove(obj); break
        if obj == self.pending_vent: self.pending_vent = None
        if getattr(obj, "editor_type", None) == "vent": self.rebuild_vent_connections_after_delete(obj)
        destroy(obj)

    def clear_map(self):
        for obj in list(self.get_all_editor_objects()): destroy(obj)
        self.player_spawn = None
        self.blocks.clear(); self.furs.clear(); self.enemies.clear(); self.eyes.clear(); self.vents.clear()
        self.pending_vent = None; self.next_vent_id = 1; self.next_vent_pair_id = 1

    def create_player_spawn(self, position):
        snapped = self.snap_world_position_to_grid(position)
        if self.player_spawn: self.player_spawn.position = (snapped.x, snapped.y, 0.2); return self.player_spawn
        self.player_spawn = EditorObject(editor_type="player", position=(snapped.x, snapped.y), size=(1, 1), hex_color="#ffa500", z=0.2)
        return self.player_spawn

    # Zaktualizowana metoda tworzenia Bloku o tile_x oraz tile_y
    def create_block(self, position, size=(1, 1), hex_color="#44aa44", tile_x=0, tile_y=0):
        if not isinstance(position, Vec2): position = Vec2(position[0], position[1])
        if not isinstance(size, Vec2): size = Vec2(size[0], size[1])

        snapped_size = self.snap_size_to_grid(size)
        snapped_position = self.snap_world_position_to_grid(position)
        clamped_position = self.clamp_center_to_sheet(snapped_position, snapped_size)

        # Wywołujemy naszą klasę Block ze spritesheetem
        block = Block(
            position=(clamped_position.x, clamped_position.y),
            size=(snapped_size.x, snapped_size.y),
            hex_color=hex_color,
            tile_x=tile_x,
            tile_y=tile_y
        )
        block.editor_type = "block"
        block.z = 0
        self.blocks.append(block)
        return block

    def create_fur(self, position, rarity="Common", hex_color="#8b5a2b"):
        snapped = self.snap_world_position_to_grid(position)
        fur = EditorObject(editor_type="fur", position=(snapped.x, snapped.y), size=(1, 1), hex_color=hex_color, z=0.1)
        fur.rarity = rarity
        self.furs.append(fur)
        return fur

    def create_enemy(self, position):
        snapped = self.snap_world_position_to_grid(position)
        enemy = EditorObject(editor_type="enemy", position=(snapped.x, snapped.y), size=(1, 1), hex_color="#ff0000", z=0.12)
        enemy.speed, enemy.zone1, enemy.zone2, enemy.zone3 = 5, 1.0, 3.0, 6.0
        self.enemies.append(enemy)
        return enemy

    def create_eye(self, position):
        snapped = self.snap_world_position_to_grid(position)
        eye = EditorObject(editor_type="eye", position=(snapped.x, snapped.y), size=(1, 1), hex_color="#ffaaaa", z=0.13)
        eye.rotation_time = 4.0
        self.eyes.append(eye)
        return eye

    def create_vent(self, position):
        snapped = self.snap_world_position_to_grid(position)
        vent = EditorObject(editor_type="vent", position=(snapped.x, snapped.y), size=(1, 1), hex_color="#555555", z=0.14)
        vent.vent_id = self.next_vent_id
        self.next_vent_id += 1
        self.vents.append(vent)

        if self.pending_vent is None:
            self.pending_vent = vent
            vent.vent_pair_id = self.next_vent_pair_id
            vent.target_vent_id = None
            vent.color = color.rgb(90, 90, 90)
        else:
            first = self.pending_vent
            second = vent
            first.vent_pair_id = second.vent_pair_id = self.next_vent_pair_id
            first.target_vent_id, second.target_vent_id = second.vent_id, first.vent_id
            first.color = second.color = color.rgb(80, 160, 255)
            self.pending_vent = None
            self.next_vent_pair_id += 1
        return vent

    def rebuild_vent_connections_after_delete(self, deleted_vent):
        for vent in self.vents:
            if vent.target_vent_id == deleted_vent.vent_id:
                vent.target_vent_id = None
                vent.color = color.rgb(90, 90, 90)
                self.pending_vent = vent

    def open_block_properties_dialog(self, block):
        current_tx = getattr(block, 'tile_x', 0)
        current_ty = getattr(block, 'tile_y', 0)
        result = self.ask_text(
            "Block properties",
            "Format:\nhex_color, scale_x, scale_y, tile_x, tile_y\n\nPodpowiedź kafelków (od lewego dołu):\nSkrzynia: 0,0 | Rura: 0,1 | Zielone cegły: 1,2",
            f"{getattr(block, 'hex_color', '#ffffff')}, {int(block.scale_x)}, {int(block.scale_y)}, {current_tx}, {current_ty}"
        )
        if result is None: return
        parts = self.split_csv(result)

        hex_color = self.normalize_hex(parts[0]) if len(parts) >= 1 else getattr(block, "hex_color", "#ffffff")
        scale_x = self.parse_float(parts[1], block.scale_x) if len(parts) >= 2 else block.scale_x
        scale_y = self.parse_float(parts[2], block.scale_y) if len(parts) >= 3 else block.scale_y
        tile_x = int(self.parse_float(parts[3], current_tx)) if len(parts) >= 4 else current_tx
        tile_y = int(self.parse_float(parts[4], current_ty)) if len(parts) >= 5 else current_ty

        size = self.snap_size_to_grid(Vec2(scale_x, scale_y))
        center = self.clamp_center_to_sheet(Vec2(block.x, block.y), size)

        block.tile_x = tile_x
        block.tile_y = tile_y
        
        if hasattr(block, "set_hex_color"):
            block.set_hex_color(hex_color)
        else:
            block.hex_color = hex_color
            block.color = EditorObject.hex_to_ursina_color(hex_color)

        if hasattr(block, "set_size_cells"):
            block.set_size_cells(size.x, size.y)
        else:
            block.scale = (size.x, size.y, 1)

        block.position = (center.x, center.y, 0)
        
        # Ostateczne odświeżenie pozycji wyciętego kafelka na żywo
        if hasattr(block, "update_tile_mapping"):
            block.update_tile_mapping()
    def open_block_create_dialog(self, position):
        result = self.ask_text(
            "Create block",
            "Format:\nhex_color, scale_x, scale_y, tile_x, tile_y\n\nKafelek (0-3 w poziomie, 0-2 w pionie)\nPrzykład:\n#ffffff, 1, 1, 1, 2",
            "#ffffff, 1, 1, 0, 0"
        )
        if result is None: return
        parts = self.split_csv(result)

        hex_color = self.normalize_hex(parts[0]) if len(parts) >= 1 else "#ffffff"
        scale_x = self.parse_float(parts[1], 1) if len(parts) >= 2 else 1
        scale_y = self.parse_float(parts[2], 1) if len(parts) >= 3 else 1
        tile_x = int(self.parse_float(parts[3], 0)) if len(parts) >= 4 else 0
        tile_y = int(self.parse_float(parts[4], 0)) if len(parts) >= 5 else 0

        self.create_block(
            position=position,
            size=Vec2(scale_x, scale_y),
            hex_color=hex_color,
            tile_x=tile_x,
            tile_y=tile_y
        )

    def open_fur_properties_dialog(self, fur):
        result = self.ask_text("Fur properties", "Format:\nrarity, hex_color", f"{getattr(fur, 'rarity', 'Common')}, {getattr(fur, 'hex_color', '#8b5a2b')}")
        if result is None: return
        parts = self.split_csv(result)
        fur.rarity = parts[0] if len(parts) >= 1 else fur.rarity
        fur.set_hex_color(parts[1] if len(parts) >= 2 else fur.hex_color)

    def open_enemy_properties_dialog(self, enemy):
        result = self.ask_text("Enemy properties", "Format:\nsize_x, size_y, hex_color, speed, zone1, zone2, zone3", f"{int(enemy.scale_x)}, {int(enemy.scale_y)}, {enemy.hex_color}, {enemy.speed}, {enemy.zone1}, {enemy.zone2}, {enemy.zone3}")
        if result is None: return
        parts = self.split_csv(result)
        size_x = self.parse_float(parts[0], enemy.scale_x) if len(parts) >= 1 else enemy.scale_x
        size_y = self.parse_float(parts[1], enemy.scale_y) if len(parts) >= 2 else enemy.scale_y
        hex_color = self.normalize_hex(parts[2]) if len(parts) >= 3 else enemy.hex_color
        speed = self.parse_float(parts[3], enemy.speed) if len(parts) >= 4 else enemy.speed
        zone1 = self.parse_float(parts[4], enemy.zone1) if len(parts) >= 5 else enemy.zone1
        zone2 = self.parse_float(parts[5], enemy.zone2) if len(parts) >= 6 else enemy.zone2
        zone3 = self.parse_float(parts[6], enemy.zone3) if len(parts) >= 7 else enemy.zone3

        size = self.snap_size_to_grid(Vec2(size_x, size_y))
        center = self.clamp_center_to_sheet(Vec2(enemy.x, enemy.y), size)
        enemy.scale = (size.x, size.y, 1)
        enemy.position = (center.x, center.y, 0.12)
        enemy.set_hex_color(hex_color)
        enemy.speed, enemy.zone1, enemy.zone2, enemy.zone3 = speed, zone1, zone2, zone3

    def open_eye_properties_dialog(self, eye):
        result = self.ask_text("Eye properties", "Format:\nrotation_time", str(getattr(eye, "rotation_time", 4.0)))
        if result is None: return
        eye.rotation_time = self.parse_float(result, eye.rotation_time)

    def open_save_dialog(self):
        result = self.ask_text("Save map", "Enter map name:", "level")
        if result is None: return
        file_path = os.path.join(self.MAPS_FOLDER, self.sanitize_file_name(result))
        self.save_level(file_path)

    def open_load_dialog(self):
        file_path = self.ask_open_file()
        if file_path: self.load_level(file_path)

    def start_drag_object(self, obj):
        mouse_pos = self.get_mouse_world_2d()
        if mouse_pos is None: return
        self.dragged_object = obj
        self.drag_offset = Vec2(obj.x - mouse_pos.x, obj.y - mouse_pos.y)

    def update_drag_object(self):
        if self.dragged_object is None: return
        if not held_keys["left mouse"]: self.dragged_object = None; self.drag_offset = Vec2(0, 0); return
        mouse_pos = self.get_mouse_world_2d()
        if mouse_pos is None: return
        snapped_position = self.snap_world_position_to_grid(mouse_pos + self.drag_offset)
        clamped_position = self.clamp_center_to_sheet(snapped_position, Vec2(self.dragged_object.scale_x, self.dragged_object.scale_y))
        self.dragged_object.position = (clamped_position.x, clamped_position.y, self.dragged_object.z)

    def object_to_grid_data(self, obj):
        return self.world_to_grid(obj.x, obj.y)

    # Dodanie zapisu parametrów tile_x i tile_y do pliku JSON
    def get_level_data(self):
        player_data = None
        if self.player_spawn:
            gx, gy = self.object_to_grid_data(self.player_spawn)
            player_data = {"grid_x": gx, "grid_y": gy, "x": self.player_spawn.x, "y": self.player_spawn.y}

        blocks_data = []
        for block in self.blocks:
            gx, gy = self.object_to_grid_data(block)
            blocks_data.append({
                "grid_x": gx,
                "grid_y": gy,
                "x": block.x,
                "y": block.y,
                "scale_x": block.scale_x,
                "scale_y": block.scale_y,
                "hex_color": getattr(block, "hex_color", "#ffffff"),
                "tile_x": getattr(block, "tile_x", 0),  # Zapisujemy kolumnę kafelka
                "tile_y": getattr(block, "tile_y", 0)   # Zapisujemy wiersz kafelka
            })

        furs_data = []
        for fur in self.furs:
            gx, gy = self.object_to_grid_data(fur)
            furs_data.append({"grid_x": gx, "grid_y": gy, "x": fur.x, "y": fur.y, "rarity": fur.rarity, "hex_color": fur.hex_color})

        enemies_data = []
        for enemy in self.enemies:
            gx, gy = self.object_to_grid_data(enemy)
            enemies_data.append({"grid_x": gx, "grid_y": gy, "x": enemy.x, "y": enemy.y, "scale_x": enemy.scale_x, "scale_y": enemy.scale_y, "hex_color": enemy.hex_color, "speed": enemy.speed, "zone1": enemy.zone1, "zone2": enemy.zone2, "zone3": enemy.zone3})

        eyes_data = []
        for eye in self.eyes:
            gx, gy = self.object_to_grid_data(eye)
            eyes_data.append({"grid_x": gx, "grid_y": gy, "x": eye.x, "y": eye.y, "rotation_time": eye.rotation_time})

        vents_data = []
        for vent in self.vents:
            gx, gy = self.object_to_grid_data(vent)
            vents_data.append({"vent_id": vent.vent_id, "target_vent_id": vent.target_vent_id, "pair_id": vent.vent_pair_id, "grid_x": gx, "grid_y": gy, "x": vent.x, "y": vent.y})

        return {
            "cell_size": 1, "grid_width": 256, "grid_height": 256,
            "origin": {"x": 0, "y": 0}, "player": player_data,
            "blocks": blocks_data, "furs": furs_data, "enemies": enemies_data, "eyes": eyes_data, "vents": vents_data
        }

    def save_level(self, file_path=None):
        if file_path is None: file_path = os.path.join(self.MAPS_FOLDER, self.save_file)
        os.makedirs(self.MAPS_FOLDER, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(self.get_level_data(), file, indent=4)
        print(f"[GridLevelEditor] Saved map to: {file_path}")

    # Dodanie odczytu parametrów tile_x i tile_y przy wczytywaniu JSON
    def load_level(self, file_path=None):
        if file_path is None: file_path = os.path.join(self.MAPS_FOLDER, self.save_file)
        try:
            with open(file_path, "r", encoding="utf-8") as file: data = json.load(file)
        except FileNotFoundError:
            print(f"[GridLevelEditor] File not found: {file_path}"); return

        self.clear_map()
        player_data = data.get("player")
        if player_data:
            self.create_player_spawn(self.grid_to_world(player_data.get("grid_x", 0), player_data.get("grid_y", 0)))

        for block_data in data.get("blocks", []):
            position = self.grid_to_world(block_data.get("grid_x", 0), block_data.get("grid_y", 0))
            size = Vec2(block_data.get("scale_x", 1), block_data.get("scale_y", 1))
            tx = block_data.get("tile_x", 0)
            ty = block_data.get("tile_y", 0)
            self.create_block(position=position, size=size, hex_color=block_data.get("hex_color", "#ffffff"), tile_x=tx, tile_y=ty)

        for fur_data in data.get("furs", []):
            self.create_fur(self.grid_to_world(fur_data.get("grid_x", 0), fur_data.get("grid_y", 0)), rarity=fur_data.get("rarity", "Common"), hex_color=fur_data.get("hex_color", "#8b5a2b"))

        for enemy_data in data.get("enemies", []):
            enemy = self.create_enemy(self.grid_to_world(enemy_data.get("grid_x", 0), enemy_data.get("grid_y", 0)))
            enemy.scale = (enemy_data.get("scale_x", 1), enemy_data.get("scale_y", 1), 1)
            enemy.set_hex_color(enemy_data.get("hex_color", "#ff0000"))
            enemy.speed = enemy_data.get("speed", 5)
            enemy.zone1, enemy.zone2, enemy.zone3 = enemy_data.get("zone1", 1.0), enemy_data.get("zone2", 3.0), enemy_data.get("zone3", 6.0)

        for eye_data in data.get("eyes", []):
            eye = self.create_eye(self.grid_to_world(eye_data.get("grid_x", 0), eye_data.get("grid_y", 0)))
            eye.rotation_time = eye_data.get("rotation_time", 4.0)

        for vent_data in data.get("vents", []):
            position = self.grid_to_world(vent_data.get("grid_x", 0), vent_data.get("grid_y", 0))
            vent = EditorObject(editor_type="vent", position=(position.x, position.y), size=(1, 1), hex_color="#555555", z=0.14)
            vent.vent_id = vent_data.get("vent_id", self.next_vent_id)
            vent.target_vent_id = vent_data.get("target_vent_id")
            vent.vent_pair_id = vent_data.get("pair_id")
            self.vents.append(vent)
            self.next_vent_id = max(self.next_vent_id, vent.vent_id + 1)

        for vent in self.vents:
            vent.color = color.rgb(80, 160, 255) if vent.target_vent_id is not None else color.rgb(90, 90, 90)
            if vent.target_vent_id is None: self.pending_vent = vent

        if self.vents:
            used_pids = [v.vent_pair_id for v in self.vents if v.vent_pair_id is not None]
            if used_pids: self.next_vent_pair_id = max(used_pids) + 1

        self.clamp_camera_to_sheet()
        print(f"[GridLevelEditor] Loaded map from: {file_path}")

    def update_marker(self):
        if not self.show_marker: self.marker.enabled = False; return
        snapped_pos = self.get_mouse_snapped_world_position()
        if snapped_pos is None: self.marker.enabled = False; return
        self.marker.enabled = True
        self.marker.position = (snapped_pos.x, snapped_pos.y, 0.65)

    def toggle_marker(self):
        self.show_marker = not self.show_marker
        self.marker.enabled = self.show_marker

    def update_camera_controls(self):
        camera_speed = camera.fov * 0.65 * time.dt
        if held_keys["shift"]: camera_speed *= 2
        if held_keys["left arrow"]: camera.x -= camera_speed
        if held_keys["right arrow"]: camera.x += camera_speed
        if held_keys["up arrow"]: camera.y += camera_speed
        if held_keys["down arrow"]: camera.y -= camera_speed
        self.clamp_camera_to_sheet()

    def zoom_camera(self, amount):
        camera.fov = max(self.min_camera_fov, min(camera.fov - amount, self.max_camera_fov))
        self.clamp_camera_to_sheet()

    def handle_left_click(self):
        clicked = self.get_object_under_mouse()
        snapped_pos = self.get_mouse_snapped_world_position()
        if snapped_pos is None: return

        if self.current_mode == self.MODE_PLAYER_PLACE:
            self.start_drag_object(clicked) if clicked else self.create_player_spawn(snapped_pos)
        elif self.current_mode == self.MODE_BLOCK_PLACE:
            self.start_drag_object(clicked) if clicked else self.open_block_create_dialog(snapped_pos)
        elif self.current_mode == self.MODE_BLOCK_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "block": self.open_block_properties_dialog(clicked)
        elif self.current_mode == self.MODE_FUR_PLACE:
            self.start_drag_object(clicked) if clicked else self.create_fur(snapped_pos)
        elif self.current_mode == self.MODE_FUR_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "fur": self.open_fur_properties_dialog(clicked)
        elif self.current_mode == self.MODE_ENEMY_PLACE:
            self.start_drag_object(clicked) if clicked else self.create_enemy(snapped_pos)
        elif self.current_mode == self.MODE_ENEMY_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "enemy": self.open_enemy_properties_dialog(clicked)
        elif self.current_mode == self.MODE_EYE_PLACE:
            self.start_drag_object(clicked) if clicked else self.create_eye(snapped_pos)
        elif self.current_mode == self.MODE_EYE_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "eye": self.open_eye_properties_dialog(clicked)
        elif self.current_mode == self.MODE_VENT_PLACE:
            self.start_drag_object(clicked) if clicked else self.create_vent(snapped_pos)

    def update(self):
        self.update_marker()
        self.update_camera_controls()
        self.update_drag_object()
        self.clamp_camera_to_sheet()

    def input(self, key):
        if key == "scroll up": self.zoom_camera(1)
        if key == "scroll down": self.zoom_camera(-1)
        if key == "0": self.set_mode(self.MODE_PLAYER_PLACE)
        if key == "1": self.set_mode(self.MODE_BLOCK_PLACE)
        if key == "2": self.set_mode(self.MODE_BLOCK_PROPERTIES)
        if key == "3": self.set_mode(self.MODE_FUR_PLACE)
        if key == "4": self.set_mode(self.MODE_FUR_PROPERTIES)
        if key == "5": self.set_mode(self.MODE_ENEMY_PLACE)
        if key == "6": self.set_mode(self.MODE_ENEMY_PROPERTIES)
        if key == "7": self.set_mode(self.MODE_EYE_PLACE)
        if key == "8": self.set_mode(self.MODE_EYE_PROPERTIES)
        if key == "9": self.set_mode(self.MODE_VENT_PLACE)

        if key == "left mouse down": self.handle_left_click()
        if key == "right mouse down":
            clicked = self.get_object_under_mouse()
            if clicked: self.remove_object(clicked)

        if key == "s": self.open_save_dialog()
        if key == "l": self.open_load_dialog()
        if key == "g": self.toggle_grid()
        if key == "m": self.toggle_marker()
        if key == "c": self.clear_map()
        if key == "home": self.center_camera_on_sheet()


GridLevelCreator = GridLevelEditor

if __name__ == "__main__":
    editor = GridLevelEditor(
        save_file="level.json",
        window_title="Grid Level Editor",
        camera_fov=32,
        min_camera_fov=6,
        max_camera_fov=128
    )
    editor.run()