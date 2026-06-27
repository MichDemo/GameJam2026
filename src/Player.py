from ursina import *
from Rat import Rat


class Player(Rat):
    def __init__(
        self,
        camera_follow=True,
        camera_offset=(0, 0),
        camera_z=-20,
        **kwargs
    ):
        kwargs['texture'] = '../assets/textures/RAT_MAIN_HERO.png'
        super().__init__(**kwargs)

        self.RAT_GRID_WIDTH = 3
        self.RAT_GRID_HEIGHT = 4

        self.WEST = -1
        self.EAST = 1
        # Wczytanie dźwięku kroku
        self.step_sound = Audio('../assets/audio/kroki_szczura.mp3', loop=False, autoplay=False)
        self.step_timer = 0
        self.step_interval = 0.1  # Przerwa między dźwiękami kroków (w sekundach)


        # --- NIUCHANIE ---
        # Inicjalizacja dźwięku niuchania (ścieżka zgodna z Main.txt [3])
        self.sniff_sound = Audio('../assets/audio/niuch.mp3', autoplay=False)

        # Pierwsze losowe odliczenie (np. od 5 do 12 sekund)
        self.sniff_timer = random.uniform(5, 116)

        # --- PRECYZYJNE KADROWANIE TWOJEGO SPRITESHEETU (3x5) ---
        self.RAT_GRID_WIDTH = 3   # 3 kolumny w obraz.png
        self.RAT_GRID_HEIGHT = 4  # 5 wierszy w obraz.png

        self.NATIVE_SPRITE_DIRECTION = self.WEST

        self.facing_direction = self.EAST
        self.current_frame = 1
        self.animation_timer = 0.0
        self.animation_speed = 0.09

        self.move_frames = [1, 2, 3, 4, 5, 6]
        self.crawl_frames = [7, 8]
        self.jump_frames = [9, 10]

        self.hitbox_width_multiplier = 0.72
        self.hitbox_height_multiplier = 0.82

        self.normal_size = Vec2(self.scale_x, self.scale_y)
        self.shrink_size = Vec2(
            self.normal_size.x,
            self.normal_size.y
        )

        self.is_shrunk = False

        self.camera_follow = camera_follow
        self.camera_offset = Vec2(camera_offset[0], camera_offset[1])
        self.camera_z = camera_z

        self.update_visual_collider()
        self.set_sprite_frame(1)

    @property
    def half_width(self):
        return (self.scale_x * self.hitbox_width_multiplier) / 2

    @property
    def half_height(self):
        return (self.scale_y * self.hitbox_height_multiplier) / 2

    @property
    def left(self):
        return self.x - self.half_width

    @property
    def right(self):
        return self.x + self.half_width

    @property
    def bottom(self):
        return self.y - self.half_height

    @property
    def top(self):
        return self.y + self.half_height

    def update_visual_collider(self):
        self.collider = BoxCollider(
            self,
            center=(0, 0, 0),
            size=(
                self.hitbox_width_multiplier,
                self.hitbox_height_multiplier,
                1
            )
        )

    def detach_camera_if_needed(self):
        if camera.parent == self:
            camera.parent = scene

    def get_camera_anchor(self):
        anchor_x = self.x
        anchor_y = self.bottom + (self.normal_size.y / 2)
        return Vec2(anchor_x, anchor_y)

    def update_camera_follow(self):
        if not self.camera_follow:
            return

        self.detach_camera_if_needed()

        anchor = self.get_camera_anchor()
        camera.x = anchor.x + self.camera_offset.x
        camera.y = anchor.y + self.camera_offset.y
        camera.z = self.camera_z

    def set_facing(self, direction):
        if direction < 0:
            self.facing_direction = self.WEST
        elif direction > 0:
            self.facing_direction = self.EAST

        self.set_sprite_frame(self.current_frame)

    def set_sprite_frame(self, frame_index):
        frame_index = max(1, min(12, int(frame_index)))

        col = (frame_index - 1) % self.RAT_GRID_WIDTH
        row_from_top = (frame_index - 1) // self.RAT_GRID_WIDTH
        row = (self.RAT_GRID_HEIGHT - 1) - row_from_top

        sx = 1 / self.RAT_GRID_WIDTH
        sy = 1 / self.RAT_GRID_HEIGHT

        if self.facing_direction == self.NATIVE_SPRITE_DIRECTION:
            self.texture_scale = (sx, sy)
            self.texture_offset = (col * sx, row * sy)
        else:
            self.texture_scale = (-sx, sy)
            self.texture_offset = ((col + 1) * sx, row * sy)

        self.current_frame = frame_index

    def animate_frames(self, frames):
        if not frames:
            return

        self.animation_timer += time.dt

        if self.current_frame not in frames:
            self.animation_timer = 0.0
            self.set_sprite_frame(frames[0])
            return

        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            index = frames.index(self.current_frame)
            next_index = (index + 1) % len(frames)
            self.set_sprite_frame(frames[next_index])

    def update_animation(self, direction_x):
        if not self.grounded:
            if self.velocity_y >= 0:
                self.set_sprite_frame(9)
            else:
                self.set_sprite_frame(10)
            return

        if self.is_shrunk:
            if direction_x == 0:
                self.animation_timer = 0.0
                self.set_sprite_frame(7)
            else:
                self.animate_frames(self.crawl_frames)
            return

        if direction_x != 0:
            self.animate_frames(self.move_frames)
            return

        self.animation_timer = 0.0
        self.set_sprite_frame(1)

    def shrink(self):
        if self.is_shrunk:
            return

        self.resize_keep_feet(
            self.shrink_size,
            allow_if_blocked=True
        )

        self.is_shrunk = True
        self.animation_timer = 0.0
        self.update_visual_collider()
        self.set_sprite_frame(7)

    def unshrink(self):
        if not self.is_shrunk:
            return

        restored = self.resize_keep_feet(
            self.normal_size,
            allow_if_blocked=False
        )

        if restored:
            self.is_shrunk = False
            self.animation_timer = 0.0
            self.update_visual_collider()
            self.set_sprite_frame(1)

    def jump(self):
        if self.is_shrunk:
            return

        was_grounded = self.grounded
        super().jump()

        if was_grounded and not self.grounded:
            self.animation_timer = 0.0
            self.set_sprite_frame(9)

    def update(self):
        self.detach_camera_if_needed()

        if getattr(self, "ignore", False):
            self.update_camera_follow()
            return

        left_pressed = held_keys['a'] or held_keys['left arrow']
        right_pressed = held_keys['d'] or held_keys['right arrow']

        direction_x = 0

        if held_keys['a'] or held_keys['left arrow']:
            direction_x -= 1
            moving = True
        else:
            moving = False

        if left_pressed and not right_pressed:
            direction_x = -1
            self.set_facing(self.WEST)

        elif right_pressed and not left_pressed:
            direction_x = 1
            self.set_facing(self.EAST)
        if held_keys['d'] or held_keys['right arrow']:
            direction_x += 1
            moving = True
        else:
            moving = False

        self.move_x(direction_x)

        if held_keys['w'] or held_keys['up arrow']:
            self.jump()

        if held_keys['s'] or held_keys['down arrow']:
            self.shrink()
        else:
            self.unshrink()

        super().update()

        self.update_animation(direction_x)

        # Uwaga: grounded to zmienna, którą powinieneś mieć w klasie Rat
        # obsługującej kolizje z solid_objects [4]
        if moving and self.grounded:
            self.step_timer += time.dt
            if self.step_timer >= self.step_interval:
                if not self.step_sound.playing:
                    self.step_sound.play()
                self.step_timer = 0
        else:
            self.step_timer = self.step_interval # Reset timera, by krok zagrał od razu po ruszeniu


        # Camera follows stable standing-height anchor
        self.update_camera_follow()
