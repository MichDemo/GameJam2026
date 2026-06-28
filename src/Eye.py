import math
from ursina import *
from Rat import Rat

class Eye(Rat):
    def __init__(
        self, 
        player=None, 
        facing_direction=1, 
        zone_radius=4.5,          
        fov_degrees=120, 
        show_zones=False,  
        detection_delay=2.0,  
        **kwargs
    ):
        super().__init__(**kwargs)

        # --- KONFIGURACJA SPRITESHEET OKA ---
        self.texture = load_texture("EYE_ENEMY") 
        self.num_cols = 4  
        self.num_rows = 4  
        self.total_frames = 13 
        self.frame = 0
        
        self.texture_scale = (1/self.num_cols, 1/self.num_rows)
        self.color = color.white
        
        self.player = player
        self.facing_direction = facing_direction  
        self.zone_radius = zone_radius          
        self.fov = fov_degrees
        self.fov_default = fov_degrees  

        self.animations = {
            "idle":    (0, 5),
            "turning": (6, 8),
            "detect":  (9, 10),
            "search":  (11, 12)
        }
        self.current_anim = "idle"
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
        self.zone_color = color.salmon   
        
        self.zone_visual = None                 
        self._init_zone_visuals()

        # --- INICJALIZACJA IKONY NAD GŁOWĄ (NOWOŚĆ / ZMIANA INDEKSÓW) ---
        self.icons_cols = 2  
        self.icons_rows = 1  
        
        # Definiujemy indeksy klatek w pliku GENERIC_ICONS.png
        self.exclamation_mark_frame = 0  # Wykrzyknik (indeks 0)
        self.question_mark_frame = 1     # Znak zapytania (indeks 1)

        self.icon_notifier = Entity(
            parent=self,              
            model="quad",
            texture=load_texture("GENERIC_ICONS"),
            position=(0, 0.8, -0.01), 
            scale=(0.4, 0.4),         
            enabled=False             
        )
        
        self.icon_notifier.texture_scale = (1 / self.icons_cols, 1 / self.icons_rows)
        # Domyślnie ustawiamy na znak zapytania
        self.update_icon_texture_offset(self.question_mark_frame)

    def update_icon_texture_offset(self, frame_index):
        """Dynamicznie zmienia wyświetlaną ikonę na podstawie podanego indeksu klatki"""
        col = frame_index % self.icons_cols
        row = frame_index // self.icons_cols
        sx = 1 / self.icons_cols
        sy = 1 / self.icons_rows
        self.icon_notifier.texture_offset = (col * sx, 1 - (row + 1) * sy)

    def _init_zone_visuals(self):
        self.zone_visual = Entity(
            model='quad',
            color=self.zone_color,
            always_on_top=False,
            z=0.05
        )

    def update_zone_visuals(self):
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
        target_pos = None

        if self.current_zone is not None:
            self.idle_turn_timer = 0.0
            self.loss_timer = 0.0  
            target_pos = self.player.position
            self.fov = 360  
            self.last_seen_position = Vec3(self.player.x, self.player.y, self.player.z)

        elif self.detection_timer > 0.0:
            self.idle_turn_timer = 0.0
            self.loss_timer = 0.0

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

        else:
            self.loss_timer = 0.0  
            self.fov = self.fov_default
            
            self.idle_turn_timer += time.dt
            if self.idle_turn_timer >= self.idle_turn_cooldown:
                self.target_direction = -1 if self.target_direction == 1 else 1
                self.idle_turn_timer = 0.0

        if target_pos is not None and self.detection_timer == 0.0:
            move_dir = target_pos - self.position
            if move_dir.x > 0.002:
                self.target_direction = 1
            elif move_dir.x < -0.002:   
                self.target_direction = -1
    
    def play_animation(self, anim_name):
        if self.current_anim != anim_name:
            self.current_anim = anim_name
            self.frame = self.animations[anim_name][0] 

    def update(self):
        super().update()
        self.check_player_detection()
        self.handle_behavior()
        
        old_dir = self.facing_direction
        self.facing_direction = lerp(self.facing_direction, self.target_direction, time.dt * self.rotation_speed)
        
        is_turning = abs(self.facing_direction) < 0.5  
        
        if is_turning:
            new_anim = "turning"
        elif self.current_zone is not None:
            new_anim = "detect"
        elif self.last_seen_position is not None:
            new_anim = "search"
        else:
            new_anim = "idle"
            
        start, end = self.animations[new_anim]
        
        if self.current_anim != new_anim:
            self.current_anim = new_anim
            self.frame = start
            
        elapsed = int(time.time() * 7)
        self.frame = start + (elapsed % (end - start + 1))
        
        col = self.frame % self.num_cols
        row = self.frame // self.num_cols
        
        sx = 1 / self.num_cols
        sy = 1 / self.num_rows
        
        direction_sign = -1 if self.facing_direction >= 0 else 1
        
        row_from_top = self.frame // self.num_cols
        row = (self.num_rows - 1) - row_from_top
        col = self.frame % self.num_cols
        
        if direction_sign >= 0: 
            self.texture_scale = (sx, sy)
            self.texture_offset = (col * sx, row * sy)
            self.icon_notifier.scale_x = abs(self.icon_notifier.scale_x)
        else: 
            self.texture_scale = (-sx, sy)
            self.texture_offset = ((col + 1) * sx, row * sy)
            self.icon_notifier.scale_x = -abs(self.icon_notifier.scale_x)

        # --- DYNAMICZNA LOGIKA IKON (NOWOŚĆ) ---
        if self.current_zone is not None:
            # Stan 1: Gracz całkowicie wykryty -> Pokaż WYKRZYKNIK
            self.icon_notifier.enabled = True
            self.update_icon_texture_offset(self.exclamation_mark_frame)
            
        elif self.detection_timer > 0.0:
            # Stan 2: Trwa odliczanie/skanowanie -> Pokaż ZNAK ZAPYTANIA
            self.icon_notifier.enabled = True
            self.update_icon_texture_offset(self.question_mark_frame)
            
        else:
            # Stan 3: Czysto -> Ukryj ikonę
            self.icon_notifier.enabled = False
            
        self.last_direction = self.facing_direction
        self.update_zone_visuals()