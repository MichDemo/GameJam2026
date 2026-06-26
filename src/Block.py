from ursina import *

class Block(Entity):
    def __init__(self, position=(0, 0), size=(1, 1), **kwargs):
        super().__init__(
            model='quad',
            position=(position[0], position[1], 0),
            scale=(size[0], size[1], 1),
            collider='box',
            **kwargs
        )