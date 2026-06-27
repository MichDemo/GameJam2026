from ursina import *

class Vent(Entity):
    def __init__(self, player, target_vent=None, cooldown_duration=1.0, **kwargs):
        wybrany_kolor = kwargs.pop('color', color.dark_gray)

        super().__init__(
            model='quad',
            color=wybrany_kolor,
            collider='box',
            **kwargs
        )
        self.player = player
        self.target_vent = target_vent
        self.sound_file = Audio('../assets/audio/vent.mp3', autoplay=False)
        
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
        self.sound_file.play()

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

        # --- ETAP 1: RUCH W POZIOMIE ---
        # Wyliczamy punkt pośredni: współrzędne X, Z z celu, ale wysokość Y ze startu
        intermediate_player_pos = Vec3(
            self.target_vent.position.x,
            self.player.position.y,
            self.target_vent.position.z
        )
        
        camera_offset = camera.position - self.player.position
        intermediate_camera_pos = intermediate_player_pos + camera_offset

        # Startujemy pierwszy etap (ruch poziomy przez 1 sekundę)
        self.player.animate_position(intermediate_player_pos, duration=0.5, curve=curve.linear)
        camera.animate_position(intermediate_camera_pos, duration=0.5, curve=curve.linear)

        # Po 1 sekundzie odpalamy etap drugi (ruch w pionie)
        invoke(self.start_vertical_movement, delay=0.5)

    def start_vertical_movement(self):
        # --- ETAP 2: RUCH W PIONIE (W GÓRĘ) ---
        # Cel ostateczny dla gracza
        target_player_pos = self.target_vent.position
        
        # Cel ostateczny dla kamery
        camera_offset = camera.position - self.player.position
        target_camera_pos = target_player_pos + camera_offset

        # Lecimy prosto w górę przez pozostałe 0.5 sekundy
        self.player.animate_position(target_player_pos, duration=0.5, curve=curve.linear)
        camera.animate_position(target_camera_pos, duration=0.5, curve=curve.linear)

        # Po 0.5 sekundy (czyli łącznie po 2 sekundach) kończymy teleportację
        invoke(self.end_teleport, delay=0.5)

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
        
        print("Płynna podróż załamana pod kątem 90 stopni zakończona!")
