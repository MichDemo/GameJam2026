from ursina import *
from Rat import Rat

class Player(Rat):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update(self):
        # Movement lewo / prawo
        direction_x = 0

        if held_keys['a'] or held_keys['left arrow']:
            direction_x -= 1

        if held_keys['d'] or held_keys['right arrow']:
            direction_x += 1

        self.move_x(direction_x)

        # Skok
        if held_keys['space']:
            self.jump()

        # Grawitacja + zabezpieczenie przed shadowrealmem
        super().update()