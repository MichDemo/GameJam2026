from ursina import *
import json
import math
import os
import tkinter as tk
from tkinter import filedialog, simpledialog

from Block import Block

class EditorObject(Entity):
    GRID_WIDTH = 4
    GRID_HEIGHT = 3

    def __init__(
        self,
        editor_type,
        position=(0, 0),
        size=(1, 1),
        hex_color="#ffffff",
        tile_index=0,     
        **kwargs
    ):
        self.editor_type = editor_type
        self.hex_color = self.normalize_hex(hex_color)
        self.tile_index = tile_index
        self.size_x = int(size[0])
        self.size_y = int(size[1])
        self.visual_tiles = []

        visual_color = self.hex_to_ursina_color(self.hex_color)

        super().__init__(
            parent=scene,
            model="quad" if editor_type != "block" else None, # Pusty model dla kontenera bloku
            position=(position[0], position[1], 0),
            scale=(1, 1, 1) if editor_type == "block" else (size[0], size[1], 1),
            color=visual_color,
            **kwargs
        )

        if self.editor_type == "block":
            self.generate_tiles()
            # Kolizja dla edytora, żeby dało się klikać i przeciągać bloczki
            self.collider = BoxCollider(
                self, 
                center=( (self.size_x - 1) / 2, (self.size_y - 1) / 2, 0 ), 
                size=(self.size_x, self.size_y, 1)
            )
        else:
            self.collider = "box"

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

    def generate_tiles(self):
        for tile in self.visual_tiles: destroy(tile)
        self.visual_tiles.clear()

        tx = self.tile_index % self.GRID_WIDTH
        ty = (self.GRID_HEIGHT - 1) - (self.tile_index // self.GRID_WIDTH)

        for x in range(self.size_x):
            for y in range(self.size_y):
                tile = Entity(
                    parent=self,
                    model='quad',
                    texture='../assets/textures/SEWER_SPRITESHEET.png',
                    position=(x, y, -0.01),
                    scale=(1, 1, 1),
                    tileset_size=[self.GRID_WIDTH, self.GRID_HEIGHT],
                    tile_coordinate=(tx, ty)
                )
                self.visual_tiles.append(tile)

    def change_tile(self, index):
        self.tile_index = index
        if self.editor_type == "block":
            tx = index % self.GRID_WIDTH
            ty = (self.GRID_HEIGHT - 1) - (index // self.GRID_WIDTH)
            for tile in self.visual_tiles:
                tile.tile_coordinate = (tx, ty)

    @property
    def scale_x(self): return self.size_x
    @property
    def scale_y(self): return self.size_y

    @staticmethod
    def normalize_hex(hex_value):
        if hex_value is None: return "#ffffff"
        value = str(hex_value).strip()
        if not value.startswith("#"): value = "#" + value
        if len(value) != 7: return "#ffffff"
        try:
            int(value[1:3], 16); int(value[3:5], 16); int(value[5:7], 16)
            return value.lower()
        except Exception: return "#ffffff"

    @staticmethod
    def hex_to_ursina_color(hex_value):
        value = EditorObject.normalize_hex(hex_value)
        return color.rgb(int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))

    def set_hex_color(self, hex_value):
        self.hex_color = self.normalize_hex(hex_value)
        self.color = self.hex_to_ursina_color(self.hex_color)

    def create_label(self):
        if self.editor_type == "block": return
        label_text = {"player": "P", "enemy": "EN", "vent": "V", "fur": "F", "eye": "EY"}.get(self.editor_type, "X")
        self.label = Text(parent=self, text=label_text, origin=(0, 0), scale=8, color=color.black, z=-0.1)

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
    MODE_TILE_PAINT = 10

    def __init__(self, save_file="level.json", window_title="Grid Level Editor", grid_color=color.rgba(255, 255, 255, 120), marker_color=color.rgba(255, 255, 255, 90), background_color=color.black, camera_fov=32, min_camera_fov=6, max_camera_fov=128):
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
        
        # ZMIANA: Pędzel używa teraz jednego indeksu (0 - 11 dla siatki 4x3)
        self.active_tile_index = 0 

        self.min_camera_fov = min_camera_fov
        self.max_camera_fov = max_camera_fov

        self.dragged_object = None
        self.drag_offset = Vec2(0, 0)

        camera.orthographic = True
        camera.fov = camera_fov
        camera.position = (128, 128, -20)
        camera.parent = scene

        self.mouse_plane = Entity(parent=scene, model="quad", position=(128, 128, 1), scale=(256, 256, 1), color=color.rgba(0, 0, 0, 0), collider="box")
        self.marker = Entity(parent=scene, model="quad", scale=(1, 1, 1), color=self.marker_color, z=0.65)

        self.create_grid_visuals()

        self.input_handler = Entity(); self.input_handler.input = self.input
        self.update_handler = Entity(); self.update_handler.update = self.update

        self.help_text = Text(text=self.get_shortcut_text(), position=(-0.86, 0.46), origin=(-0.5, 0.5), scale=0.75, color=color.white, background=True)
        self.mode_text = Text(text=self.get_mode_name(), position=(-0.86, -0.46), origin=(-0.5, -0.5), scale=0.9, color=color.azure, background=True)

        self.clamp_camera_to_sheet()

    def run(self): self.app.run()

    def get_shortcut_text(self):
        return (
            "0: Player placement\n1: Block placement\n2: Block properties\n"
            "3: Fur placement\n4: Fur properties\n5: Enemy placement\n"
            "6: Enemy properties\n7: Eye placement\n8: Eye properties\n"
            "9: Vent placement\nT: Tile painting mode\n"
            "J / K: Change active tile index\n"
            "LMB: place / drag / edit\nRMB: delete\nS: save map\nL: load map\n"
            "G: toggle grid\nM: toggle marker\nC: clear map\nHome: center camera\nArrows: move camera\nScroll: zoom"
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
            self.MODE_VENT_PLACE: "Mode 9: Vent placement",
            self.MODE_TILE_PAINT: f"Mode T: Tile Painting (Active Index: {self.active_tile_index})"
        }
        return names.get(self.current_mode, "Unknown mode")

    def set_mode(self, mode):
        self.current_mode = mode
        if self.mode_text: self.mode_text.text = self.get_mode_name()

    def ask_text(self, title, prompt, default_value=""):
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        result = simpledialog.askstring(title, prompt, initialvalue=default_value, parent=root)
        root.destroy()
        return result

    def ask_open_file(self):
        os.makedirs(self.MAPS_FOLDER, exist_ok=True)
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        path = filedialog.askopenfilename(initialdir=os.path.abspath(self.MAPS_FOLDER), title="Open map JSON", filetypes=[("JSON map files", "*.json")])
        root.destroy()
        return path

    def parse_vec2(self, text, fallback):
        if text is None: return fallback
        cleaned = str(text).replace("(", "").replace(")", "").replace(";", ",").replace(" ", ",")
        parts = [p for p in cleaned.split(",") if p != ""]
        if len(parts) < 2: return fallback
        try: return Vec2(float(parts[0]), float(parts[1]))
        except Exception: return fallback

    def parse_float(self, text, fallback):
        try: return float(str(text).strip())
        except Exception: return fallback

    def normalize_hex(self, text):
        if text is None: return "#ffffff"
        value = str(text).strip()
        if not value.startswith("#"): value = "#" + value
        if len(value) != 7: return "#ffffff"
        try: int(value[1:3], 16); int(value[3:5], 16); int(value[5:7], 16); return value.lower()
        except Exception: return "#ffffff"

    def sanitize_file_name(self, text):
        value = str(text).strip()
        if value == "": value = "level"
        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']: value = value.replace(char, "_")
        if not value.endswith(".json"): value += ".json"
        return value

    def split_csv(self, text):
        if text is None: return []
        return [p.strip() for p in str(text).split(",") if p.strip() != ""]

    def get_camera_half_view_size(self):
        half_h = camera.fov / 2
        return Vec2(half_h * (window.aspect_ratio if hasattr(window, "aspect_ratio") else 16/9), half_h)

    def clamp_camera_to_sheet(self):
        half_view = self.get_camera_half_view_size()
        min_x, max_x = half_view.x, 256 - half_view.x
        min_y, max_y = half_view.y, 256 - half_view.y
        camera.x = 128 if min_x > max_x else max(min_x, min(camera.x, max_x))
        camera.y = 128 if min_y > max_y else max(min_y, min(camera.y, max_y))
        camera.z = -20

    def center_camera_on_sheet(self):
        camera.x, camera.y, camera.z = 128, 128, -20
        self.clamp_camera_to_sheet()

    def clamp_grid_position(self, grid_x, grid_y): return max(0, min(int(grid_x), 255)), max(0, min(int(grid_y), 255))
    def grid_to_world(self, grid_x, grid_y): gx, gy = self.clamp_grid_position(grid_x, grid_y); return Vec2(gx + 0.5, gy + 0.5)
    def world_to_grid(self, world_x, world_y): return self.clamp_grid_position(math.floor(world_x), math.floor(world_y))
    def snap_world_position_to_grid(self, pos): g = self.world_to_grid(pos.x, pos.y); return self.grid_to_world(g[0], g[1])
    def snap_size_to_grid(self, size): return Vec2(max(1, int(round(size.x))), max(1, int(round(size.y))))
    def clamp_center_to_sheet(self, center, size): return Vec2(max(size.x / 2, min(center.x, 256 - size.x / 2)), max(size.y / 2, min(center.y, 256 - size.y / 2)))

    def get_mouse_world_2d(self): return Vec2(mouse.world_point.x, mouse.world_point.y) if mouse.world_point else None
    def get_mouse_snapped_world_position(self): m = self.get_mouse_world_2d(); return self.snap_world_position_to_grid(m) if m else None

    def create_grid_visuals(self):
        self.clear_grid_visuals()
        v = []
        for x in range(257): v.append((x, 0, 0)); v.append((x, 256, 0))
        for y in range(257): v.append((0, y, 0)); v.append((256, y, 0))
        self.grid_entity = Entity(parent=scene, model=Mesh(vertices=v, mode="line", static=True), position=(0, 0, 0.9), color=self.grid_color)
        bv = [(0, 0, 0), (256, 0, 0), (256, 0, 0), (256, 256, 0), (256, 256, 0), (0, 256, 0), (0, 256, 0), (0, 0, 0)]
        self.sheet_border_entity = Entity(parent=scene, model=Mesh(vertices=bv, mode="line", static=True), position=(0, 0, 0.95), color=color.rgba(255, 255, 255, 230))

    def clear_grid_visuals(self):
        if self.grid_entity: destroy(self.grid_entity); self.grid_entity = None
        if self.sheet_border_entity: destroy(self.sheet_border_entity); self.sheet_border_entity = None

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        if self.grid_entity: self.grid_entity.enabled = self.show_grid
        if self.sheet_border_entity: self.sheet_border_entity.enabled = self.show_grid

    def get_all_editor_objects(self):
        objs = []
        if self.player_spawn: objs.append(self.player_spawn)
        objs.extend(self.blocks); objs.extend(self.furs); objs.extend(self.enemies); objs.extend(self.eyes); objs.extend(self.vents)
        return objs

    def get_object_under_mouse(self):
        m = self.get_mouse_world_2d()
        if m is None: return None
        for obj in reversed(self.get_all_editor_objects()):
            if (obj.x - obj.scale_x / 2) <= m.x <= (obj.x + obj.scale_x / 2) and (obj.y - obj.scale_y / 2) <= m.y <= (obj.y + obj.scale_y / 2): return obj
        return None

    def remove_object(self, obj):
        if obj == self.player_spawn: destroy(self.player_spawn); self.player_spawn = None; return
        for coll in [self.blocks, self.furs, self.enemies, self.eyes, self.vents]:
            if obj in coll: coll.remove(obj); break
        if obj == self.pending_vent: self.pending_vent = None
        if getattr(obj, "editor_type", None) == "vent": self.rebuild_vent_connections_after_delete(obj)
        destroy(obj)

    def clear_map(self):
        for obj in list(self.get_all_editor_objects()): destroy(obj)
        self.player_spawn = None
        self.blocks.clear(); self.furs.clear(); self.enemies.clear(); self.eyes.clear(); self.vents.clear()
        self.pending_vent = None; self.next_vent_id = 1; self.next_vent_pair_id = 1

    def create_player_spawn(self, pos):
        snapped = self.snap_world_position_to_grid(pos)
        if self.player_spawn: self.player_spawn.position = (snapped.x, snapped.y, 0.2); return self.player_spawn
        self.player_spawn = EditorObject(editor_type="player", position=(snapped.x, snapped.y), size=(1, 1), hex_color="#ffa500", z=0.2)
        return self.player_spawn

    # ZMIANA: create_block przyjmuje teraz liniowy tile_index
    def create_block(self, position, size=(1, 1), hex_color="#ffffff", tile_index=0):
        if not isinstance(position, Vec2): position = Vec2(position[0], position[1])
        if not isinstance(size, Vec2): size = Vec2(size[0], size[1])

        snapped_size = self.snap_size_to_grid(size)
        snapped_position = self.snap_world_position_to_grid(position)
        clamped_position = self.clamp_center_to_sheet(snapped_position, snapped_size)

        # Używamy zaktualizowanej klasy Block, podając tile_index
        block = Block(
            position=(clamped_position.x, clamped_position.y),
            size=(snapped_size.x, snapped_size.y),
            hex_color=hex_color,
            tile_index=tile_index
        )
        block.z = 0
        self.blocks.append(block)
        return block

    def create_fur(self, pos, rarity="Common", hex_color="#8b5a2b"):
        s = self.snap_world_position_to_grid(pos)
        fur = EditorObject(editor_type="fur", position=(s.x, s.y), size=(1, 1), hex_color=hex_color, z=0.1)
        fur.rarity = rarity; self.furs.append(fur); return fur

    def create_enemy(self, pos):
        s = self.snap_world_position_to_grid(pos)
        enemy = EditorObject(editor_type="enemy", position=(s.x, s.y), size=(1, 1), hex_color="#ff0000", z=0.12)
        enemy.speed, enemy.zone1, enemy.zone2, enemy.zone3 = 5, 1.0, 3.0, 6.0
        self.enemies.append(enemy); return enemy

    def create_eye(self, pos):
        s = self.snap_world_position_to_grid(pos)
        eye = EditorObject(editor_type="eye", position=(s.x, s.y), size=(1, 1), hex_color="#ffaaaa", z=0.13)
        eye.rotation_time = 4.0; self.eyes.append(eye); return eye

    def create_vent(self, pos):
        s = self.snap_world_position_to_grid(pos)
        vent = EditorObject(editor_type="vent", position=(s.x, s.y), size=(1, 1), hex_color="#555555", z=0.14)
        vent.vent_id = self.next_vent_id; self.next_vent_id += 1; self.vents.append(vent)
        if self.pending_vent is None:
            self.pending_vent = vent; vent.vent_pair_id = self.next_vent_pair_id; vent.target_vent_id = None; vent.color = color.rgb(90, 90, 90)
        else:
            first = self.pending_vent; second = vent
            first.vent_pair_id = second.vent_pair_id = self.next_vent_pair_id
            first.target_vent_id, second.target_vent_id = second.vent_id, first.vent_id
            first.color = second.color = color.rgb(80, 160, 255)
            self.pending_vent = None; self.next_vent_pair_id += 1
        return vent

    def rebuild_vent_connections_after_delete(self, deleted_vent):
        for vent in self.vents:
            if vent.target_vent_id == deleted_vent.vent_id: vent.target_vent_id = None; vent.color = color.rgb(90, 90, 90); self.pending_vent = vent

    def open_block_properties_dialog(self, block):
        # Formularz: hex, scale_x, scale_y, tile_index, has_collision(1/0)
        result = self.ask_text(
            "Block properties",
            "Format:\nhex, scale_x, scale_y, tile_index, has_collision(1 or 0)",
            f"{block.hex_color}, {int(block.scale_x)}, {int(block.scale_y)}, {block.tile_index}, {int(block.has_collision)}"
        )
        if result is None: return
        parts = self.split_csv(result)
        
        collision_val = int(parts[4]) if len(parts) >= 5 else 1
        block.has_collision = (collision_val == 1)
        
        # Jeśli zmieniliśmy kolizję, przebudowujemy collider
        if block.has_collision:
            # Obliczamy poprawne parametry zamiast ...
            center_x = (block.scale_x - 1) / 2
            center_y = (block.scale_y - 1) / 2
            block.collider = BoxCollider(block, center=(center_x, center_y, 0), size=(block.scale_x, block.scale_y, 1))
        else:
            block.collider = None

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
        enemy.scale = (size.x, size.y, 1); enemy.position = (center.x, center.y, 0.12); enemy.set_hex_color(hex_color)
        enemy.speed, enemy.zone1, enemy.zone2, enemy.zone3 = speed, zone1, zone2, zone3

    def open_eye_properties_dialog(self, eye):
        result = self.ask_text("Eye properties", "Format:\nrotation_time", str(getattr(eye, "rotation_time", 4.0)))
        if result is None: return
        eye.rotation_time = self.parse_float(result, eye.rotation_time)

    def open_save_dialog(self):
        result = self.ask_text("Save map", "Enter map name:", "level")
        if result is None: return
        self.save_level(os.path.join(self.MAPS_FOLDER, self.sanitize_file_name(result)))

    def open_load_dialog(self):
        path = self.ask_open_file()
        if path: self.load_level(path)

    def start_drag_object(self, obj):
        m = self.get_mouse_world_2d()
        if m is None: return
        self.dragged_object = obj; self.drag_offset = Vec2(obj.x - m.x, obj.y - m.y)

    def update_drag_object(self):
        if self.dragged_object is None: return
        if not held_keys["left mouse"]: self.dragged_object = None; self.drag_offset = Vec2(0, 0); return
        m = self.get_mouse_world_2d()
        if m is None: return
        s = self.snap_world_position_to_grid(m + self.drag_offset)
        c = self.clamp_center_to_sheet(s, Vec2(self.dragged_object.scale_x, self.dragged_object.scale_y))
        self.dragged_object.position = (c.x, c.y, self.dragged_object.z)

    def object_to_grid_data(self, obj): return self.world_to_grid(obj.x, obj.y)

    # ZMIANA: get_level_data zapisuje teraz "tile_index" zamiast "tile_x"/"tile_y"
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
                "tile_indices": block.tile_indices,  # ZAPISUJEMY LISTĘ
                "has_collision": block.has_collision  # ZAPISUJEMY STAN KOLIZJI
            })

        # ... (reszta danych)
        return {"cell_size": 1, "blocks": blocks_data}

        furs_data = [{"grid_x": self.world_to_grid(f.x, f.y)[0], "grid_y": self.world_to_grid(f.x, f.y)[1], "x": f.x, "y": f.y, "rarity": f.rarity, "hex_color": f.hex_color} for f in self.furs]
        enemies_data = [{"grid_x": self.world_to_grid(e.x, e.y)[0], "grid_y": self.world_to_grid(e.x, e.y)[1], "x": e.x, "y": e.y, "scale_x": e.scale_x, "scale_y": e.scale_y, "hex_color": e.hex_color, "speed": e.speed, "zone1": e.zone1, "zone2": e.zone2, "zone3": e.zone3} for e in self.enemies]
        eyes_data = [{"grid_x": self.world_to_grid(ey.x, ey.y)[0], "grid_y": self.world_to_grid(ey.x, ey.y)[1], "x": ey.x, "y": ey.y, "rotation_time": ey.rotation_time} for ey in self.eyes]
        vents_data = [{"vent_id": v.vent_id, "target_vent_id": v.target_vent_id, "pair_id": v.vent_pair_id, "grid_x": self.world_to_grid(v.x, v.y)[0], "grid_y": self.world_to_grid(v.x, v.y)[1], "x": v.x, "y": v.y} for v in self.vents]

        return {"cell_size": 1, "grid_width": 256, "grid_height": 256, "origin": {"x": 0, "y": 0}, "player": player_data, "blocks": blocks_data, "furs": furs_data, "enemies": enemies_data, "eyes": eyes_data, "vents": vents_data}

    def save_level(self, path=None):
        if path is None: path = os.path.join(self.MAPS_FOLDER, self.save_file)
        os.makedirs(self.MAPS_FOLDER, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: json.dump(self.get_level_data(), f, indent=4)
        print(f"[GridLevelEditor] Saved map to: {path}")

    # ZMIANA: load_level bezbłędnie wczytuje "tile_index" ze struktury JSON
    def load_level(self, path=None):
        if path is None: path = os.path.join(self.MAPS_FOLDER, self.save_file)
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
        except FileNotFoundError: print(f"[GridLevelEditor] File not found: {path}"); return

        self.clear_map()
        p = data.get("player")
        if p: self.create_player_spawn(self.grid_to_world(p.get("grid_x", 0), p.get("grid_y", 0)))

        for b in data.get("blocks", []):
            pos = self.grid_to_world(b.get("grid_x", 0), b.get("grid_y", 0))
            size = (b.get("scale_x", 1), b.get("scale_y", 1))
            
            # 1. Pobierz listę indeksów
            t_indices = b.get("tile_indices", None) 
            if not t_indices and "tile_index" in b:
                t_indices = [b["tile_index"]] * (int(size[0]) * int(size[1]))
            
            # 2. Pobierz stan kolizji (domyślnie True dla kompatybilności)
            has_coll = b.get("has_collision", True)

            # 3. Przekaż has_coll do konstruktora
            block = Block(
                position=pos, 
                size=size, 
                hex_color=b.get("hex_color", "#ffffff"), 
                tile_indices=t_indices,
                has_collision=has_coll # Dodane!
            )
            
            # 4. Jeśli wczytany blok jest bez kolizji, zaktualizuj jego wygląd (przezroczystość)
            if not has_coll:
                block.alpha = 0.6
                
            self.blocks.append(block)

        for fur_data in data.get("furs", []): self.create_fur(self.grid_to_world(fur_data.get("grid_x", 0), fur_data.get("grid_y", 0)), rarity=fur_data.get("rarity", "Common"), hex_color=fur_data.get("hex_color", "#8b5a2b"))
        for ed in data.get("enemies", []):
            enemy = self.create_enemy(self.grid_to_world(ed.get("grid_x", 0), ed.get("grid_y", 0)))
            enemy.scale = (ed.get("scale_x", 1), ed.get("scale_y", 1), 1); enemy.set_hex_color(ed.get("hex_color", "#ff0000")); enemy.speed = ed.get("speed", 5); enemy.zone1, enemy.zone2, enemy.zone3 = ed.get("zone1", 1.0), ed.get("zone2", 3.0), ed.get("zone3", 6.0)
        for ey in data.get("eyes", []): eye = self.create_eye(self.grid_to_world(ey.get("grid_x", 0), ey.get("grid_y", 0))); eye.rotation_time = ey.get("rotation_time", 4.0)
        for vd in data.get("vents", []):
            pos = self.grid_to_world(vd.get("grid_x", 0), vd.get("grid_y", 0))
            vent = EditorObject(editor_type="vent", position=(pos.x, pos.y), size=(1, 1), hex_color="#555555", z=0.14)
            vent.vent_id = vd.get("vent_id", self.next_vent_id); vent.target_vent_id = vd.get("target_vent_id"); vent.vent_pair_id = vd.get("pair_id")
            self.vents.append(vent); self.next_vent_id = max(self.next_vent_id, vent.vent_id + 1)

        for vent in self.vents:
            vent.color = color.rgb(80, 160, 255) if vent.target_vent_id is not None else color.rgb(90, 90, 90)
            if vent.target_vent_id is None: self.pending_vent = vent
        if self.vents:
            pids = [v.vent_pair_id for v in self.vents if v.vent_pair_id is not None]
            if pids: self.next_vent_pair_id = max(pids) + 1

        self.clamp_camera_to_sheet()
        print(f"[GridLevelEditor] Loaded map from: {path}")

    def update_marker(self):
        if not self.show_marker: self.marker.enabled = False; return
        s = self.get_mouse_snapped_world_position()
        if s is None: self.marker.enabled = False; return
        self.marker.enabled = True; self.marker.position = (s.x, s.y, 0.65)

    def toggle_marker(self): self.show_marker = not self.show_marker; self.marker.enabled = self.show_marker

    def update_camera_controls(self):
        # Sprawdzamy stan klawiszy w każdej klatce (to działa płynnie)
        speed = camera.fov * 0.65 * time.dt
        if held_keys["shift"]: speed *= 2
        
        if held_keys["left arrow"]: camera.x -= speed
        if held_keys["right arrow"]: camera.x += speed
        if held_keys["up arrow"]: camera.y += speed
        if held_keys["down arrow"]: camera.y -= speed
        
        self.clamp_camera_to_sheet()

    def zoom_camera(self, amt): camera.fov = max(self.min_camera_fov, min(camera.fov - amt, self.max_camera_fov)); self.clamp_camera_to_sheet()

    def handle_left_click(self):
        clicked = self.get_object_under_mouse()
        snapped_pos = self.get_mouse_snapped_world_position()
        if snapped_pos is None: return

        if self.current_mode == self.MODE_TILE_PAINT:
            clicked = self.get_object_under_mouse()
            if clicked and getattr(clicked, "editor_type", None) == "block":
                m = self.get_mouse_world_2d()
                # Obliczamy lokalną pozycję kliknięcia (0 do size-1)
                rel_x = int(m.x - (clicked.x - clicked.scale_x / 2))
                rel_y = int(m.y - (clicked.y - clicked.scale_y / 2))
                clicked.change_tile_at(rel_x, rel_y, self.active_tile_index)
            return
        elif self.current_mode == self.MODE_BLOCK_PLACE:
            if clicked is not None: self.start_drag_object(clicked)
            else: self.create_block(position=snapped_pos, size=Vec2(1, 1), tile_index=self.active_tile_index)
            return

        if self.current_mode == self.MODE_PLAYER_PLACE: self.start_drag_object(clicked) if clicked else self.create_player_spawn(snapped_pos)
        elif self.current_mode == self.MODE_BLOCK_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "block": self.open_block_properties_dialog(clicked)
        elif self.current_mode == self.MODE_FUR_PLACE: self.start_drag_object(clicked) if clicked else self.create_fur(snapped_pos)
        elif self.current_mode == self.MODE_FUR_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "fur": self.open_fur_properties_dialog(clicked)
        elif self.current_mode == self.MODE_ENEMY_PLACE: self.start_drag_object(clicked) if clicked else self.create_enemy(snapped_pos)
        elif self.current_mode == self.MODE_ENEMY_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "enemy": self.open_enemy_properties_dialog(clicked)
        elif self.current_mode == self.MODE_EYE_PLACE: self.start_drag_object(clicked) if clicked else self.create_eye(snapped_pos)
        elif self.current_mode == self.MODE_EYE_PROPERTIES:
            if clicked and getattr(clicked, "editor_type", None) == "eye": self.open_eye_properties_dialog(clicked)
        elif self.current_mode == self.MODE_VENT_PLACE: self.start_drag_object(clicked) if clicked else self.create_vent(snapped_pos)

    def update(self):
        self.update_marker()
        self.update_camera_controls()
        self.update_drag_object()
        self.clamp_camera_to_sheet()
        
        # LOGIKA MALOWANIA: sprawdzamy, czy w danym miejscu już coś jest
        if self.current_mode == self.MODE_BLOCK_PLACE and held_keys["left mouse"]:
            pos = self.get_mouse_snapped_world_position()
            if pos:
                # Sprawdzamy, czy istnieje już blok w tej konkretnej pozycji gridowej
                # (sprawdzamy, czy jakikolwiek blok ma takie same koordynaty X, Y)
                already_exists = False
                for b in self.blocks:
                    # Zaokrąglamy, bo pozycje mogą być floatami
                    if round(b.x) == round(pos.x) and round(b.y) == round(pos.y):
                        already_exists = True
                        break
                
                # Tworzymy blok tylko wtedy, gdy go tam jeszcze nie ma
                if not already_exists:
                    self.create_block(position=pos, size=Vec2(1, 1), tile_index=self.active_tile_index)

    def input(self, key):
        if key == "scroll up": self.zoom_camera(1)
        elif key == "scroll down": self.zoom_camera(-1)
        
        for i in range(10):
            if key == str(i): self.set_mode(i)
        
        if key == "t": self.set_mode(self.MODE_TILE_PAINT)

        if key == "j":
            self.active_tile_index = max(0, self.active_tile_index - 1)
            if self.current_mode == self.MODE_TILE_PAINT and self.mode_text: self.mode_text.text = self.get_mode_name()
        
        if key == "k" and not held_keys["control"]:
            self.active_tile_index = min(11, self.active_tile_index + 1)
            if self.current_mode == self.MODE_TILE_PAINT and self.mode_text: self.mode_text.text = self.get_mode_name()
        
        if key == "c" and held_keys["control"]: # Np. CTRL + C
            clicked = self.get_object_under_mouse()
            if clicked and getattr(clicked, "editor_type", None) == "block":
                clicked.toggle_collision()
                print(f"Collision set to: {clicked.has_collision}")

        # Obsługa kliknięć
        if key == "left mouse down": 
            self.handle_left_click()
            
        if key == "right mouse down":
            clicked = self.get_object_under_mouse()
            if clicked: 
                self.remove_object(clicked)

        # Reszta klawiszy
        if key == "s": self.open_save_dialog()
        elif key == "l": self.open_load_dialog()
        elif key == "g": self.toggle_grid()
        elif key == "m": self.toggle_marker()
        elif key == "c": self.clear_map()
        elif key == "home": self.center_camera_on_sheet()


GridLevelCreator = GridLevelEditor

if __name__ == "__main__":
    editor = GridLevelEditor(save_file="level.json", window_title="Grid Level Editor", camera_fov=32)
    editor.run()