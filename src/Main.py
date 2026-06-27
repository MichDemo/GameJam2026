import os
import json
from ursina import *

# Importy klas
from Block import Block
from Enemy import Enemy
from Eye import Eye
from Fur import Fur
from Player import Player
from Vent import Vent

app = Ursina()

# 1. Dynamiczne wyznaczenie poprawnej ścieżki do pliku JSON
def load_map_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    full_path = os.path.join(project_root, "assets", "maps", "level_5.json")
    
    print(f"--- Wczytuję mapę z: {full_path} ---")
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)

map_data = load_map_data()

# --------------------------------------------------
# --- POZYCJA STARTOWA GRACZA ---
# --------------------------------------------------
if map_data.get("player"):
    player_start_x = map_data["player"]["x"]
    player_start_y = map_data["player"]["y"]
elif map_data.get("furs"):
    player_start_x = map_data["furs"][0]["x"]
    player_start_y = map_data["furs"][0]["y"]
elif map_data.get("blocks"):
    player_start_x = map_data["blocks"][0]["x"]
    player_start_y = map_data["blocks"][0]["y"]
else:
    player_start_x = 0.0
    player_start_y = 0.0

print(f"--- Start gracza na dokładnych współrzędnych: ({player_start_x}, {player_start_y}) ---")

# Inicjalizacja pustych struktur danych, żeby były widoczne w całym skrypcie
all_blocks = []
created_vents = {}

# --------------------------------------------------
# --- TWORZENIE GRACZA ---
# --------------------------------------------------
player = Player(
    position=(player_start_x, player_start_y),
    size=(1, 1),
    color=color.orange,
    speed=10,
    jump_force=15,
    use_gravity=True,
    solid_objects=[],  
    camera_follow=True,
    camera_offset=(0, 0),
    camera_z=-20
)

# --------------------------------------------------
# --- GENEROWANIE BLOKÓW ---
# --------------------------------------------------
for b in map_data.get("blocks", []):
    pos = (b["x"], b["y"])  
    size = (b["scale_x"], b["scale_y"])
    block_obj = Block(position=pos, size=size, hex_color=b.get("hex_color"))
    all_blocks.append(block_obj)  # <--- TUTAJ dodajemy blok do listy!

# Przekazujemy klocki graczowi
player.solid_objects = all_blocks

# --------------------------------------------------
# --- GENEROWANIE FUTER ---
# --------------------------------------------------
all_furs = []  # Tworzymy listę, w której będziemy trzymać obiekty futer

for f in map_data.get("furs", []):
    pos = (f["x"], f["y"])  
    fur_obj = Fur(player=player, position=pos, hold_time=0.6)
    all_furs.append(fur_obj)  # Dodajemy każde stworzone futro do listy

# Początkowa liczba futer na mapie
total_furs = len(all_furs)
print(f"--- Znaleziono futer na mapie: {total_furs} ---")
# --------------------------------------------------
# --- GENEROWANIE PRZECIWNIKÓW ----
# --------------------------------------------------
for e in map_data.get("enemies", []):
    pos = (e["x"], e["y"])  
    size = (e["scale_x"], e["scale_y"])
    radii = (e["zone1"], e["zone2"], e["zone3"])
    
    enemy_color = Block.hex_to_ursina_color(e["hex_color"]) if "hex_color" in e else color.red

    Enemy(
        player=player,
        position=pos,
        size=size,
        zone_radii=radii,
        fov_degrees=110,
        color=enemy_color,
        use_gravity=True,
        solid_objects=all_blocks,
        show_zones=True
    )

# --------------------------------------------------
# --- GENEROWANIE OCZU ---
# --------------------------------------------------
for eye_data in map_data.get("eyes", []):
    pos = (eye_data["x"], eye_data["y"])  

    eye_obj = Eye(
        player=player,
        position=pos,
        size=(1, 1),
        zone_radii=(2.0, 4.0, 6.0),
        fov_degrees=110,
        color=color.red,
        use_gravity=False,
        solid_objects=all_blocks,  # <--- I tutaj też działa
        show_zones=True
    )
    if hasattr(eye_obj, "rotation_time"):
        eye_obj.rotation_time = eye_data["rotation_time"]

# --------------------------------------------------
# --- GENEROWANIE WENTYLI ---
# --------------------------------------------------
for v in map_data.get("vents", []):
    pos = (v["x"], v["y"])  
    vent_obj = Vent(player=player, position=pos, color=color.cyan)
    created_vents[v["vent_id"]] = {"obj": vent_obj, "target_id": v["target_vent_id"]}

for vent_id, info in created_vents.items():
    current_vent = info["obj"]
    target_id = info["target_id"]
    if target_id in created_vents:
        current_vent.target_vent = created_vents[target_id]["obj"]

# --------------------------------------------------
# --- URUCHOMIENIE ---
# --------------------------------------------------
camera.orthographic = True
camera.fov = 12
camera.parent = scene

have_won = False

def update():
    global all_furs, total_furs, have_won  # <--- Dodajemy total_furs i have_won do global
    
    # Filtrujemy aktywne futra
    all_furs = [f for f in all_furs if f and f.enabled]
    
    furs_left = len(all_furs)
    collected_furs = total_furs - furs_left

    # Aktualizacja tekstu na ekranie
    licznik_tekst.text = f'Futra: {collected_furs}/{total_furs}'
    
    # Sprawdzamy warunek wygranej
    if furs_left == 0 and total_furs > 0 and not have_won:
        have_won = True  # Zmieniamy na True – teraz ten IF wykona się TYLKO RAZ
        print("You've got all the Furs! Wygrałeś!")
        
        # Opcjonalnie: możesz wyświetlić wielki napis na środku ekranu
        Text(text="WYGRAŁEŚ!", scale=5, origin=(0, 0), color=color.green)

Sky()

licznik_tekst = Text(text=f'Futra: 0/{total_furs}', position=(-0.8, 0.45), scale=2)

app.run()