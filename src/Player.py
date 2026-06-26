from panda3d.core import Vec2
from ursina import held_keys

from Rat import *
class Player(Rat):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update(self):
        # horizontal movement
        direction_x = 0

        if held_keys['a'] or held_keys['left arrow']:
            direction_x -= 1

        if held_keys['d'] or held_keys['right arrow']:
            direction_x += 1

        self.move_x(direction_x)

        # jump
        if held_keys['space']:
            self.jump()

        # gravity + safety
        super().update()