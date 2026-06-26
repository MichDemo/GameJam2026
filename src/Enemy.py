import math
from ursina import *
from Rat import Rat

class Enemy(Rat):
    def __init__(
        self, 
        player=None, 
        facing_direction=1, 
        zone_radii=(2.0, 4.5, 7.0), 
        fov_degrees=120, 
        show_zones=False,  # <-- Added a default parameter to control visibility
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.player = player
        self.facing_direction = facing_direction  # 1 = Right, -1 = Left
        self.zone_radii = zone_radii
        self.fov = fov_degrees
        self.fov_default = fov_degrees  
        
        self.current_zone = None  
        self.last_seen_position = None  
        
        self.show_zones = show_zones  # <-- Tracks whether zones should be drawn
        
        # Zone presentation styling (Switched to your custom pastel palette!)
        self.zone_colors = [
            color.salmon,   # Zone 1 (Red)
            color.yellow,   # Zone 2 (Orange)
            color.lime      # Zone 3 (Green)
        ]
        
        self.zone_visuals = []
        self._init_zone_visuals()

    def _init_zone_visuals(self):
        for i, radius in enumerate(self.zone_radii):
            visual = Entity(
                model='quad',
                color=self.zone_colors[i],
                always_on_top=False,
                z=0.05
            )
            self.zone_visuals.append(visual)

    def update_zone_visuals(self):
        for i, radius in enumerate(self.zone_radii):
            visual = self.zone_visuals[i]
            
            # --- TOGGLE CHECK ---
            # If show_zones is False, turn off the entity rendering and skip math calculations
            if not self.show_zones:
                visual.enabled = False
                continue
            
            # Otherwise, ensure the entity is active and update its transformations
            visual.enabled = True
            
            # If FOV expands to 360, change visual zones to center completely around the enemy
            if self.fov >= 360:
                visual.position = self.position + Vec3(0, 0, 0.05)
                visual.scale = (radius * 2, radius * 2, 1)
            else:
                # Normal directional cone visualization
                offset_x = (radius / 2) * self.facing_direction
                visual.position = self.position + Vec3(offset_x, 0, 0.05)
                vertical_reach = radius * math.sin(math.radians(self.fov / 2)) * 2
                visual.scale = (radius, max(vertical_reach, 1.0), 1)

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

        detected_zone = None
        if is_in_vision_cone:
            if distance <= self.zone_radii[0]:
                detected_zone = 1
            elif distance <= self.zone_radii[1]:
                detected_zone = 2
            elif distance <= self.zone_radii[2]:
                detected_zone = 3

        if detected_zone != self.current_zone:
            if detected_zone is not None:
                print(f"[ALERT] Player ENTERED Detection Zone {detected_zone}!")
            else:
                print(f"[ALERT] Player LEFT all detection zones. Moving to last seen position!")
            self.current_zone = detected_zone

    # --------------------------------------------------
    # AI Behavior & Movement Logic
    # --------------------------------------------------
    
    def handle_behavior(self):
        """Processes current tracking state to determine movement vectors."""
        target_pos = None

        # State A: Player is detected in a zone -> Chase and log coordinates
        if self.current_zone is not None:
            # Respects your zone 3 warning filter rule
            if self.current_zone != 3:
                target_pos = self.player.position
                self.fov = 360  
                self.last_seen_position = Vec3(self.player.x, self.player.y, self.player.z)

        # State B: Player is lost -> Head towards the last known coordinates
        elif self.last_seen_position is not None:
            self.fov = self.fov_default  
            target_pos = self.last_seen_position
            
            # Check arrival proximity tolerances
            horizontal_dist = abs(self.x - self.last_seen_position.x)
            vertical_dist = abs(self.y - self.last_seen_position.y) if not self.use_gravity else 0
            
            # If close enough to target point, drop interest tracking
            if horizontal_dist < 0.15 and vertical_dist < 0.15:
                print("[BEHAVIOR] Arrived at last seen location. Returning to idle.")
                self.last_seen_position = None
                target_pos = None

        # Execute movement commands towards the active target coordinate
        if target_pos is not None:
            move_dir = target_pos - self.position
            
            # Dynamic Turn: Face the direction of target pursuit
            if move_dir.x > 0.002:
                self.facing_direction = 1
            elif move_dir.x < -0.002:
                self.facing_direction = -1

            # Build platform safe/top-down safe vectors using your base model
            if self.use_gravity:
                move_vector = Vec2(1 if move_dir.x > 0 else -1, 0)
            else:
                move_vector = Vec2(move_dir.x, move_dir.y).normalized()

            self.move(move_vector)

    def update(self):
        super().update()
        
        # Check vision status, then run AI behavior state machine
        self.check_player_detection()
        self.handle_behavior()
        
        # Render visual elements
        self.texture_scale = (self.facing_direction, 1)
        self.update_zone_visuals()