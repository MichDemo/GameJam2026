from ursina import *

class Vent(Entity):
    def __init__(self, player, target_vent=None, **kwargs):
        # Inicjalizacja jako podstawowy obiekt (podobnie jak Block czy Rat)
        super().__init__(
            model='quad',
            collider='box',
            color=kwargs.pop('color', color.dark_gray), # Wyciąga kolor z kwargs, a jak go nie ma, daje dark_gray
            **kwargs
)

        self.player = player
        self.target_vent = target_vent  # Referencja do innego obiektu klasy Vent

        # Placeholder symbolu interakcji "E"
        self.prompt = Text(
            text='E',
            parent=self,
            y=1.2,
            scale=10,
            enabled=False,
            origin=(0, 0),
            color=color.yellow
        )

    def update(self):
        # Sprawdzanie dystansu między szczurem (graczem) a ventem
        if distance(self.position, self.player.position) < 1.5:
            self.prompt.enabled = True
        else:
            self.prompt.enabled = False

    def input(self, key):
        # Reakcja na naciśnięcie "E", gdy gracz jest blisko
        if key == 'e' and self.prompt.enabled:
            if self.target_vent:
                # Przeniesienie gracza do pozycji docelowego venta
                self.player.position = self.target_vent.position
                print("Teleportacja przez wentylację!")
            else:
                print("Ten wentyl prowadzi donikąd.")
