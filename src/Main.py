# ==========================================
# PLIK: gra.py
# ==========================================
from ursina import *
from Enemy import Enemy
from Player import Player  # Upewnij się, że importujesz konkretne klasy
from Block import Block

def uruchom_scene_gry(game_container):
    # Tworzymy podłogę i przeszkody, przypisując je do game_container
    floor = Block(position=(0, -3), size=(100, 1), parent=game_container)
    przeskoda = Block(position=(0, -1.5), size=(1, 3), parent=game_container)
    
    # Tworzymy gracza
    player = Player(
        position=(0, 2),
        size=(1, 1),
        color=color.orange,
        speed=15,
        jump_force=15,
        use_gravity=True,
        solid_objects=[floor, przeskoda],
        parent=game_container # Przypisanie do kontenera gry
    )

    # Tworzymy przeciwnika
    test_enemy = Enemy(
        player=player, 
        position=(2, -2), 
        size=(1, 1),
        zone_radii=(2.0, 5.0, 7.0),
        fov_degrees=110,
        color=color.red,
        use_gravity=True,
        solid_objects=[floor, przeskoda],
        show_zones=True,
        parent=game_container # Przypisanie do kontenera gry
    )
    
    # --------------------------------------------------
    # Ustawienia Kamery
    # --------------------------------------------------
    camera.orthographic = True
    camera.fov = 10
    camera.position = (0, 0, -20)
    camera.rotation = (0, 0, 0)
    camera.parent = player  # Przyczepienie kamery do gracza
    
    # Dodajemy niebo do kontenera gry
    Sky(parent=game_container)
    
    print("Gra została pomyślnie załadowana!")