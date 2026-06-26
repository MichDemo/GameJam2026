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
        
        self.player = player
        self.facing_direction = facing_direction  
        self.zone_radius = zone_radius          # <-- ZMIANA: Jeden promień
        self.fov = fov_degrees
        self.fov_default = fov_degrees  
        
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

        # --- ZMIANA: Filtrowanie oparte o jeden promień ---
        raw_zone = None
        if is_in_vision_cone and distance <= self.zone_radius:
            raw_zone = 1

        if raw_zone is not None:
            self.potential_zone = raw_zone

            if self.current_zone is None:
                if self.detection_timer == 0.0:
                    print(f"[SKANOWANIE] Gracz namierzony. Rozpoczęto odliczanie {self.detection_delay} sekund...")
                
                self.detection_timer += time.dt
                
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

        # Stan A: Gracz wykryty (Usunięto warunek zone != 3)
        if self.current_zone is not None:
            self.idle_turn_timer = 0.0
            self.loss_timer = 0.0  
            target_pos = self.player.position
            self.fov = 360  
            self.last_seen_position = Vec3(self.player.x, self.player.y, self.player.z)

        # Stan B: Gracz zgubiony
        elif self.last_seen_position is not None:
            self.idle_turn_timer = 0.0
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

        # Stan C: Tryb Idle
        else:
            self.fov = self.fov_default
            self.idle_turn_timer += time.dt
            if self.idle_turn_timer >= self.idle_turn_cooldown:
                self.target_direction = -1 if self.target_direction == 1 else 1
                self.idle_turn_timer = 0.0

        if target_pos is not None:
            move_dir = target_pos - self.position
            if move_dir.x > 0.002:
                self.target_direction = 1
            elif move_dir.x < -0.002:
                self.target_direction = -1

    def update(self):
        super().update()
        self.check_player_detection()
        self.handle_behavior()
        
        self.facing_direction = lerp(self.facing_direction, self.target_direction, time.dt * self.rotation_speed)
        self.texture_scale = (1 if self.facing_direction >= 0 else -1, 1)
        self.update_zone_visuals()