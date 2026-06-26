from ursina import *
from Enemy import Enemy
from Player import *
from Block import *

app = Ursina()

floor = Block(position=(0, -3), size=(100, 1))
#przeskoda = Block(position=(0, -1.5), size=(1, 3))
player = Player(
    position=(0, 2),
    size=(1, 1),
    color=color.orange,
    speed=10,
    jump_force=15,
    use_gravity=True,
    solid_objects=[floor],
    camera_follow=True,
    camera_offset=(0, 0),
    camera_z=-20
)

test_enemy = Enemy(
        player=player, 
        position=(2, -2), 
        size=(1, 1),
        zone_radii=(2.0, 4.0, 6.0),
        fov_degrees=110,
        color=color.red,
        use_gravity=True,
        solid_objects=[floor],
        show_zones=True  # <-- Set to True to visualize zones
    )
# --------------------------------------------------
# Camera settings
# --------------------------------------------------
camera.orthographic = True
camera.fov = 10
camera.position = (0, 0, -20)
camera.rotation = (0, 0, 0)
camera.parent = scene

Sky()

app.run()


