from ursina import *

class Vent(Entity):
    def __init__(self, player, target_vent=None, cooldown_duration=2.0, **kwargs):
        wybrany_kolor = kwargs.pop('color', color.dark_gray)

        super().__init__(
            model='quad',
            color=wybrany_kolor,
            collider='box',
            **kwargs
        )
        self.player = player
        self.target_vent = target_vent
        
        # Cooldown
        self.cooldown_duration = cooldown_duration
        self.cooldown_timer = 0  

        # Zmieniony tekst na "Naciśnij E"
        self.prompt = Text(
            text='Naciśnij E',
            parent=self,
            y=1.2,
            scale=10,
            enabled=False,
            origin=(0, 0)
        )

    def update(self):
        # Obsługa cooldownu
        if self.cooldown_timer > 0:
            self.cooldown_timer -= time.dt
            self.prompt.enabled = False  
            return  

        # Sprawdzanie dystansu do gracza
        dist = distance(self.position, self.player.position)

        if dist < 1.5:
            self.prompt.enabled = True

            # NATYCHMIASTOWY TELEPORT: wystarczy, że klawisz jest wciśnięty
            if held_keys['e']:
                self.teleport()
        else:
            self.prompt.enabled = False

    def teleport(self):
        if self.target_vent:
            # Natychmiastowa zmiana pozycji gracza
            self.player.position = self.target_vent.position
            
            # Aktywacja cooldownu na oba wentyle
            self.cooldown_timer = self.cooldown_duration
            self.target_vent.cooldown_timer = self.target_vent.cooldown_duration
            
            print("Natychmiastowa teleportacja zakończona sukcesem!")
        else:
            print("Ten wentyl nie ma ustawionego celu.")