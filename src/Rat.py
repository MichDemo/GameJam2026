from ursina import *


class Rat(Entity):
    def __init__(
        self,
        position=(0, 0),
        size=(1, 1),
        speed=5,
        use_gravity=False,
        gravity=30,
        max_fall_speed=35,
        jump_force=12,
        solid_objects=None,
        auto_find_solids=True,
        fall_limit=-20,
        ground_check_distance=0.01,
        foot_inset=0.06,
        **kwargs
    ):
        super().__init__(
            model='quad',
            position=(position[0], position[1], 0),
            scale=(size[0], size[1], 1),
            collider='box',
            **kwargs
        )

        self.start_position = Vec3(position[0], position[1], 0)

        self.speed = speed

        self.use_gravity = use_gravity
        self.gravity = gravity
        self.max_fall_speed = max_fall_speed
        self.jump_force = jump_force

        self.velocity_y = 0
        self.grounded = False

        self.solid_objects = solid_objects
        self.auto_find_solids = auto_find_solids

        self.fall_limit = fall_limit

        # Tiny distance used only for checking if feet are touching ground.
        # Keep this small. Big values cause levitation.
        self.ground_check_distance = ground_check_distance

        # Prevents being grounded by barely touching a platform corner.
        self.foot_inset = foot_inset

        self.EPSILON = 0.0001

    # --------------------------------------------------
    # Solids
    # --------------------------------------------------

    def get_solids(self):
        if self.solid_objects is not None:
            return self.solid_objects

        if not self.auto_find_solids:
            return []

        solids = []

        for entity in scene.entities:
            if entity == self:
                continue

            if not hasattr(entity, "collider"):
                continue

            if entity.collider is None:
                continue

            if not entity.enabled:
                continue

            solids.append(entity)

        return solids

    # --------------------------------------------------
    # Bounds
    # --------------------------------------------------

    @property
    def half_width(self):
        return self.scale_x / 2

    @property
    def half_height(self):
        return self.scale_y / 2

    @property
    def left(self):
        return self.x - self.half_width

    @property
    def right(self):
        return self.x + self.half_width

    @property
    def bottom(self):
        return self.y - self.half_height

    @property
    def top(self):
        return self.y + self.half_height

    def entity_left(self, entity):
        return entity.x - entity.scale_x / 2

    def entity_right(self, entity):
        return entity.x + entity.scale_x / 2

    def entity_bottom(self, entity):
        return entity.y - entity.scale_y / 2

    def entity_top(self, entity):
        return entity.y + entity.scale_y / 2

    # --------------------------------------------------
    # Collision checks
    # --------------------------------------------------

    def horizontal_overlap(self, entity):
        return (
            self.right > self.entity_left(entity) + self.EPSILON and
            self.left < self.entity_right(entity) - self.EPSILON
        )

    def vertical_overlap(self, entity):
        return (
            self.top > self.entity_bottom(entity) + self.EPSILON and
            self.bottom < self.entity_top(entity) - self.EPSILON
        )

    def is_colliding_with(self, entity):
        return self.horizontal_overlap(entity) and self.vertical_overlap(entity)

    def feet_overlap(self, entity):
        """
        Uses narrower feet bounds than the full body.
        This prevents weird grounding on edges/corners.
        """
        feet_left = self.left + self.foot_inset
        feet_right = self.right - self.foot_inset

        # fallback if object is very small
        if feet_left >= feet_right:
            feet_left = self.left
            feet_right = self.right

        return (
            feet_right > self.entity_left(entity) + self.EPSILON and
            feet_left < self.entity_right(entity) - self.EPSILON
        )

    def is_standing_on(self, entity):
        """
        True only when the Rat is actually on top of this entity.
        Used to avoid treating floor as a wall during horizontal movement.
        """
        if not self.feet_overlap(entity):
            return False

        distance = self.bottom - self.entity_top(entity)

        return abs(distance) <= self.ground_check_distance + self.EPSILON

    def get_vertical_collision(self):
        for entity in self.get_solids():
            if not entity.enabled:
                continue

            if self.is_colliding_with(entity):
                return entity

        return None

    def get_horizontal_collision(self):
        for entity in self.get_solids():
            if not entity.enabled:
                continue

            # Important fix:
            # If we are standing on this object, it is floor, not wall.
            if self.is_standing_on(entity):
                continue

            if self.is_colliding_with(entity):
                return entity

        return None

    def get_ground_below(self):
        """
        Detects actual ground directly below the Rat.
        This replaces loose snapping that caused levitation.
        """
        for entity in self.get_solids():
            if not entity.enabled:
                continue

            if not self.feet_overlap(entity):
                continue

            entity_top = self.entity_top(entity)
            distance_to_ground = self.bottom - entity_top

            if -self.EPSILON <= distance_to_ground <= self.ground_check_distance:
                return entity

        return None

    # --------------------------------------------------
    # Movement
    # --------------------------------------------------

    def move_x(self, direction_x):
        if direction_x == 0:
            return

        dx = direction_x * self.speed * time.dt

        steps = max(1, int(abs(dx) / 0.025))
        step_x = dx / steps

        for _ in range(steps):
            self.x += step_x
            hit = self.get_horizontal_collision()

            if hit:
                if step_x > 0:
                    self.x = self.entity_left(hit) - self.half_width

                elif step_x < 0:
                    self.x = self.entity_right(hit) + self.half_width

                break

    def move_y(self, dy):
        if dy == 0:
            return

        steps = max(1, int(abs(dy) / 0.025))
        step_y = dy / steps

        for _ in range(steps):
            self.y += step_y
            hit = self.get_vertical_collision()

            if hit:
                if step_y < 0:
                    # Falling down. Snap exactly onto the object.
                    self.y = self.entity_top(hit) + self.half_height
                    self.grounded = True

                elif step_y > 0:
                    # Jumping up. Hit ceiling / underside.
                    self.y = self.entity_bottom(hit) - self.half_height
                    self.grounded = False

                self.velocity_y = 0
                break

    def move(self, direction):
        """
        Free 2D movement.
        Use this mainly when gravity is disabled.
        """
        if direction.length() == 0:
            return

        direction = direction.normalized()

        self.move_x(direction.x)

        if not self.use_gravity:
            self.move_y(direction.y * self.speed * time.dt)

    # --------------------------------------------------
    # Gravity / jump
    # --------------------------------------------------

    def apply_gravity(self):
        if not self.use_gravity:
            return

        # If moving upward, do not ground-snap.
        # This prevents jump from being cancelled.
        if self.velocity_y <= 0:
            ground = self.get_ground_below()

            if ground:
                self.y = self.entity_top(ground) + self.half_height
                self.velocity_y = 0
                self.grounded = True
                return

        self.grounded = False

        self.velocity_y -= self.gravity * time.dt
        self.velocity_y = max(self.velocity_y, -self.max_fall_speed)

        self.move_y(self.velocity_y * time.dt)

    def jump(self):
        if not self.use_gravity:
            return

        if self.grounded:
            self.velocity_y = self.jump_force
            self.grounded = False

    # --------------------------------------------------
    # Safety
    # --------------------------------------------------

    def reset_position(self):
        self.position = self.start_position
        self.velocity_y = 0
        self.grounded = False

    def check_fall_limit(self):
        if self.y < self.fall_limit:
            self.reset_position()

    def update(self):
        self.apply_gravity()
        self.check_fall_limit()