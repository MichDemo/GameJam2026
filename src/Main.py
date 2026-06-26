from ursina import *
from Player import *
from Block import *

app = Ursina()

player = Player(position=(-2,0), size=(1,1), color=color.orange, use_gravity=True, jump_force=15)

floor = Block(position=(0, -3), size=(10, 1))
przeskoda = Block(position=(0, -1.5), size=(1, 3))


# --------------------------------------------------
# Camera settings
# --------------------------------------------------
camera.orthographic = True
camera.fov = 10
camera.position = (0, 0, -20)
camera.rotation = (0, 0, 0)

app.run()


