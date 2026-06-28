import os
import math
from ursina import *
from Rat import Rat


class Eye(Rat):
    _shared_eye_vision_music = None
    _active_vision_eyes = set()
    _eye_vision_audio_failed = False

    def __init__(
        self,
        player=None,
        facing_direction=1,
        zone_radius=4.5,
        fov_degrees=120,
        show_zones=False,
        detection_delay=2.0,
        **kwargs
    ):
        super().__init__(**kwargs)

        # --------------------------------------------------
        # EYE VISION MUSIC
        # --------------------------------------------------

        self._was_player_in_vision_last_frame = False
        self.ensure_eye_vision_music_exists()

        # --------------------------------------------------
        # EYE SPRITESHEET
        # --------------------------------------------------

        self.texture = load_texture("EYE_ENEMY")
        self.num_cols = 4
        self.num_rows = 4
        self.total_frames = 13
        self.frame = 0

        self.texture_scale = (1 / self.num_cols, 1 / self.num_rows)
        self.color = color.white

        # --------------------------------------------------
        # AI CONFIG
        # --------------------------------------------------

        self.player = player
        self.facing_direction = facing_direction
        self.zone_radius = zone_radius
        self.fov = fov_degrees
        self.fov_default = fov_degrees

        self.animations = {
            "idle": (0, 5),
            "turning": (6, 8),
            "detect": (9, 10),
            "search": (11, 12)
        }

        self.current_anim = "idle"
        self.last_direction = self.facing_direction

        self.current_zone = None
        self.last_seen_position = None

        self.detection_delay = detection_delay
        self.detection_timer = 0.0
        self.potential_zone = None

        self.target_direction = facing_direction
        self.rotation_speed = 2.0

        self.idle_turn_cooldown = 4.0
        self.idle_turn_timer = 0.0

        self.loss_cooldown = 2.0
        self.loss_timer = 0.0

        self.show_zones = show_zones
        self.zone_color = color.rgba(250, 128, 114, 70)

        self.zone_visual = None
        self._init_zone_visuals()

        # --------------------------------------------------
        # ANIMATION TIMERS
        # --------------------------------------------------

        self.anim_timer = 0.0
        self.idle_anim_speed = 0.14
        self.turning_anim_speed = 0.11
        self.detect_anim_speed = 0.16
        self.search_anim_speed = 1.0

        self.detect_reached_final_frame = False

        # --------------------------------------------------
        # ICON NOTIFIER
        # --------------------------------------------------

        self.icons_cols = 2
        self.icons_rows = 2

        self.exclamation_mark_frame = 0
        self.question_mark_frame = 1

        self.icon_scale = 0.38
        self.icon_extra_y_offset = 0.28

        self.icon_notifier = Entity(
            parent=scene,
            model="quad",
            texture=load_texture("GENERIC_ICONS"),
            position=(self.x, self.y + 1.0, -0.35),
            scale=(self.icon_scale, self.icon_scale, 1),
            enabled=False,
            always_on_top=True,
            collider=None
        )

        self.icon_notifier.origin = (0, 0)
        self.icon_notifier.color = color.white
        self.icon_notifier.texture_scale = (
            1 / self.icons_cols,
            1 / self.icons_rows
        )

        self.update_icon_texture_offset(self.question_mark_frame)
        self.update_icon_position()

    @classmethod
    def get_eye_vision_audio_path(cls):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_path = os.path.join(current_dir, "..", "assets", "audio", "eye_vision")
        normalized_path = os.path.normpath(target_path)
        
        if not os.path.exists(normalized_path + ".wav"):
            print(f"[Eye Warning] Fizyczny plik nie istnieje pod ścieżką: {normalized_path}.wav")
            
        return "audio/eye_vision"

    # --------------------------------------------------
    # EYE VISION MUSIC - KLASYCZNY RELATYWNY WZORZEC
    # --------------------------------------------------

    @classmethod
    def ensure_eye_vision_music_exists(cls):
        if cls._eye_vision_audio_failed:
            return
        if cls._shared_eye_vision_music is not None:
            return

        try:
            # Szukamy bezpośrednio w assets/audio/eye_vision, bez rozszerzenia .wav
            cls._shared_eye_vision_music = Audio(
                'audio/eye_vision',
                loop=True,
                autoplay=False
            )
            cls._shared_eye_vision_music.volume = 0.0
        except Exception as error:
            print(f"[Eye] Błąd ładowania audio oka: {error}")
            cls._eye_vision_audio_failed = True
            cls._shared_eye_vision_music = None

    def start_eye_vision_music(self):
        Eye.ensure_eye_vision_music_exists()
        if Eye._eye_vision_audio_failed or Eye._shared_eye_vision_music is None:
            return

        if self not in Eye._active_vision_eyes:
            Eye._active_vision_eyes.add(self)

        try:
            Eye._shared_eye_vision_music.volume = 0.75
            if not Eye._shared_eye_vision_music.playing:
                Eye._shared_eye_vision_music.play()
        except Exception:
            pass

    def stop_eye_vision_music(self):
        if self in Eye._active_vision_eyes:
            Eye._active_vision_eyes.remove(self)

        if len(Eye._active_vision_eyes) > 0:
            return

        if Eye._shared_eye_vision_music is None:
            return

        try:
            Eye._shared_eye_vision_music.volume = 0.0
        except Exception:
            pass

    @classmethod
    def has_valid_eye_audio(cls):
        if cls._shared_eye_vision_music is None or cls._eye_vision_audio_failed:
            return False
        try:
            if hasattr(cls._shared_eye_vision_music, 'clip') and cls._shared_eye_vision_music.clip is None:
                return False
        except Exception:
            return False
        return True

    def is_player_currently_seen_or_scanned(self):
        return (
            self.detection_timer > 0.0
            or self.current_zone is not None
            or self.potential_zone is not None
        )

    def update_eye_vision_music_state(self):
        player_in_vision = self.is_player_currently_seen_or_scanned()

        if player_in_vision:
            self.start_eye_vision_music()
            self._was_player_in_vision_last_frame = True
            return

        if self._was_player_in_vision_last_frame:
            self.stop_eye_vision_music()
            self._was_player_in_vision_last_frame = False

    # --------------------------------------------------
    # CLEANUP
    # --------------------------------------------------

    def on_destroy(self):
        try:
            self.stop_eye_vision_music()
        except Exception:
            pass

        if self in Eye._active_vision_eyes:
            Eye._active_vision_eyes.remove(self)

        if self.zone_visual is not None:
            try:
                destroy(self.zone_visual)
            except Exception:
                pass

            self.zone_visual = None

        if self.icon_notifier is not None:
            try:
                destroy(self.icon_notifier)
            except Exception:
                pass

            self.icon_notifier = None

    # --------------------------------------------------
    # ICONS
    # --------------------------------------------------

    def update_icon_texture_offset(self, frame_index):
        if self.icon_notifier is None:
            return

        frame_index = max(
            0,
            min(
                int(frame_index),
                (self.icons_cols * self.icons_rows) - 1
            )
        )

        col = frame_index % self.icons_cols
        row_from_top = frame_index // self.icons_cols

        sx = 1 / self.icons_cols
        sy = 1 / self.icons_rows

        row_from_bottom = (self.icons_rows - 1) - row_from_top

        self.icon_notifier.texture_scale = (sx, sy)
        self.icon_notifier.texture_offset = (
            col * sx,
            row_from_bottom * sy
        )

    def update_icon_position(self):
        if self.icon_notifier is None:
            return

        icon_y = self.y + (self.scale_y / 2) + self.icon_extra_y_offset

        self.icon_notifier.position = (
            self.x,
            icon_y,
            -0.35
        )

        self.icon_notifier.scale = (
            self.icon_scale,
            self.icon_scale,
            1
        )

        self.icon_notifier.rotation = (0, 0, 0)

    def update_icon_state(self):
        if self.icon_notifier is None:
            return

        self.update_icon_position()

        if self.current_zone is not None:
            self.icon_notifier.enabled = True
            self.update_icon_texture_offset(self.exclamation_mark_frame)

        elif self.detection_timer > 0.0:
            self.icon_notifier.enabled = True
            self.update_icon_texture_offset(self.question_mark_frame)

        else:
            self.icon_notifier.enabled = False

    # --------------------------------------------------
    # ZONE VISUALS
    # --------------------------------------------------

    def _init_zone_visuals(self):
        self.zone_visual = Entity(
            parent=scene,
            model="quad",
            color=self.zone_color,
            always_on_top=False,
            collider=None,
            z=0.05,
            enabled=self.show_zones
        )

    def update_zone_visuals(self):
        if self.zone_visual is None:
            return

        if not self.show_zones:
            self.zone_visual.enabled = False
            return

        self.zone_visual.enabled = True

        radius = self.zone_radius

        if self.fov >= 360:
            self.zone_visual.position = (
                self.x,
                self.y,
                0.05
            )

            self.zone_visual.scale = (
                radius * 2,
                radius * 2,
                1
            )

        else:
            offset_x = (radius / 2) * self.facing_direction
            vertical_reach = radius * math.sin(math.radians(self.fov / 2)) * 2

            self.zone_visual.position = (
                self.x + offset_x,
                self.y,
                0.05
            )

            self.zone_visual.scale = (
                radius,
                max(vertical_reach, 1.0),
                1
            )

    # --------------------------------------------------
    # DETECTION
    # --------------------------------------------------

    def check_player_detection(self):
        if not self.player:
            self.current_zone = None
            self.potential_zone = None
            self.detection_timer = 0.0
            return

        if getattr(self.player, "invisible", False):
            self.current_zone = None
            self.potential_zone = None
            self.detection_timer = 0.0
            return

        to_player = self.player.position - self.position
        to_player_2d = Vec2(to_player.x, to_player.y)
        distance_to_player = to_player_2d.length()

        is_in_vision_cone = False

        if distance_to_player > 0:
            player_dir = to_player_2d.normalized()
            facing_vec = Vec2(self.facing_direction, 0)

            dot_product = facing_vec.x * player_dir.x + facing_vec.y * player_dir.y
            cos_half_fov = math.cos(math.radians(self.fov / 2))

            if dot_product >= cos_half_fov:
                is_in_vision_cone = True

        # Bezpieczny raycast z ignorowaniem samego siebie
        if is_in_vision_cone and distance_to_player <= self.zone_radius:
            hit_info = raycast(self.position, to_player_2d.normalized(), distance=distance_to_player, ignore=(self, self.icon_notifier))
            if hit_info.hit and hit_info.entity.__class__.__name__.lower() != "player":
                is_in_vision_cone = False

        raw_zone = None
        if is_in_vision_cone and distance_to_player <= self.zone_radius:
            raw_zone = 1

        if raw_zone is not None:
            self.potential_zone = raw_zone

            if self.current_zone is None:
                self.detection_timer += time.dt

                if to_player.x > 0.002:
                    self.target_direction = 1
                elif to_player.x < -0.002:
                    self.target_direction = -1

                if self.detection_timer >= self.detection_delay:
                    self.current_zone = self.potential_zone
                    
                    # Bezpieczne wywołanie przegranej przez referencję sceny
                    if hasattr(scene, "game_over_func") and scene.game_over_func:
                        scene.game_over_func()

            else:
                self.current_zone = raw_zone
        else:
            if self.potential_zone is not None or self.current_zone is not None:
                self.current_zone = None
                self.potential_zone = None
                self.detection_timer = 0.0

    # --------------------------------------------------
    # BEHAVIOR
    # --------------------------------------------------

    def handle_behavior(self):
        target_pos = None

        if self.current_zone is not None:
            self.idle_turn_timer = 0.0
            self.loss_timer = 0.0

            target_pos = self.player.position
            self.fov = 360

            self.last_seen_position = Vec3(
                self.player.x,
                self.player.y,
                self.player.z
            )

        elif self.detection_timer > 0.0:
            self.idle_turn_timer = 0.0
            self.loss_timer = 0.0

        elif self.last_seen_position is not None:
            self.idle_turn_timer = 0.0
            self.fov = self.fov_default

            target_pos = self.last_seen_position
            move_dir = target_pos - self.position

            desired_dir = 1 if move_dir.x > 0 else -1

            if abs(self.facing_direction - desired_dir) < 0.2:
                self.loss_timer += time.dt

                if self.loss_timer >= self.loss_cooldown:
                    print(
                        f"[BEHAVIOR] Minęło {self.loss_cooldown}s obserwacji. "
                        f"Powrót do idle."
                    )

                    self.last_seen_position = None
                    self.loss_timer = 0.0
                    target_pos = None

        else:
            self.loss_timer = 0.0
            self.fov = self.fov_default

            self.idle_turn_timer += time.dt

            if self.idle_turn_timer >= self.idle_turn_cooldown:
                self.target_direction = -1 if self.target_direction == 1 else 1
                self.idle_turn_timer = 0.0

        if target_pos is not None and self.detection_timer == 0.0:
            move_dir = target_pos - self.position

            if move_dir.x > 0.002:
                self.target_direction = 1
            elif move_dir.x < -0.002:
                self.target_direction = -1

    # --------------------------------------------------
    # ANIMATION
    # --------------------------------------------------

    def play_animation(self, anim_name):
        if self.current_anim != anim_name:
            self.current_anim = anim_name
            self.frame = self.animations[anim_name][0]
            self.anim_timer = 0.0

            if anim_name == "detect":
                self.detect_reached_final_frame = False

    def update_frame_uv(self):
        sx = 1 / self.num_cols
        sy = 1 / self.num_rows

        row_from_top = self.frame // self.num_cols
        row = (self.num_rows - 1) - row_from_top
        col = self.frame % self.num_cols

        direction_sign = -1 if self.facing_direction >= 0 else 1

        if direction_sign >= 0:
            self.texture_scale = (sx, sy)
            self.texture_offset = (col * sx, row * sy)
        else:
            self.texture_scale = (-sx, sy)
            self.texture_offset = ((col + 1) * sx, row * sy)

    def advance_animation_frame(self, start, end, speed):
        self.anim_timer += time.dt

        if self.anim_timer < speed:
            return

        self.anim_timer = 0.0

        self.frame += 1

        if self.frame > end:
            self.frame = start

    def advance_detect_until_final_frame(self, start, end):
        if self.detect_reached_final_frame:
            self.frame = end
            return

        self.anim_timer += time.dt

        if self.anim_timer < self.detect_anim_speed:
            return

        self.anim_timer = 0.0

        if self.frame < end:
            self.frame += 1

        if self.frame >= end:
            self.frame = end
            self.detect_reached_final_frame = True

    def update_animation_state(self):
        self.facing_direction = lerp(
            self.facing_direction,
            self.target_direction,
            time.dt * self.rotation_speed
        )

        is_turning = abs(self.facing_direction) < 0.5

        if is_turning:
            new_anim = "turning"
        elif self.current_zone is not None:
            new_anim = "detect"
        elif self.last_seen_position is not None:
            new_anim = "search"
        else:
            new_anim = "idle"

        start, end = self.animations[new_anim]

        if self.current_anim != new_anim:
            self.current_anim = new_anim
            self.frame = start
            self.anim_timer = 0.0

            if new_anim == "detect":
                self.detect_reached_final_frame = False

        if new_anim == "detect":
            self.advance_detect_until_final_frame(
                start=start,
                end=end
            )

        elif new_anim == "search":
            self.advance_animation_frame(
                start=start,
                end=end,
                speed=self.search_anim_speed
            )

        elif new_anim == "turning":
            self.advance_animation_frame(
                start=start,
                end=end,
                speed=self.turning_anim_speed
            )

        else:
            self.advance_animation_frame(
                start=start,
                end=end,
                speed=self.idle_anim_speed
            )

        self.update_frame_uv()
        self.last_direction = self.facing_direction

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------

    def update(self):
        super().update()

        self.check_player_detection()
        self.handle_behavior()
        self.update_animation_state()

        self.update_icon_state()
        self.update_eye_vision_music_state()
        self.update_zone_visuals()