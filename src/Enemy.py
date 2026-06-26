from ursina import *
from Rat import Rat
import math


class Enemy(Rat):
    def __init__(
        self,
        player,
        position=(0, 0),
        size=(1, 1),
        speed=5,
        chase_speed=6,
        zone_radii=(1.0, 3.0, 6.0),
        fov_degrees=110,
        show_zones=False,
        **kwargs
    ):
        super().__init__(
            position=position,
            size=size,
            speed=speed,
            **kwargs
        )

        self.player = player

        self.chase_speed = chase_speed

        # Half-size values.
        # Full square zone would be radius * 2.
        # Front half-zone uses width = radius and height = radius * 2.
        self.zone1_radius = zone_radii[0]
        self.zone2_radius = zone_radii[1]
        self.zone3_radius = zone_radii[2]

        self.fov_degrees = fov_degrees

        self.show_zones = show_zones

        # Enemy looks right by default.
        self.facing_direction = Vec2(1, 0)

        self.is_chasing = False

        self.zone1_visual = None
        self.zone2_visual = None
        self.zone3_visual = None

        if self.show_zones:
            self.create_zone_visuals()

    # --------------------------------------------------
    # Zone visuals - QUADS ONLY
    # --------------------------------------------------

    def create_zone_visuals(self):
        """
        2D debug zones using quads only.
        No circles. No spheres.

        These are not parented to the enemy on purpose,
        so scale changes / transforms do not affect them weirdly.
        """

        self.zone3_visual = Entity(
            model='quad',
            color=color.rgba(0, 120, 255, 35),
            collider=None,
            z=0.30,
            enabled=True
        )

        self.zone2_visual = Entity(
            model='quad',
            color=color.rgba(255, 255, 0, 45),
            collider=None,
            z=0.20,
            enabled=True
        )

        self.zone1_visual = Entity(
            model='quad',
            color=color.rgba(255, 0, 0, 65),
            collider=None,
            z=0.10,
            enabled=True
        )

        self.update_zone_visuals()

    def get_facing_x(self):
        """
        Returns the horizontal direction enemy is facing.

        Platformer behavior:
        -  1 means facing right
        - -1 means facing left
        """

        if self.facing_direction.x < 0:
            return -1

        return 1

    def set_zone_as_front_half(self, zone, radius):
        """
        Draws only the half of the zone in front of the enemy.

        If facing right:
            zone covers from enemy.x to enemy.x + radius

        If facing left:
            zone covers from enemy.x - radius to enemy.x

        Uses quad only.
        """

        facing_x = self.get_facing_x()

        zone.enabled = True
        zone.scale = (radius, radius * 2, 1)
        zone.x = self.x + (facing_x * radius / 2)
        zone.y = self.y

    def set_zone_as_full_square(self, zone, radius):
        """
        Draws a full square zone centered on the enemy.
        Used during chase so Zone 3 behaves like a tracking/search area.
        """

        zone.enabled = True
        zone.scale = (radius * 2, radius * 2, 1)
        zone.x = self.x
        zone.y = self.y

    def update_zone_visuals(self):
        """
        Visual rules:

        NOT chasing:
            draw all 3 zones as front-facing half-quads.

        CHASING:
            draw all 3 zones as full quads,
            with Zone 3 highlighted because it is the tracking zone.
        """

        if not self.show_zones:
            return

        if not self.zone1_visual or not self.zone2_visual or not self.zone3_visual:
            return

        if self.is_chasing:
            self.set_zone_as_full_square(self.zone3_visual, self.zone3_radius)
            self.set_zone_as_full_square(self.zone2_visual, self.zone2_radius)
            self.set_zone_as_full_square(self.zone1_visual, self.zone1_radius)

            # Chasing state colors
            if self.is_player_in_zone_3():
                self.zone3_visual.color = color.rgba(0, 120, 255, 90)
            else:
                self.zone3_visual.color = color.rgba(0, 120, 255, 25)

            self.zone2_visual.color = color.rgba(255, 255, 0, 25)
            self.zone1_visual.color = color.rgba(255, 0, 0, 35)

            return

        # Idle / detection state.
        # All zones are visible, but only the front half is drawn.
        self.set_zone_as_front_half(self.zone3_visual, self.zone3_radius)
        self.set_zone_as_front_half(self.zone2_visual, self.zone2_radius)
        self.set_zone_as_front_half(self.zone1_visual, self.zone1_radius)

        if self.is_player_crouched():
            # Crouched player only cares about Zone 1,
            # but all zones remain visible for debugging.
            self.zone1_visual.color = (
                color.rgba(255, 0, 0, 95)
                if self.is_player_in_zone_1()
                else color.rgba(255, 0, 0, 55)
            )

            self.zone2_visual.color = color.rgba(255, 255, 0, 18)
            self.zone3_visual.color = color.rgba(0, 120, 255, 14)

            return

        # Standing player detection colors.
        self.zone1_visual.color = (
            color.rgba(255, 0, 0, 95)
            if self.is_player_in_zone_1()
            else color.rgba(255, 0, 0, 55)
        )

        self.zone2_visual.color = (
            color.rgba(255, 255, 0, 85)
            if self.is_player_in_zone_2()
            else color.rgba(255, 255, 0, 45)
        )

        self.zone3_visual.color = (
            color.rgba(0, 120, 255, 55)
            if self.is_player_in_zone_3()
            else color.rgba(0, 120, 255, 30)
        )

    # --------------------------------------------------
    # 2D helpers
    # --------------------------------------------------

    def get_player_position_2d(self):
        return Vec2(self.player.x, self.player.y)

    def get_enemy_position_2d(self):
        return Vec2(self.x, self.y)

    def get_direction_to_player(self):
        direction = self.get_player_position_2d() - self.get_enemy_position_2d()

        if direction.length() == 0:
            return Vec2(0, 0)

        return direction.normalized()

    def get_horizontal_direction_to_player(self):
        if self.player.x > self.x:
            return 1

        if self.player.x < self.x:
            return -1

        return 0

    # --------------------------------------------------
    # Zone detection
    # --------------------------------------------------

    def is_player_inside_full_square_zone(self, radius):
        """
        Full square zone centered on enemy.
        Used while chasing, mainly for Zone 3 tracking.
        """

        dx = abs(self.player.x - self.x)
        dy = abs(self.player.y - self.y)

        return dx <= radius and dy <= radius

    def is_player_inside_front_half_zone(self, radius):
        """
        Front-facing half-zone.

        If enemy faces right:
            player must be between enemy.x and enemy.x + radius.

        If enemy faces left:
            player must be between enemy.x - radius and enemy.x.

        Height remains radius * 2.
        """

        facing_x = self.get_facing_x()

        dx = self.player.x - self.x
        dy = abs(self.player.y - self.y)

        if dy > radius:
            return False

        if facing_x > 0:
            return 0 <= dx <= radius

        return -radius <= dx <= 0

    def is_player_in_zone_1(self):
        if self.is_chasing:
            return self.is_player_inside_full_square_zone(self.zone1_radius)

        return self.is_player_inside_front_half_zone(self.zone1_radius)

    def is_player_in_zone_2(self):
        if self.is_chasing:
            return self.is_player_inside_full_square_zone(self.zone2_radius)

        return self.is_player_inside_front_half_zone(self.zone2_radius)

    def is_player_in_zone_3(self):
        if self.is_chasing:
            return self.is_player_inside_full_square_zone(self.zone3_radius)

        return self.is_player_inside_front_half_zone(self.zone3_radius)

    # --------------------------------------------------
    # Player state
    # --------------------------------------------------

    def is_player_crouched(self):
        return getattr(self.player, "is_shrunk", False)

    # --------------------------------------------------
    # FOV
    # --------------------------------------------------

    def is_player_in_fov(self):
        """
        FOV check still exists, but since idle zones are already front-half
        this mostly acts as an extra angle safety gate.
        """

        direction_to_player = self.get_direction_to_player()

        if direction_to_player.length() == 0:
            return True

        if self.facing_direction.length() == 0:
            self.facing_direction = Vec2(1, 0)

        facing = self.facing_direction.normalized()
        target = direction_to_player.normalized()

        dot_value = facing.dot(target)
        dot_value = max(-1, min(1, dot_value))

        angle = math.degrees(math.acos(dot_value))

        return angle <= self.fov_degrees / 2

    # --------------------------------------------------
    # Behavior
    # --------------------------------------------------

    def should_start_chase(self):
        """
        Initial detection:

        Crouched player:
            Zone 1 front-half + FOV.

        Standing player:
            Zone 1 front-half + FOV
            or Zone 2 front-half + FOV.
        """

        if not self.is_player_in_fov():
            return False

        if self.is_player_crouched():
            return self.is_player_in_zone_1()

        if self.is_player_in_zone_1():
            return True

        if self.is_player_in_zone_2():
            return True

        return False

    def should_continue_chase(self):
        """
        Once chasing, enemy tracks using full Zone 3.
        FOV is not required here, otherwise chasing breaks.
        """

        return self.is_player_inside_full_square_zone(self.zone3_radius)

    def should_chase_player(self):
        if self.is_chasing:
            if self.should_continue_chase():
                return True

            self.is_chasing = False
            return False

        if self.should_start_chase():
            self.is_chasing = True
            return True

        return False

    # --------------------------------------------------
    # Movement
    # --------------------------------------------------

    def chase_player(self):
        direction_x = self.get_horizontal_direction_to_player()

        if direction_x == 0:
            return

        # While chasing, face the movement direction.
        self.facing_direction = Vec2(direction_x, 0)

        old_speed = self.speed
        self.speed = self.chase_speed

        self.move_x(direction_x)

        self.speed = old_speed

    # --------------------------------------------------
    # Update
    # --------------------------------------------------

    def update(self):
        if self.should_chase_player():
            self.chase_player()

        self.update_zone_visuals()

        super().update()