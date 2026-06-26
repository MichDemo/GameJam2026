from ursina import *
from Player import *
from Block import *

app = Ursina()

floor = Block(position=(0, -3), size=(10, 1))
przeskoda = Block(position=(0, -1.5), size=(1, 3))
player = Player(
    position=(0, 2),
    size=(1, 1),
    color=color.orange,
    speed=5,
    jump_force=15,
    use_gravity=True,
    solid_objects=[floor, przeskoda]
)


# --------------------------------------------------
# Camera settings
# --------------------------------------------------
camera.orthographic = True
camera.fov = 10
camera.position = (0, 0, -20)
camera.rotation = (0, 0, 0)

app.run()


