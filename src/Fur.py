from ursina import *

class Fur(Entity):
    def __init__(self, player, hold_time=2.0, **kwargs):
        super().__init__(
            model='quad',
            color=color.brown,
            collider='box',
            **kwargs
        )

        self.pickup_sound = Audio('../assets/audio/podnoszenie_skory.mp3', autoplay=False)

        self.player = player
        self.hold_time = hold_time  # Czas potrzebny na podniesienie (w sekundach)
        self.timer = 0

        self.prompt = Text(
            text='Przytrzymaj E',
            parent=self,
            y=1.2,
            scale=10,
            enabled=False,
            origin=(0, 0)
        )

    def update(self):
        dist = distance(self.position, self.player.position)

        if dist < 1.5:
            self.prompt.enabled = True

            # Mechanika przytrzymywania klawisza
            if held_keys['e']:
                self.timer += time.dt
                # Opcjonalnie: wizualizacja postępu (np. zmiana koloru promptu)
                # self.prompt.color = color.lerp(color.white, color.green, self.timer / self.hold_time)

                if self.timer >= self.hold_time:
                    self.collect()
            else:
                # Reset postępu po puszczeniu klawisza
                self.timer = 0
                self.prompt.color = color.white
        else:
            self.prompt.enabled = False
            self.timer = 0

    def collect(self):
        self.pickup_sound.play()
        destroy(self) # Usunięcie obiektu ze świata gry
