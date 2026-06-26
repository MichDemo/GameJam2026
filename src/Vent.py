from ursina import *

class Vent(Entity):
    def __init__(self, player, target_vent=None, **kwargs):
        # Wyciągamy 'color' z kwargs. Jeśli go tam nie ma,
        # przypisujemy domyślny color.dark_gray
        wybrany_kolor = kwargs.pop('color', color.dark_gray)

        super().__init__(
            model='quad',
            color=wybrany_kolor,
            collider='box',
            **kwargs
        )
        self.player = player
        self.target_vent = target_vent
        self.hold_time = 3.0  # Czas w sekundach wymagany do przejścia
        self.timer = 0

        # Symbol interakcji dostosowany do skali kamery (fov=10) z Main.txt [3]
        self.prompt = Text(
            text='Przytrzymaj E',
            parent=self,
            y=1.2,
            scale=10,
            enabled=False,
            origin=(0, 0)
        )

    def update(self):
        # Sprawdzanie dystansu do gracza (Player) [4, 5]
        dist = distance(self.position, self.player.position)

        if dist < 1.5:
            self.prompt.enabled = True

            # Mechanika przytrzymywania (jak w przypadku futra)
            if held_keys['e']:
                self.timer += time.dt

                if self.timer >= self.hold_time:
                    self.teleport()
            else:
                # Reset, jeśli gracz puści klawisz przed czasem
                self.timer = 0
                self.prompt.color = color.white
        else:
            self.prompt.enabled = False
            self.timer = 0

    def teleport(self):
        if self.target_vent:
            # Zmiana pozycji gracza na pozycję docelowego venta [2, 4]
            self.player.position = self.target_vent.position
            self.timer = 0  # Reset timera po teleportacji
            print("Teleportacja zakończona sukcesem!")
        else:
            print("Ten wentyl nie ma ustawionego celu.")
