from ursina import *


class Vent(Entity):
    def __init__(self, player, target_vent=None, cooldown_duration=1.0, tile_x=0, tile_y=2, **kwargs):
        # Domyślna tekstura dla wentylacji
        kwargs.setdefault('texture', 'LEVEL_BLOCK_SHEET.png')
        kwargs.setdefault('color', color.white)

        super().__init__(
            model='quad',
            collider='box',
            **kwargs
        )
        self.player = player
        self.target_vent = target_vent
        self.sound_file = Audio('../assets/audio/vent.mp3', autoplay=False)


        # --- DYNAMICZNE MAPOWANIE UV (Siatka 9x3, kafelki po 32x32px) ---
        tileset_cols = 9
        tileset_rows = 3

        # Wycinamy kafelek na podstawie podanych współrzędnych
        self.texture_scale = (1 / tileset_cols, 1 / tileset_rows)
        self.texture_offset = (tile_x / tileset_cols, tile_y / tileset_rows)
        # -----------------------------------------------------

        # Cooldown
        self.cooldown_duration = cooldown_duration
        self.cooldown_timer = 0

        # Flaga blokująca ruch podczas animacji
        self.is_teleporting = False

        self.prompt = Text(
            text='Naciśnij E',
            parent=self,
            y=1.2,
            scale=10,
            enabled=False,
            origin=(0, 0)
        )

    def update(self):
        if self.is_teleporting:
            self.prompt.enabled = False
            return

        if self.cooldown_timer > 0:
            self.cooldown_timer -= time.dt
            self.prompt.enabled = False
            return

        dist = distance(self.position, self.player.position)

        if dist < 1.0:
            self.prompt.enabled = True
            if held_keys['e']:
                self.start_teleport()
        else:
            self.prompt.enabled = False

    def start_teleport(self):
        self.sound_file.play()

        if not self.target_vent:
            print("Ten wentyl nie ma ustawionego celu.")
            return

        if hasattr(self.player, 'ignore'):
            self.player.ignore = True

        self.player.visible = False
        self.player.invisible = True
        if hasattr(self.player, 'collider') and self.player.collider:
            self.player.collider.enabled = False

        self.is_teleporting = True
        self.target_vent.is_teleporting = True

        intermediate_player_pos = Vec3(
            self.target_vent.position.x,
            self.player.position.y,
            self.target_vent.position.z
        )

        camera_offset = camera.position - self.player.position
        intermediate_camera_pos = intermediate_player_pos + camera_offset

        self.player.animate_position(intermediate_player_pos, duration=0.5, curve=curve.linear)
        camera.animate_position(intermediate_camera_pos, duration=0.5, curve=curve.linear)

        invoke(self.start_vertical_movement, delay=0.5)

    def start_vertical_movement(self):
        target_player_pos = self.target_vent.position

        camera_offset = camera.position - self.player.position
        target_camera_pos = target_player_pos + camera_offset

        self.player.animate_position(target_player_pos, duration=0.5, curve=curve.linear)
        camera.animate_position(target_camera_pos, duration=0.5, curve=curve.linear)

        invoke(self.end_teleport, delay=0.5)

    def end_teleport(self):
        self.player.visible = True
        self.player.invisible = False
        if hasattr(self.player, 'collider') and self.player.collider:
            self.player.collider.enabled = True

        if hasattr(self.player, 'ignore'):
            self.player.ignore = False

        self.is_teleporting = False
        self.target_vent.is_teleporting = False

        self.cooldown_timer = self.cooldown_duration
        self.target_vent.cooldown_timer = self.target_vent.cooldown_duration

        print("Płynna podróż załamana pod kątem 90 stopni zakończona!")
