import os
import math
from ursina import *
from ursina import color as ursina_color
from Rat import Rat

class Enemy(Rat):
    def __init__(
        self,
        player=None,
        position=(0, 0),
        size=(1, 1),
        color=None,
        speed=5,
        chase_speed=None,
        zone_radii=None,
        zone1=None,
        zone2=None,
        zone3=None,
        fov_degrees=110,
        facing_direction=1,
        use_gravity=True,
        solid_objects=None,
        show_zones=True,
        show_label=False,
        always_chase=False,
        variant="brown",
        **kwargs
    ):
        # Czyszczenie kwargs
        kwargs.pop("player", None)
        kwargs.pop("target", None)
        kwargs.pop("zone_radii", None)
        kwargs.pop("zone1", None)
        kwargs.pop("zone2", None)
        kwargs.pop("zone3", None)
        kwargs.pop("fov_degrees", None)
        kwargs.pop("facing_direction", None)
        kwargs.pop("chase_speed", None)
        kwargs.pop("show_zones", None)
        kwargs.pop("show_label", None)
        kwargs.pop("always_chase", None)
        kwargs.pop("variant", None)

        super().__init__(
            position=position,
            size=size,
            speed=speed,
            use_gravity=use_gravity,
            solid_objects=solid_objects if solid_objects is not None else [],
            auto_find_solids=False,
            **kwargs
        )

        self.model = "quad"
        self.collider = "box"
        self.z = 0.12
        self.player = player
        self.target = player

        # --- OBSŁUGA SPRITESHEET ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        textures_path = os.path.join(project_root, "assets", "textures")
        
        if textures_path not in application.asset_folder.parent.parents:
            application.asset_folder = Path(textures_path)

        sprite_config = {
            "brown":  {"file": "RAT_ENEMY_BROWN",  "cols": 2, "rows": 3, "anim_frames": 6},
            "horror": {"file": "RAT_ENEMY_HORROR", "cols": 3, "rows": 3, "anim_frames": 6},
            "rich":   {"file": "RAT_ENEMY_RICH",   "cols": 2, "rows": 3, "anim_frames": 6},
            "white":  {"file": "RAT_ENEMY_WHITE",  "cols": 3, "rows": 3, "anim_frames": 6}
        }

        config = sprite_config.get(variant, sprite_config["brown"])
        
        self.texture = load_texture(config["file"])
        self.num_cols = config["cols"]
        self.num_rows = config["rows"]
        self.total_frames = config.get("anim_frames", self.num_cols * self.num_rows)
        
        # TO JEST KLUCZOWE:
        self.texture_scale = (1 / self.num_cols, 1 / self.num_rows)
        self.color = color if color is not None else ursina_color.white

        # --- Inicjalizacja reszty ---
        self.base_speed = float(speed)
        self.speed = float(speed)
        self.chase_speed = float(chase_speed) if chase_speed is not None else float(speed)
        self.spawn_point = Vec2(position[0], position[1])
        self.facing_direction = 1 if facing_direction >= 0 else -1
        self.fov = float(fov_degrees)
        
        # Strefy
        if isinstance(zone_radii, (list, tuple)):
            self.zone1, self.zone2, self.zone3 = float(zone_radii[0]), float(zone_radii[1]), float(zone_radii[2])
        else:
            self.zone1 = float(zone1) if zone1 is not None else 1.0
            self.zone2 = float(zone2) if zone2 is not None else 3.0
            self.zone3 = float(zone3) if zone3 is not None else 6.0

        self.current_zone = None
        self.chasing = False
        self.show_zones = show_zones
        self.zone_visuals = []
        
        self.create_zone_visuals()
        self.update_zone_visuals()

    # --------------------------------------------------
    # Solid filtering
    # --------------------------------------------------

    def get_solids(self):
        if self.solid_objects is None:
            return []

        valid_solids = []

        for obj in self.solid_objects:
            if obj is None:
                continue

            if obj is self:
                continue

            if obj == self.player:
                continue

            if getattr(obj, "__class__", None) and obj.__class__.__name__.lower() == "player":
                continue

            if getattr(obj, "editor_type", None) in ("enemy", "eye", "vent", "fur", "player"):
                continue

            if not getattr(obj, "enabled", True):
                continue

            if not hasattr(obj, "collider"):
                continue

            if obj.collider is None:
                continue

            valid_solids.append(obj)

        return valid_solids

    # --------------------------------------------------
    # Player resolving
    # --------------------------------------------------

    def set_player(self, player):
        self.player = player
        self.target = player

    def is_live_player_reference(self, obj):
        if obj is None:
            return False

        if not hasattr(obj, "x") or not hasattr(obj, "y"):
            return False

        if obj.__class__.__name__.lower() == "player":
            return True

        if hasattr(obj, "camera_follow") and hasattr(obj, "jump"):
            return True

        return False

    def resolve_player_if_missing_or_static(self):
        if self.is_live_player_reference(self.player):
            return

        if self.is_live_player_reference(self.target):
            self.player = self.target
            return

        for entity in scene.entities:
            if entity is self:
                continue

            if entity.__class__.__name__.lower() == "player":
                self.set_player(entity)
                return

            if hasattr(entity, "camera_follow") and hasattr(entity, "jump"):
                self.set_player(entity)
                return

    # --------------------------------------------------
    # Zone visuals
    # --------------------------------------------------

    def create_zone_visuals(self):
        for visual in self.zone_visuals:
            if visual is not None:
                destroy(visual)

        self.zone_visuals.clear()

        zone_colors = [
            ursina_color.rgba(255, 40, 40, 100),
            ursina_color.rgba(255, 150, 30, 80),
            ursina_color.rgba(255, 255, 40, 60),
        ]

        for zone_color in zone_colors:
            visual = Entity(
                parent=scene,
                model="quad",
                color=zone_color,
                collider=None,
                enabled=self.show_zones,
                always_on_top=False,
                z=0.04
            )

            self.zone_visuals.append(visual)

    def get_zone_visual_data(self, radius):
        if self.fov >= 360:
            return Vec3(self.x, self.y, 0.04), (radius * 2, radius * 2, 1)

        offset_x = (radius / 2) * self.facing_direction
        vertical_reach = radius * math.sin(math.radians(self.fov / 2)) * 2

        return (
            Vec3(self.x + offset_x, self.y, 0.04),
            (radius, max(vertical_reach, 0.35), 1)
        )

    def update_zone_visuals(self):
        if not self.zone_visuals:
            return

        radii = [self.zone1, self.zone2, self.zone3]

        for i, visual in enumerate(self.zone_visuals):
            if visual is None:
                continue

            visual.enabled = self.show_zones

            if not self.show_zones:
                continue

            visual.position, visual.scale = self.get_zone_visual_data(radii[i])

            if i == 0:
                visual.color = ursina_color.rgba(255, 40, 40, 100)
            elif i == 1:
                visual.color = ursina_color.rgba(255, 150, 30, 80)
            elif i == 2:
                visual.color = ursina_color.rgba(255, 255, 40, 60)

    # --------------------------------------------------
    # Position helpers
    # --------------------------------------------------

    def get_player_position_2d(self):
        self.resolve_player_if_missing_or_static()

        if not self.is_live_player_reference(self.player):
            return None

        return Vec2(self.player.x, self.player.y)

    def get_enemy_position_2d(self):
        return Vec2(self.x, self.y)

    def get_player_distance_and_direction(self):
        player_pos = self.get_player_position_2d()

        if player_pos is None:
            return None, None

        enemy_pos = self.get_enemy_position_2d()
        to_player = player_pos - enemy_pos
        distance_to_player = to_player.length()

        if distance_to_player <= 0:
            return distance_to_player, Vec2(0, 0)

        return distance_to_player, to_player.normalized()

    # --------------------------------------------------
    # Player state
    # --------------------------------------------------

    def is_player_invisible(self):
        self.resolve_player_if_missing_or_static()

        if self.player is None:
            return False

        return bool(getattr(self.player, "invisible", False))

    def is_player_crouched(self):
        self.resolve_player_if_missing_or_static()

        if self.player is None:
            return False

        return bool(getattr(self.player, "is_shrunk", False))

    # --------------------------------------------------
    # Detection
    # --------------------------------------------------

    def is_player_in_fov(self, direction_to_player):
        if direction_to_player is None:
            return False

        if self.fov >= 360:
            return True

        if direction_to_player.length() <= 0:
            return True

        facing = Vec2(self.facing_direction, 0)
        dot = facing.x * direction_to_player.x + facing.y * direction_to_player.y
        cos_half_fov = math.cos(math.radians(self.fov / 2))

        return dot >= cos_half_fov

    def get_detection_zone(self):
        distance_to_player, direction_to_player = self.get_player_distance_and_direction()

        if distance_to_player is None:
            return None

        if self.is_player_invisible():
            return None

        if not self.is_player_in_fov(direction_to_player):
            return None

        if distance_to_player <= self.zone1:
            return 1

        if distance_to_player <= self.zone2:
            return 2

        if distance_to_player <= self.zone3:
            return 3

        return None

    def update_detection_state(self):
        distance_to_player, direction_to_player = self.get_player_distance_and_direction()

        if distance_to_player is None:
            self.current_zone = None
            self.chasing = False
            return

        if self.is_player_invisible():
            self.current_zone = None
            self.chasing = False
            return

        detected_zone = self.get_detection_zone()
        self.current_zone = detected_zone

        if self.chasing:
            if distance_to_player <= self.zone3:
                self.last_seen_position = self.get_player_position_2d()
                return

            self.chasing = False
            return

        if detected_zone is None:
            return

        if self.is_player_crouched():
            if detected_zone == 1:
                self.chasing = True
                self.last_seen_position = self.get_player_position_2d()
            return

        if detected_zone in (1, 2, 3):
            self.chasing = True
            self.last_seen_position = self.get_player_position_2d()

    # --------------------------------------------------
    # Movement
    # --------------------------------------------------

    def get_horizontal_stop_distance(self):
        player_width = getattr(self.player, "scale_x", 1)
        enemy_width = getattr(self, "scale_x", 1)

        return (player_width / 2) + (enemy_width / 2) + 0.08

    def update_facing_direction(self, direction_x):
        if direction_x > 0.001:
            self.facing_direction = 1
        elif direction_x < -0.001:
            self.facing_direction = -1

        # Ustawiamy skalę tak, aby 1 patrzyło w prawo, a -1 w lewo
        # Jeśli domyślnie jest odwrócony, zamień znaki przy sx
        sx = -1 / self.num_cols
        sy = 1 / self.num_rows
        
        # Jeśli szczur patrzy w lewo, skalujemy x na minus
        if self.facing_direction == -1:
            self.texture_scale = (-sx, sy)
        else:
            self.texture_scale = (sx, sy)

    def chase_player(self):
        player_pos = self.get_player_position_2d()

        if player_pos is None:
            return

        enemy_pos = self.get_enemy_position_2d()

        delta_x = player_pos.x - enemy_pos.x
        stop_distance = self.get_horizontal_stop_distance()

        if abs(delta_x) <= stop_distance:
            self.update_facing_direction(delta_x)
            return

        move_dir = 1 if delta_x > 0 else -1

        self.update_facing_direction(move_dir)

        old_speed = self.speed
        self.speed = self.chase_speed

        old_x = self.x

        self.move_x(move_dir)

        new_delta_x = player_pos.x - self.x

        if abs(new_delta_x) > abs(delta_x) + 0.05:
            self.x = old_x

        self.speed = old_speed

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    def update(self):
        frame_index = int(time.time() * 7) % self.total_frames
        col = frame_index % self.num_cols
        row = frame_index // self.num_rows

        sx = 1 / self.num_cols
        sy = 1 / self.num_rows

        if self.facing_direction == 1:
            # Normalny offset
            self.texture_offset = (col * sx, 1 - (row + 1) * sy)
        else:
            # Offset skorygowany o szerokość klatki dla ujemnej skali
            self.texture_offset = ((col + 1) * sx, 1 - (row + 1) * sy)
        
        self.resolve_player_if_missing_or_static()
        self.update_detection_state()
        if self.chasing:
            self.chase_player()
        
        super().update()
        self.update_zone_visuals()