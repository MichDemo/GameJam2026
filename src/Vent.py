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
        # Jeśli trwa teleportacja, nic nie rób
        if self.is_teleporting:
            self.prompt.enabled = False
            return

        # Obsługa cooldownu
        if self.cooldown_timer > 0:
            self.cooldown_timer -= time.dt
            self.prompt.enabled = False  
            return  

        # Sprawdzanie dystansu do gracza
        dist = distance(self.position, self.player.position)

        if dist < 1.5:
            self.prompt.enabled = True

            # Używamy inputu zamiast held_keys, aby kliknięcie zadziałało raz
            if held_keys['e']:
                self.start_teleport()
        else:
            self.prompt.enabled = False

    def start_teleport(self):
        if not self.target_vent:
            print("Ten wentyl nie ma ustawionego celu.")
            return

        # Wyłączamy skrypty gracza i sterowanie na czas lotu
        if hasattr(self.player, 'ignore'):
            self.player.ignore = True 
        
        # --- NIEWIDZIALNOŚĆ I NIEWYKRYWALNOŚĆ ---
        self.player.visible = False          
        self.player.invisible = True         
        
        if hasattr(self.player, 'collider') and self.player.collider:
            self.player.collider.enabled = False

        # Blokujemy wentyle
        self.is_teleporting = True
        self.target_vent.is_teleporting = True

        # --- OBLICZENIE DOCELOWEJ POZYCJI KAMERY ---
        # Sprawdzamy, jaki był offset (odległość) kamery od gracza przed startem,
        # aby zachować ten sam kąt i dystans (np. widok TPP, rzut izometryczny itp.)
        camera_offset = camera.position - self.player.position
        target_camera_pos = self.target_vent.position + camera_offset

        # --- ANIMACJA LOTU (Gracz + Kamera) ---
        # Animizujemy gracza
        self.player.animate_position(
            self.target_vent.position, 
            duration=1.0, 
            curve=curve.linear
        )
        # Animizujemy kamerę dokładnie w to samo miejsce (z zachowaniem offsetu)
        camera.animate_position(
            target_camera_pos,
            duration=1.0,
            curve=curve.linear
        )

        # Wywołanie zakończenia po 2 sekundach
        invoke(self.end_teleport, delay=1.0)

    def end_teleport(self):
        # --- PRZYWRACANIE WIDZIALNOŚCI I DETEKCJI ---
        self.player.visible = True
        self.player.invisible = False
        
        if hasattr(self.player, 'collider') and self.player.collider:
            self.player.collider.enabled = True

        # Przywracamy kontrolę nad graczem
        if hasattr(self.player, 'ignore'):
            self.player.ignore = False

        # Odblokowujemy wentyle i nakładamy cooldown
        self.is_teleporting = False
        self.target_vent.is_teleporting = False
        
        self.cooldown_timer = self.cooldown_duration
        self.target_vent.cooldown_timer = self.target_vent.cooldown_duration
        
        print("Płynna podróż z kamerą zakończona sukcesem!")