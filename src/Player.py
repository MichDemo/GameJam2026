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
        # Wstrzykujemy ścieżkę do tekstury szczura
        kwargs['texture'] = '../assets/textures/RAT_MAIN_HERO.png'

        super().__init__(**kwargs)

        # Wczytanie dźwięku kroku
        self.step_sound = Audio('../assets/audio/kroki_szczura.mp3', loop=False, autoplay=False)
        self.step_timer = 0
        self.step_interval = 0.1  # Przerwa między dźwiękami kroków (w sekundach)



        # --- PRECYZYJNE KADROWANIE TWOJEGO SPRITESHEETU (3x5) ---
        self.RAT_GRID_WIDTH = 3   # 3 kolumny w obraz.png
        self.RAT_GRID_HEIGHT = 4  # 5 wierszy w obraz.png

        # Wybieramy domyślną stojącą klatkę (lewy górny róg)
        # W Ursinie dolny wiersz to 0, najwyższy to 4
        frame_x = 0  # Pierwsza kolumna
        frame_y = 4  # Najwyższy wiersz (stojący szczurek)

        self.texture_scale = (1 / self.RAT_GRID_WIDTH, 1 / self.RAT_GRID_HEIGHT)
        self.texture_offset = (frame_x / self.RAT_GRID_WIDTH, frame_y / self.RAT_GRID_HEIGHT)
        # --------------------------------------------------

        self.normal_size = Vec2(self.scale_x, self.scale_y)

        # Shrink height only.
        # Width remains exactly the same.
        self.shrink_size = Vec2(
            self.normal_size.x,
            self.normal_size.y
        )

        self.is_shrunk = False

        # Camera settings.
        # Camera follows a stable anchor, not current scaled player center.
        self.camera_follow = camera_follow
        self.camera_offset = Vec2(camera_offset[0], camera_offset[1])
        self.camera_z = camera_z

    # --------------------------------------------------
    # Camera
    # --------------------------------------------------

    def detach_camera_if_needed(self):
        """
        Prevents player scale from affecting camera/world transform.
        If camera.parent = player exists in Main.py, this safely detaches it.
        """
        if camera.parent == self:
            camera.parent = scene

    def get_camera_anchor(self):
        """
        Returns a stable 2D camera anchor.

        Important:
        Camera follows the player's NORMAL standing center,
        not the current crouched center.

        This prevents camera misalignment while crouching.
        """
        anchor_x = self.x

        # Stable vertical anchor:
        # bottom + original standing half-height
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

    # --------------------------------------------------
    # Shrink / restore
    # --------------------------------------------------

    def shrink(self):
        if self.is_shrunk:
            return

        self.resize_keep_feet(
            self.shrink_size,
            allow_if_blocked=True
        )

        self.is_shrunk = True
        
        # Zmiana sprajtu na kucającego szczurka (kolumna 0, wiersz 1 od dołu)
        self.texture_offset = (0 / self.RAT_GRID_WIDTH, 1 / self.RAT_GRID_HEIGHT)

    def unshrink(self):
        if not self.is_shrunk:
            return

        restored = self.resize_keep_feet(
            self.normal_size,
            allow_if_blocked=False
        )

        if restored:
            self.is_shrunk = False
            # Powrót do stojącego szczurka (kolumna 0, wiersz 4 od dołu)
            self.texture_offset = (0 / self.RAT_GRID_WIDTH, 4 / self.RAT_GRID_HEIGHT)

    # --------------------------------------------------
    # Akcje
    # --------------------------------------------------

    def jump(self):
        """Blokuje skok, jeśli gracz jest obecnie skurczony."""
        if self.is_shrunk:
            return  # Przerywa działanie funkcji, skok się nie odbędzie
            
        super().jump()  # Wywołuje oryginalny skok z klasy Rat

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    def update(self):
        # Ensure camera is not parented to player before scale changes.
        self.detach_camera_if_needed()

        # Movement left / right
        direction_x = 0

        if held_keys['a'] or held_keys['left arrow']:
            direction_x -= 1
            moving = True
        else:
            moving = False


        if held_keys['d'] or held_keys['right arrow']:
            direction_x += 1
            moving = True
        else:
            moving = False

        self.move_x(direction_x)

        # W = jump
        if held_keys['w'] or held_keys['up arrow']:
            self.jump()

        # S = shrink height only
        if held_keys['s'] or held_keys['down arrow']:
            self.shrink()
        else:
            self.unshrink()

        # Gravity + fall protection
        super().update()


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
