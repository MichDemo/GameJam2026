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

    # --------------------------------------------------
    # Kolizja robi brrr
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
    @property
    def left(self):
        return self.x - self.scale_x / 2

    @property
    def right(self):
        return self.x + self.scale_x / 2

    @property
    def bottom(self):
        return self.y - self.scale_y / 2

    @property
    def top(self):
        return self.y + self.scale_y / 2

    def get_entity_bounds(self, entity):
        return {
            "left": entity.x - entity.scale_x / 2,
            "right": entity.x + entity.scale_x / 2,
            "bottom": entity.y - entity.scale_y / 2,
            "top": entity.y + entity.scale_y / 2,
        }

    def is_colliding_with(self, entity):
        bounds = self.get_entity_bounds(entity)

        return (
            self.right > bounds["left"] and
            self.left < bounds["right"] and
            self.top > bounds["bottom"] and
            self.bottom < bounds["top"]
        )

    def get_collision(self):
        for entity in self.get_solids():
            if self.is_colliding_with(entity):
                return entity

        return None

    # --------------------------------------------------
    # Movement postaci
    # --------------------------------------------------

    def move_x(self, direction_x):
        if direction_x == 0:
            return

        dx = direction_x * self.speed * time.dt

        steps = max(1, int(abs(dx) / 0.04))
        step_x = dx / steps

        for _ in range(steps):
            old_x = self.x
            self.x += step_x

            if self.get_collision():
                self.x = old_x
                break

    def move_y(self, dy):
        if dy == 0:
            return

        steps = max(1, int(abs(dy) / 0.04))
        step_y = dy / steps

        for _ in range(steps):
            old_y = self.y
            self.y += step_y

            if self.get_collision():
                self.y = old_y

                if step_y < 0:
                    self.grounded = True

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
    # Ogarnanie grawitacji + skoku wiary
    # --------------------------------------------------

    def apply_gravity(self):
        if not self.use_gravity:
            return

        self.grounded = False

        self.velocity_y -= self.gravity * time.dt
        self.velocity_y = max(self.velocity_y, -self.max_fall_speed)

        dy = self.velocity_y * time.dt
        self.move_y(dy)

    def jump(self):
        if not self.use_gravity:
            return

        if self.grounded:
            self.velocity_y = self.jump_force
            self.grounded = False

    # --------------------------------------------------
    # W przypadku jak coś wyleci za mapę to tepa na mape. TODO : Przerobić na usuwanie obiektu z egzystencji
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
