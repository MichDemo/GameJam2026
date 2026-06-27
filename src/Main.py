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
    full_path = os.path.join(project_root, "assets", "maps", "level_1.json")
    
    print(f"--- Wczytuję mapę z: {full_path} ---")
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)

map_data = load_map_data()

# --------------------------------------------------
# --- POZYCJA STARTOWA GRACZA ---
# --------------------------------------------------
if map_data.get("furs"):
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
for f in map_data.get("furs", []):
    pos = (f["x"], f["y"])  
    Fur(player=player, position=pos, hold_time=2.0)

# --------------------------------------------------
# --- GENEROWANIE PRZECIWNIKÓW (BEZPIECZNE EYE) ---
# --------------------------------------------------
for e in map_data.get("enemies", []):
    pos = (e["x"], e["y"])  
    size = (e["scale_x"], e["scale_y"])
    radii = (e["zone1"], e["zone2"], e["zone3"])
    
    enemy_color = Block.hex_to_ursina_color(e["hex_color"]) if "hex_color" in e else color.red

    Eye(
        player=player,
        position=pos,
        size=size,
        zone_radii=radii,
        fov_degrees=110,
        color=enemy_color,
        use_gravity=False,
        solid_objects=all_blocks,  # <--- Teraz ta zmienna już bezpiecznie istnieje
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

Sky()

app.run()