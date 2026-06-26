from ursina import *
import json
import math
import os
import tkinter as tk
from tkinter import filedialog

from Block import Block


class GridLevelCreator:
    SHEET_SIZE = 256
    MAPS_FOLDER = "assets/maps"

    def __init__(
        self,
        save_file="level.json",
        window_title="Grid Level Creator",
        grid_color=color.rgba(255, 255, 255, 120),
        marker_color=color.rgba(255, 255, 255, 90),
        background_color=color.black,
        camera_fov=32,
        min_camera_fov=6,
        max_camera_fov=128
    ):
        # --------------------------------------------------
        # Independent Ursina app
        # --------------------------------------------------

        self.app = Ursina()

        window.title = window_title
        window.color = background_color
        window.borderless = False
        window.fullscreen = False
        window.exit_button.visible = True
        window.fps_counter.enabled = True

        os.makedirs(self.MAPS_FOLDER, exist_ok=True)

        # --------------------------------------------------
        # Hard-coded level sheet
        # --------------------------------------------------

        self.grid_width = self.SHEET_SIZE
        self.grid_height = self.SHEET_SIZE
        self.cell_size = 1

        # Sheet bounds:
        # x = 0..256
        # y = 0..256
        self.origin = Vec2(0, 0)

        self.save_file = save_file

        self.grid_color = grid_color
        self.marker_color = marker_color

        self.blocks = []

        self.player_spawn = None
        self.enemy_spawns = []

        self.grid_entity = None
        self.sheet_border_entity = None

        self.show_grid = True
        self.show_marker = True

        self.min_camera_fov = min_camera_fov
        self.max_camera_fov = max_camera_fov

        # Dragging
        self.dragged_block = None
        self.drag_offset = Vec2(0, 0)

        # Popup state
        self.popup_open = False
        self.popup_root = None

        self.hex_input = None
        self.scale_input = None

        self.save_name_input = None

        self.pending_position = Vec2(0, 0)

        # --------------------------------------------------
        # Camera
        # --------------------------------------------------

        camera.orthographic = True
        camera.fov = camera_fov
        camera.position = (128, 128, -20)
        camera.rotation = (0, 0, 0)
        camera.parent = scene

        # --------------------------------------------------
        # Mouse plane
        # --------------------------------------------------
        # Covers exact 256x256 sheet so mouse.world_point works.

        self.mouse_plane = Entity(
            parent=scene,
            model='quad',
            position=(128, 128, 1),
            scale=(256, 256, 1),
            color=color.rgba(0, 0, 0, 0),
            collider='box',
            enabled=True
        )

        # --------------------------------------------------
        # Cursor marker
        # --------------------------------------------------

        self.marker = Entity(
            parent=scene,
            model='quad',
            scale=(1, 1, 1),
            color=self.marker_color,
            collider=None,
            z=0.65,
            enabled=True
        )

        # --------------------------------------------------
        # Grid
        # --------------------------------------------------

        self.create_grid_visuals()

        # --------------------------------------------------
        # Ursina hooks
        # --------------------------------------------------

        self.input_handler = Entity()
        self.input_handler.input = self.input

        self.update_handler = Entity()
        self.update_handler.update = self.update

        # --------------------------------------------------
        # Shortcut-only helper text
        # --------------------------------------------------

        self.help_text = Text(
            text=(
                "LMB: create / drag block\n"
                "RMB: delete block\n"
                "P: place player spawn\n"
                "E: place enemy spawn\n"
                "S: save map\n"
                "L: load map\n"
                "G: toggle grid\n"
                "M: toggle marker\n"
                "C: clear map\n"
                "Home: center camera\n"
                "Arrows: move camera\n"
                "Scroll: zoom"
            ),
            position=(-0.86, 0.46),
            origin=(-0.5, 0.5),
            scale=0.8,
            color=color.white,
            background=True
        )

        self.clamp_camera_to_sheet()

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def run(self):
        self.app.run()

    # --------------------------------------------------
    # Sheet / camera
    # --------------------------------------------------

    def get_sheet_min_x(self):
        return 0

    def get_sheet_min_y(self):
        return 0

    def get_sheet_max_x(self):
        return 256

    def get_sheet_max_y(self):
        return 256

    def get_sheet_center(self):
        return Vec2(128, 128)

    def clamp_grid_position(self, grid_x, grid_y):
        grid_x = max(0, min(int(grid_x), 255))
        grid_y = max(0, min(int(grid_y), 255))

        return grid_x, grid_y

    def get_camera_aspect_ratio(self):
        try:
            return window.aspect_ratio
        except Exception:
            return 16 / 9

    def get_camera_half_view_size(self):
        half_height = camera.fov / 2
        half_width = half_height * self.get_camera_aspect_ratio()

        return Vec2(half_width, half_height)

    def clamp_camera_to_sheet(self):
        half_view = self.get_camera_half_view_size()

        min_x = self.get_sheet_min_x() + half_view.x
        max_x = self.get_sheet_max_x() - half_view.x

        min_y = self.get_sheet_min_y() + half_view.y
        max_y = self.get_sheet_max_y() - half_view.y

        center = self.get_sheet_center()

        if min_x > max_x:
            camera.x = center.x
        else:
            camera.x = max(min_x, min(camera.x, max_x))

        if min_y > max_y:
            camera.y = center.y
        else:
            camera.y = max(min_y, min(camera.y, max_y))

        camera.z = -20

    def center_camera_on_sheet(self):
        camera.x = 128
        camera.y = 128
        camera.z = -20

        self.clamp_camera_to_sheet()

    # --------------------------------------------------
    # Parsing helpers
    # --------------------------------------------------

    def parse_vec2(self, text, fallback):
        if text is None:
            return fallback

        cleaned = (
            str(text)
            .replace("(", "")
            .replace(")", "")
            .replace(";", ",")
            .replace(" ", ",")
        )

        parts = [part for part in cleaned.split(",") if part != ""]

        if len(parts) < 2:
            return fallback

        try:
            return Vec2(float(parts[0]), float(parts[1]))
        except ValueError:
            return fallback

    def normalize_hex(self, text):
        if text is None:
            return "#ffffff"

        value = str(text).strip()

        if not value.startswith("#"):
            value = "#" + value

        if len(value) != 7:
            return "#ffffff"

        try:
            int(value[1:3], 16)
            int(value[3:5], 16)
            int(value[5:7], 16)

            return value.lower()

        except ValueError:
            return "#ffffff"

    def sanitize_file_name(self, text):
        value = str(text).strip()

        if value == "":
            value = "level"

        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

        for char in invalid_chars:
            value = value.replace(char, "_")

        if not value.endswith(".json"):
            value += ".json"

        return value

    # --------------------------------------------------
    # Grid conversion
    # --------------------------------------------------

    def grid_to_world(self, grid_x, grid_y):
        """
        Cell index -> exact cell center.

        Cell (0, 0):
            bounds: x=0..1, y=0..1
            center: x=0.5, y=0.5

        A block with:
            position=(0.5, 0.5)
            scale=(1, 1, 1)

        fills exactly one cell.
        """

        grid_x, grid_y = self.clamp_grid_position(grid_x, grid_y)

        return Vec2(
            grid_x + 0.5,
            grid_y + 0.5
        )

    def world_to_grid(self, world_x, world_y):
        grid_x = math.floor(world_x)
        grid_y = math.floor(world_y)

        return self.clamp_grid_position(grid_x, grid_y)

    def snap_world_position_to_grid(self, position):
        grid_x, grid_y = self.world_to_grid(position.x, position.y)

        return self.grid_to_world(grid_x, grid_y)

    def snap_size_to_grid(self, size):
        """
        Cell-based size.

        1,1 = one cell
        2,1 = two cells wide, one cell high
        """

        width_cells = max(1, int(round(size.x)))
        height_cells = max(1, int(round(size.y)))

        return Vec2(width_cells, height_cells)

    def clamp_block_center_to_sheet(self, center, size):
        half_width = size.x / 2
        half_height = size.y / 2

        min_x = 0 + half_width
        max_x = 256 - half_width

        min_y = 0 + half_height
        max_y = 256 - half_height

        clamped_x = max(min_x, min(center.x, max_x))
        clamped_y = max(min_y, min(center.y, max_y))

        return Vec2(clamped_x, clamped_y)

    def get_mouse_world_2d(self):
        if mouse.world_point is None:
            return None

        return Vec2(mouse.world_point.x, mouse.world_point.y)

    def get_mouse_snapped_world_position(self):
        mouse_pos = self.get_mouse_world_2d()

        if mouse_pos is None:
            return None

        return self.snap_world_position_to_grid(mouse_pos)

    # --------------------------------------------------
    # Grid visuals
    # --------------------------------------------------

    def create_grid_visuals(self):
        """
        Creates grid as one line mesh.

        Grid lines:
            x = 0..256
            y = 0..256
        """

        self.clear_grid_visuals()

        vertices = []

        for x in range(257):
            vertices.append((x, 0, 0))
            vertices.append((x, 256, 0))

        for y in range(257):
            vertices.append((0, y, 0))
            vertices.append((256, y, 0))

        grid_mesh = Mesh(
            vertices=vertices,
            mode='line',
            static=True
        )

        self.grid_entity = Entity(
            parent=scene,
            model=grid_mesh,
            position=(0, 0, 0.9),
            color=self.grid_color,
            collider=None
        )

        self.create_sheet_border()

    def create_sheet_border(self):
        border_vertices = [
            (0, 0, 0), (256, 0, 0),
            (256, 0, 0), (256, 256, 0),
            (256, 256, 0), (0, 256, 0),
            (0, 256, 0), (0, 0, 0),
        ]

        border_mesh = Mesh(
            vertices=border_vertices,
            mode='line',
            static=True
        )

        self.sheet_border_entity = Entity(
            parent=scene,
            model=border_mesh,
            position=(0, 0, 0.95),
            color=color.rgba(255, 255, 255, 230),
            collider=None
        )

    def clear_grid_visuals(self):
        if self.grid_entity is not None:
            destroy(self.grid_entity)
            self.grid_entity = None

        if self.sheet_border_entity is not None:
            destroy(self.sheet_border_entity)
            self.sheet_border_entity = None

    def toggle_grid(self):
        self.show_grid = not self.show_grid

        if self.grid_entity is not None:
            self.grid_entity.enabled = self.show_grid

        if self.sheet_border_entity is not None:
            self.sheet_border_entity.enabled = self.show_grid

    # --------------------------------------------------
    # Block helpers
    # --------------------------------------------------

    def is_block(self, entity):
        return isinstance(entity, Block)

    def get_block_under_mouse(self):
        mouse_pos = self.get_mouse_world_2d()

        if mouse_pos is None:
            return None

        for block in reversed(self.blocks):
            left = block.x - block.scale_x / 2
            right = block.x + block.scale_x / 2
            bottom = block.y - block.scale_y / 2
            top = block.y + block.scale_y / 2

            if left <= mouse_pos.x <= right and bottom <= mouse_pos.y <= top:
                return block

        return None

    def create_block(self, position, size=(1, 1), hex_color="#44aa44"):
        if not isinstance(position, Vec2):
            position = Vec2(position[0], position[1])

        if not isinstance(size, Vec2):
            size = Vec2(size[0], size[1])

        snapped_size = self.snap_size_to_grid(size)
        snapped_position = self.snap_world_position_to_grid(position)

        clamped_position = self.clamp_block_center_to_sheet(
            snapped_position,
            snapped_size
        )

        block = Block(
            position=(clamped_position.x, clamped_position.y),
            size=(snapped_size.x, snapped_size.y),
            hex_color=hex_color
        )

        # Hard guarantee:
        # 1x1 is exactly one grid cell.
        block.scale = (
            snapped_size.x,
            snapped_size.y,
            1
        )

        block.z = 0

        self.blocks.append(block)

        return block

    def remove_block(self, block):
        if block not in self.blocks:
            return

        self.blocks.remove(block)
        destroy(block)

    def clear_blocks(self):
        for block in list(self.blocks):
            destroy(block)

        self.blocks.clear()

        if self.player_spawn is not None:
            destroy(self.player_spawn)
            self.player_spawn = None

        for enemy_spawn in list(self.enemy_spawns):
            destroy(enemy_spawn)

        self.enemy_spawns.clear()

    def get_solids(self):
        return list(self.blocks)

    # --------------------------------------------------
    # Spawn markers
    # --------------------------------------------------

    def create_player_spawn(self, position):
        snapped = self.snap_world_position_to_grid(position)

        if self.player_spawn is not None:
            self.player_spawn.position = (snapped.x, snapped.y, 0.3)
            return self.player_spawn

        self.player_spawn = Entity(
            parent=scene,
            model='quad',
            position=(snapped.x, snapped.y, 0.3),
            scale=(0.75, 0.75, 1),
            color=color.orange,
            collider=None
        )

        Text(
            parent=self.player_spawn,
            text="P",
            origin=(0, 0),
            scale=8,
            color=color.black,
            z=-0.1
        )

        return self.player_spawn

    def create_enemy_spawn(self, position):
        snapped = self.snap_world_position_to_grid(position)

        enemy_spawn = Entity(
            parent=scene,
            model='quad',
            position=(snapped.x, snapped.y, 0.31),
            scale=(0.75, 0.75, 1),
            color=color.red,
            collider=None
        )

        Text(
            parent=enemy_spawn,
            text="E",
            origin=(0, 0),
            scale=8,
            color=color.black,
            z=-0.1
        )

        self.enemy_spawns.append(enemy_spawn)

        return enemy_spawn

    # --------------------------------------------------
    # Block placement popup
    # --------------------------------------------------

    def open_create_popup(self, default_position):
        if self.popup_open:
            return

        snapped_position = self.snap_world_position_to_grid(default_position)

        self.popup_open = True
        self.pending_position = snapped_position

        self.popup_root = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(20, 20, 20, 245),
            scale=(0.86, 0.52, 1),
            position=(0, 0, -20),
            collider=None
        )

        Text(
            parent=self.popup_root,
            text="Create a block",
            position=(-0.38, 0.21, -1),
            scale=1.45,
            color=color.azure
        )

        Text(
            parent=self.popup_root,
            text="This window creates one solid block at the selected grid cell.",
            position=(-0.38, 0.155, -1),
            scale=0.72,
            color=color.white
        )

        Text(
            parent=self.popup_root,
            text="Hex color",
            position=(-0.38, 0.055, -1),
            scale=0.85,
            color=color.white
        )

        Text(
            parent=self.popup_root,
            text="Visual color of the block. Example: #44aa44",
            position=(-0.38, 0.015, -1),
            scale=0.62,
            color=color.light_gray
        )

        self.hex_input = InputField(
            parent=self.popup_root,
            default_value="#44aa44",
            position=(0.20, 0.045, -1),
            scale=(0.42, 0.065),
            character_limit=16
        )

        Text(
            parent=self.popup_root,
            text="Scale",
            position=(-0.38, -0.105, -1),
            scale=0.85,
            color=color.white
        )

        Text(
            parent=self.popup_root,
            text="Block size in grid cells. Example: 1,1 or 3,2",
            position=(-0.38, -0.145, -1),
            scale=0.62,
            color=color.light_gray
        )

        self.scale_input = InputField(
            parent=self.popup_root,
            default_value="1,1",
            position=(0.20, -0.115, -1),
            scale=(0.42, 0.065),
            character_limit=32
        )

        Button(
            parent=self.popup_root,
            text="Create",
            color=color.azure,
            position=(-0.18, -0.225, -1),
            scale=(0.24, 0.075),
            on_click=self.confirm_create_popup
        )

        Button(
            parent=self.popup_root,
            text="Cancel",
            color=color.gray,
            position=(0.18, -0.225, -1),
            scale=(0.24, 0.075),
            on_click=self.close_popup
        )

    def close_popup(self):
        if self.popup_root is not None:
            destroy(self.popup_root)

        self.popup_root = None

        self.hex_input = None
        self.scale_input = None
        self.save_name_input = None

        self.popup_open = False

    def confirm_create_popup(self):
        hex_value = self.normalize_hex(self.hex_input.text)

        raw_size = self.parse_vec2(
            self.scale_input.text,
            Vec2(1, 1)
        )

        self.create_block(
            position=self.pending_position,
            size=raw_size,
            hex_color=hex_value
        )

        self.close_popup()

    # --------------------------------------------------
    # Save popup
    # --------------------------------------------------

    def open_save_popup(self):
        if self.popup_open:
            return

        self.popup_open = True

        self.popup_root = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(20, 20, 20, 245),
            scale=(0.76, 0.36, 1),
            position=(0, 0, -20),
            collider=None
        )

        Text(
            parent=self.popup_root,
            text="Save map",
            position=(-0.33, 0.13, -1),
            scale=1.35,
            color=color.azure
        )

        Text(
            parent=self.popup_root,
            text="Enter map name. JSON will be saved into assets/maps.",
            position=(-0.33, 0.055, -1),
            scale=0.7,
            color=color.white
        )

        self.save_name_input = InputField(
            parent=self.popup_root,
            default_value="level",
            position=(0.06, -0.035, -1),
            scale=(0.56, 0.07),
            character_limit=64
        )

        Button(
            parent=self.popup_root,
            text="Save",
            color=color.azure,
            position=(-0.16, -0.145, -1),
            scale=(0.22, 0.075),
            on_click=self.confirm_save_popup
        )

        Button(
            parent=self.popup_root,
            text="Cancel",
            color=color.gray,
            position=(0.16, -0.145, -1),
            scale=(0.22, 0.075),
            on_click=self.close_popup
        )

    def confirm_save_popup(self):
        file_name = self.sanitize_file_name(self.save_name_input.text)
        file_path = os.path.join(self.MAPS_FOLDER, file_name)

        self.save_level(file_path)
        self.close_popup()

    # --------------------------------------------------
    # Dragging
    # --------------------------------------------------

    def start_drag_block(self, block):
        mouse_pos = self.get_mouse_world_2d()

        if mouse_pos is None:
            return

        self.dragged_block = block

        self.drag_offset = Vec2(
            block.x - mouse_pos.x,
            block.y - mouse_pos.y
        )

    def update_drag_block(self):
        if self.dragged_block is None:
            return

        if not held_keys["left mouse"]:
            self.dragged_block = None
            self.drag_offset = Vec2(0, 0)
            return

        mouse_pos = self.get_mouse_world_2d()

        if mouse_pos is None:
            return

        raw_position = mouse_pos + self.drag_offset
        snapped_position = self.snap_world_position_to_grid(raw_position)

        block_size = Vec2(
            self.dragged_block.scale_x,
            self.dragged_block.scale_y
        )

        clamped_position = self.clamp_block_center_to_sheet(
            snapped_position,
            block_size
        )

        self.dragged_block.position = (
            clamped_position.x,
            clamped_position.y,
            0
        )

    # --------------------------------------------------
    # Save / load
    # --------------------------------------------------

    def world_position_to_grid_data(self, x, y):
        return self.world_to_grid(x, y)

    def get_level_data(self):
        blocks_data = []

        for block in self.blocks:
            grid_x, grid_y = self.world_position_to_grid_data(block.x, block.y)

            blocks_data.append({
                "grid_x": grid_x,
                "grid_y": grid_y,
                "x": block.x,
                "y": block.y,
                "scale_x": block.scale_x,
                "scale_y": block.scale_y,
                "hex_color": getattr(block, "hex_color", "#ffffff")
            })

        blocks_data.sort(key=lambda data: (data["grid_y"], data["grid_x"]))

        player_spawn_data = None

        if self.player_spawn is not None:
            player_spawn_data = {
                "x": self.player_spawn.x,
                "y": self.player_spawn.y
            }

        enemy_spawns_data = []

        for enemy_spawn in self.enemy_spawns:
            enemy_spawns_data.append({
                "x": enemy_spawn.x,
                "y": enemy_spawn.y
            })

        return {
            "cell_size": 1,
            "grid_width": 256,
            "grid_height": 256,
            "origin": {
                "x": 0,
                "y": 0
            },
            "player_spawn": player_spawn_data,
            "enemy_spawns": enemy_spawns_data,
            "blocks": blocks_data
        }

    def save_level(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.MAPS_FOLDER, self.save_file)

        os.makedirs(self.MAPS_FOLDER, exist_ok=True)

        data = self.get_level_data()

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        print(f"[GridLevelCreator] Saved map to: {file_path}")

    def open_load_file_dialog(self):
        if self.popup_open:
            return

        os.makedirs(self.MAPS_FOLDER, exist_ok=True)

        root = tk.Tk()
        root.withdraw()

        file_path = filedialog.askopenfilename(
            initialdir=os.path.abspath(self.MAPS_FOLDER),
            title="Open map JSON",
            filetypes=[("JSON map files", "*.json")]
        )

        root.destroy()

        if file_path:
            self.load_level(file_path)

    def load_level(self, file_path=None):
        if file_path is None:
            file_path = os.path.join(self.MAPS_FOLDER, self.save_file)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

        except FileNotFoundError:
            print(f"[GridLevelCreator] File not found: {file_path}")
            return

        self.clear_blocks()

        for block_data in data.get("blocks", []):
            if "grid_x" in block_data and "grid_y" in block_data:
                position = self.grid_to_world(
                    block_data.get("grid_x", 0),
                    block_data.get("grid_y", 0)
                )
            else:
                position = Vec2(
                    block_data.get("x", 0.5),
                    block_data.get("y", 0.5)
                )

            size = Vec2(
                block_data.get("scale_x", 1),
                block_data.get("scale_y", 1)
            )

            hex_color = block_data.get("hex_color", "#ffffff")

            self.create_block(
                position=position,
                size=size,
                hex_color=hex_color
            )

        player_data = data.get("player_spawn", None)

        if player_data is not None:
            self.create_player_spawn(
                Vec2(
                    player_data.get("x", 0.5),
                    player_data.get("y", 0.5)
                )
            )

        for enemy_data in data.get("enemy_spawns", []):
            self.create_enemy_spawn(
                Vec2(
                    enemy_data.get("x", 0.5),
                    enemy_data.get("y", 0.5)
                )
            )

        self.clamp_camera_to_sheet()

        print(f"[GridLevelCreator] Loaded map from: {file_path}")

    # --------------------------------------------------
    # Marker
    # --------------------------------------------------

    def update_marker(self):
        if not self.show_marker or self.popup_open:
            self.marker.enabled = False
            return

        snapped_pos = self.get_mouse_snapped_world_position()

        if snapped_pos is None:
            self.marker.enabled = False
            return

        self.marker.enabled = True
        self.marker.position = (snapped_pos.x, snapped_pos.y, 0.65)
        self.marker.scale = (1, 1, 1)

    def toggle_marker(self):
        self.show_marker = not self.show_marker
        self.marker.enabled = self.show_marker

    # --------------------------------------------------
    # Camera controls
    # --------------------------------------------------

    def update_camera_controls(self):
        if self.popup_open:
            return

        camera_speed = camera.fov * 0.65 * time.dt

        if held_keys["shift"]:
            camera_speed *= 2

        if held_keys["left arrow"]:
            camera.x -= camera_speed

        if held_keys["right arrow"]:
            camera.x += camera_speed

        if held_keys["up arrow"]:
            camera.y += camera_speed

        if held_keys["down arrow"]:
            camera.y -= camera_speed

        self.clamp_camera_to_sheet()

    def zoom_camera(self, amount):
        camera.fov -= amount
        camera.fov = max(self.min_camera_fov, min(camera.fov, self.max_camera_fov))

        self.clamp_camera_to_sheet()

    # --------------------------------------------------
    # Update / input
    # --------------------------------------------------

    def update(self):
        self.update_marker()
        self.update_camera_controls()
        self.update_drag_block()
        self.clamp_camera_to_sheet()

    def input(self, key):
        if key == "scroll up":
            self.zoom_camera(1)

        if key == "scroll down":
            self.zoom_camera(-1)

        # Do not trigger editor shortcuts while popup is open.
        # This allows typing S/L/etc. inside input fields.
        if self.popup_open:
            return

        if key == "left mouse down":
            hovered_block = self.get_block_under_mouse()

            if hovered_block is not None:
                self.start_drag_block(hovered_block)
                return

            snapped_pos = self.get_mouse_snapped_world_position()

            if snapped_pos is not None:
                self.open_create_popup(snapped_pos)

        if key == "right mouse down":
            hovered_block = self.get_block_under_mouse()

            if hovered_block is not None:
                self.remove_block(hovered_block)

        if key == "p":
            snapped_pos = self.get_mouse_snapped_world_position()

            if snapped_pos is not None:
                self.create_player_spawn(snapped_pos)

        if key == "e":
            snapped_pos = self.get_mouse_snapped_world_position()

            if snapped_pos is not None:
                self.create_enemy_spawn(snapped_pos)

        if key == "s":
            self.open_save_popup()

        if key == "l":
            self.open_load_file_dialog()

        if key == "g":
            self.toggle_grid()

        if key == "m":
            self.toggle_marker()

        if key == "c":
            self.clear_blocks()

        if key == "home":
            self.center_camera_on_sheet()


if __name__ == "__main__":
    creator = GridLevelCreator(
        save_file="level.json",
        window_title="Grid Level Creator",
        camera_fov=32,
        min_camera_fov=6,
        max_camera_fov=128
    )

    creator.run()