import math
from ursina import *
from Rat import Rat

class Eye(Rat):
    def __init__(
        self, 
        player=None, 
        facing_direction=1, 
        zone_radius=4.5,          # <-- ZMIANA: Pojedyncza wartość
        fov_degrees=120, 
        show_zones=False,  
        detection_delay=2.0,  
        **kwargs
    ):
        super().__init__(**kwargs)

        # --- KONFIGURACJA SPRITESHEET OKA ---
        self.texture = load_texture("EYE_ENEMY") # Nazwa pliku bez .png
        self.num_cols = 4  # Zliczając z obrazka: masz 4 kolumny
        self.num_rows = 4  # Ostatni rząd jest niepełny, ale zdefiniujmy jako 4
        self.total_frames = 13 # Masz 13 klatek (4*4 minus 3 puste)
        self.frame = 0
        
        # Ustawienie skali jednej klatki
        self.texture_scale = (1/self.num_cols, 1/self.num_rows)
        self.color = color.white
        
        self.player = player
        self.facing_direction = facing_direction  
        self.zone_radius = zone_radius          # <-- ZMIANA: Jeden promień
        self.fov = fov_degrees
        self.fov_default = fov_degrees  

        self.animations = {
            "idle":    (0, 5),
            "turning": (6, 8),
            "detect":  (9, 10),
            "search":  (11, 12)
        }
        self.current_anim = "idle"
        # Dodajemy zmienną do śledzenia poprzedniego kierunku
        self.last_direction = self.facing_direction
        self.frame = 0
        
        self.current_zone = None  
        self.last_seen_position = None  
        
        self.detection_delay = detection_delay  
        self.detection_timer = 0.0              
        self.potential_zone = None              

        self.target_direction = facing_direction  
        self.rotation_speed = 2.0                 

        self.idle_turn_cooldown = 4.0             
        self.idle_turn_timer = 0.0

        self.loss_cooldown = 2.0        
        self.loss_timer = 0.0           
        
        self.show_zones = show_zones  
        
        # --- ZMIANA: Jeden kolor ---
        self.zone_color = color.salmon   
        
        self.zone_visual = None                 # <-- ZMIANA: Jeden obiekt
        self._init_zone_visuals()

    def _init_zone_visuals(self):
        # --- ZMIANA: Tworzenie pojedynczego quada ---
        self.zone_visual = Entity(
            model='quad',
            color=self.zone_color,
            always_on_top=False,
            z=0.05
        )

    def update_zone_visuals(self):
        # --- ZMIANA: Uproszczona aktualizacja ---
        if not self.show_zones:
            self.zone_visual.enabled = False
            return
        
        self.zone_visual.enabled = True
        radius = self.zone_radius
        
        if self.fov >= 360:
            self.zone_visual.position = self.position + Vec3(0, 0, 0.05)
            self.zone_visual.scale = (radius * 2, radius * 2, 1)
        else:
            offset_x = (radius / 2) * self.facing_direction
            self.zone_visual.position = self.position + Vec3(offset_x, 0, 0.05)
            vertical_reach = radius * math.sin(math.radians(self.fov / 2)) * 2
            self.zone_visual.scale = (radius, max(vertical_reach, 1.0), 1)

    def check_player_detection(self):
        if not self.player:
            return

        to_player = self.player.position - self.position
        to_player_2d = Vec2(to_player.x, to_player.y)
        distance = to_player_2d.length()
        
        is_in_vision_cone = False
        
        if distance > 0:
            player_dir = to_player_2d.normalized()
            facing_vec = Vec2(self.facing_direction, 0)
            dot_product = facing_vec.x * player_dir.x + facing_vec.y * player_dir.y
            cos_half_fov = math.cos(math.radians(self.fov / 2))
            
            if dot_product >= cos_half_fov:
                is_in_vision_cone = True

        raw_zone = None
        if is_in_vision_cone and distance <= self.zone_radius:
            raw_zone = 1

        if raw_zone is not None:
            self.potential_zone = raw_zone

            if self.current_zone is None:
                if self.detection_timer == 0.0:
                    print(f"[SKANOWANIE] Gracz namierzony. Rozpoczęto odliczanie {self.detection_delay} sekund...")
                
                self.detection_timer += time.dt
                
                # --- NOWOŚĆ: Podczas skanowania blokujemy wzrok na graczu ---
                if to_player.x > 0.002:
                    self.target_direction = 1
                elif to_player.x < -0.002:
                    self.target_direction = -1
                
                if self.detection_timer >= self.detection_delay:
                    self.current_zone = self.potential_zone
                    print(f"[ALERT] Gracz oficjalnie WYKRYTY po {self.detection_delay}s!")
            else:
                self.current_zone = raw_zone
        else:
            if self.potential_zone is not None or self.current_zone is not None:
                if self.current_zone is not None:
                    print("[ALERT] Gracz zgubiony! Patrzę w stronę ostatniej pozycji.")
                else:
                    print("[SKANOWANIE] Gracz uciekł ze stożka widzenia. Reset timera.")
                
                self.current_zone = None
                self.potential_zone = None
                self.detection_timer = 0.0

    def handle_behavior(self):
        """Przetwarza stan wykrywania i ustawia docelowy kierunek spojrzenia."""
        target_pos = None

        # Stan A: Gracz w pełni wykryty
        if self.current_zone is not None:
            self.idle_turn_timer = 0.0
            self.loss_timer = 0.0  
            target_pos = self.player.position
            self.fov = 360  
            self.last_seen_position = Vec3(self.player.x, self.player.y, self.player.z)

        # NOWOŚĆ -> Stan A.5: Gracz jest dopiero skanowany (timer odlicza, ale jeszcze nie wykryty)
        elif self.detection_timer > 0.0:
            self.idle_turn_timer = 0.0
            self.loss_timer = 0.0
            # Wzrok jest blokowany bezpośrednio w check_player_detection, więc tutaj nic nie nadpisujemy

        # Stan B: Gracz zgubiony -> Patrz w tamtą stronę przez określony czas
        elif self.last_seen_position is not None:
            self.idle_turn_timer = 0.0  # Blokujemy timer obrotów w tle!
            self.fov = self.fov_default  
            target_pos = self.last_seen_position
            
            move_dir = target_pos - self.position
            desired_dir = 1 if move_dir.x > 0 else -1
            
            if abs(self.facing_direction - desired_dir) < 0.2:
                self.loss_timer += time.dt
                
                if self.loss_timer >= self.loss_cooldown:
                    print(f"[BEHAVIOR] Minęło {self.loss_cooldown}s obserwacji. Powrót do idle.")
                    self.last_seen_position = None
                    self.loss_timer = 0.0
                    target_pos = None

        # Stan C: Prawdziwy, czysty Tryb Idle (Włączany tylko, gdy powyższe są nieaktywne)
        else:
            self.loss_timer = 0.0  # Czyszczenie na wszelki wypadek
            self.fov = self.fov_default
            
            self.idle_turn_timer += time.dt
            if self.idle_turn_timer >= self.idle_turn_cooldown:
                self.target_direction = -1 if self.target_direction == 1 else 1
                self.idle_turn_timer = 0.0

        # Wyznaczenie docelowego kierunku na podstawie aktywnego celu (Gracz / Ostatnia pozycja)
        # Ignorujemy to, jeśli trwa skanowanie (pomiędzy Stanem A a B)
        if target_pos is not None and self.detection_timer == 0.0:
            move_dir = target_pos - self.position
            if move_dir.x > 0.002:
                self.target_direction = 1
            elif move_dir.x < -0.002:   
                self.target_direction = -1
    
    def play_animation(self, anim_name):
        if self.current_anim != anim_name:
            self.current_anim = anim_name
            self.frame = self.animations[anim_name][0] # Reset do pierwszej klatki nowej animacji

    def update(self):
        super().update()
        self.check_player_detection()
        self.handle_behavior()
        
        # Zapamiętujemy stary kierunek
        old_dir = self.facing_direction
        # Wykonujemy obrót
        self.facing_direction = lerp(self.facing_direction, self.target_direction, time.dt * self.rotation_speed)
        
        # Jeśli różnica między kierunkami jest duża (oko jest w trakcie intensywnego obrotu),
        # lub jeśli przechodzi przez zero:
        is_turning = abs(self.facing_direction) < 0.5  # Oko "patrzy" w bok, gdy jest blisko 0
        
        # 1. Wybór stanu
        if is_turning:
            new_anim = "turning"
        elif self.current_zone is not None:
            new_anim = "detect"
        elif self.last_seen_position is not None:
            new_anim = "search"
        else:
            new_anim = "idle"
            
        start, end = self.animations[new_anim]
        
        # ... reszta kodu (reset, obliczanie klatki, renderowanie)
        # Reset przy zmianie animacji
        if self.current_anim != new_anim:
            self.current_anim = new_anim
            self.frame = start
            
        # 2. Animacja
        # Jeśli to turning, nie zapętlajmy w nieskończoność, tylko odtwórzmy raz 
        # (albo użyj modulo, jeśli wolisz szybkie zapętlenie)
        elapsed = int(time.time() * 7)
        self.frame = start + (elapsed % (end - start + 1))
        
        # 3. Renderowanie
        col = self.frame % self.num_cols
        row = self.frame // self.num_cols
        
        sx = 1 / self.num_cols
        sy = 1 / self.num_rows
        
        # ZMYSŁOWE OKREŚLENIE KIERUNKU:
        # Używamy target_direction (docelowego), albo sprawdzamy znak facing_direction
        # Ale robimy to raz, aby nie "drżało" podczas lerpowania
        direction_sign = -1 if self.facing_direction >= 0 else 1
        
        # OBLICZANIE WIERZA (Uwaga: sprawdź czy to działa, jeśli oko jest do góry nogami, zamień na row = row_from_top)
        row_from_top = self.frame // self.num_cols
        row = (self.num_rows - 1) - row_from_top
        col = self.frame % self.num_cols
        
        # Renderowanie
        if direction_sign >= 0: 
            self.texture_scale = (sx, sy)
            self.texture_offset = (col * sx, row * sy)
        else: 
            self.texture_scale = (-sx, sy)
            self.texture_offset = ((col + 1) * sx, row * sy)
            
        self.last_direction = self.facing_direction
        self.update_zone_visuals()