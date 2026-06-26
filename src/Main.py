from ursina import *
from Enemy import Enemy
from Player import *
from Block import *
from Fur import Fur
from Vent import Vent



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

# test_enemy = Enemy(
#         player=player,
#         position=(2, -2),
#         size=(1, 1),
#         zone_radii=(2.0, 4.0, 6.0),
#         fov_degrees=110,
#         color=color.red,
#         use_gravity=True,
#         solid_objects=[floor],
#         show_zones=True  # <-- Set to True to visualize zones
#     )



# --------------------------------------------------
# --- TESTOWE FUTRO ---
# --------------------------------------------------

# Ustawiamy je w zasięgu gracza (np. na podłodze obok niego)
# testowe_futro = Fur(
#     player=player,
#     position=(-3, -2),
#     hold_time=6.0  # Wymagane x sekund trzymania "E"
# )
#
# camera.orthographic = True
# camera.fov = 10



# --------------------------------------------------
# --- TESTOWE VENTY ---
# --------------------------------------------------

# 1. pierwszy wentyl (np. po lewej stronie)
vent_start = Vent(
    player=player,
    position=(-5, -2),
    color=color.magenta
)

# 2. drugi wentyl
vent_end = Vent(
    player=player,
    position=(5, -2),
    color=color.cyan
)

# 3. Łączymy je (ustawiamy cele podróży)
vent_start.target_vent = vent_end
vent_end.target_vent = vent_start # Dzięki temu można wracać

# Ustawienia kamery zgodne ze źródłami [2]
camera.orthographic = True
camera.fov = 10



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


