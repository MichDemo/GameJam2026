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

        self.start_position = Vec2(position[0], position[1])
        self.original_size = Vec2(size[0], size[1])

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
        self.ground_check_distance = ground_check_distance
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
        feet_left = self.left + self.foot_inset
        feet_right = self.right - self.foot_inset

        if feet_left >= feet_right:
            feet_left = self.left
            feet_right = self.right

        return (
            feet_right > self.entity_left(entity) + self.EPSILON and
            feet_left < self.entity_right(entity) - self.EPSILON
        )

    def is_standing_on(self, entity):
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

            # Floor should not act like a wall.
            if self.is_standing_on(entity):
                continue

            if self.is_colliding_with(entity):
                return entity

        return None

    def get_ground_below(self):
        for entity in self.get_solids():
            if not entity.enabled:
                continue

            if not self.feet_overlap(entity):
                continue

            distance_to_ground = self.bottom - self.entity_top(entity)

            if -self.EPSILON <= distance_to_ground <= self.ground_check_distance:
                return entity

        return None

    # --------------------------------------------------
    # Resizing
    # --------------------------------------------------

    def resize_keep_feet(self, new_size, allow_if_blocked=False):
        """
        Resizes Rat while keeping bottom/feet in the same world position.

        new_size must be Vec2(width, height).
        """

        old_position = Vec2(self.x, self.y)
        old_scale = Vec2(self.scale_x, self.scale_y)
        old_bottom = self.bottom

        self.scale = (new_size.x, new_size.y, 1)
        self.y = old_bottom + self.half_height

        hit = self.get_vertical_collision() or self.get_horizontal_collision()

        if hit and not allow_if_blocked:
            self.scale = (old_scale.x, old_scale.y, 1)
            self.position = (old_position.x, old_position.y, 0)
            return False

        return True

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
                    self.y = self.entity_top(hit) + self.half_height
                    self.grounded = True

                elif step_y > 0:
                    self.y = self.entity_bottom(hit) - self.half_height
                    self.grounded = False

                self.velocity_y = 0
                break

    def move(self, direction):
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
        self.position = (self.start_position.x, self.start_position.y, 0)
        self.velocity_y = 0
        self.grounded = False

    def check_fall_limit(self):
        if self.y < self.fall_limit:
            self.reset_position()

    def update(self):
        self.apply_gravity()
        self.check_fall_limit()