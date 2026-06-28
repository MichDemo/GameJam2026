from ursina import *

fur_texture = load_texture('../assets/textures/GENERIC_ICONS.png')

class Fur(Entity):
    def __init__(self, player, hold_time=2.0, **kwargs):
        super().__init__(
            model='quad',
            color=color.white,
            collider='box',
            texture=fur_texture, # Przypisujemy wczytaną teksturę
            **kwargs
        )

        self.pickup_sound = Audio('../assets/audio/podnoszenie_skory.wav', autoplay=False)

        # 2. Jeśli tekstura się wczytała, przycinamy ją dopiero tutaj
        if self.texture:
            self.texture_scale = (0.5, 0.5)
            self.texture_offset = (0, 0) # Lewy dolny róg (skóra)
        else:
            print("BŁĄD: Tekstura wciąż nie została wczytana przez load_texture!")

        self.player = player
        self.hold_time = hold_time
        self.timer = 0

        self.prompt = Text(
            text='Przytrzymaj E',
            parent=self,
            y=1.2,
            scale=10,
            enabled=False,
            origin=(0, 0),
            always_on_top=True
        )

    def update(self):
        # Sprawdź dystans do gracza
        dist = distance(self.position, self.player.position)

        if dist < 1.5:
            self.prompt.enabled = True

            # Płynna zmiana koloru promptu (wymaga importu z ursina)
            progress = self.timer / self.hold_time
            self.prompt.color = lerp(color.white, color.lime, progress)

            if held_keys['e']:
                self.timer += time.dt
                if self.timer >= self.hold_time:
                    self.collect()
            else:
                self.timer = 0
        else:
            self.prompt.enabled = False
            self.timer = 0
            self.prompt.color = color.white

    def collect(self):
        print("Fur zebrano!")
        self.pickup_sound.play()
        destroy(self) # Usunięcie obiektu ze świata gry
