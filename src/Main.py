import os
import json
from ursina import *

# Importy Twoich klas
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
    full_path = os.path.join(project_root, "assets", "maps", "level.json")
    
    print(f"--- Wczytuję mapę z: {full_path} ---")
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)

map_data = load_map_data()

OFFSET_X = 128.0
OFFSET_Y = 128.0

# --------------------------------------------------
# --- TWORZENIE GRACZA ---
# --------------------------------------------------
print("--- [1/6] Tworzenie Gracza ---")
player_start_x = 128.5 - OFFSET_X
player_start_y = 128.5 - OFFSET_Y

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

all_blocks = []
created_vents = {}

# --------------------------------------------------
# --- GENEROWANIE BLOKÓW ---
# --------------------------------------------------
print(f"--- [2/6] Generowanie bloków (Znaleziono: {len(map_data.get('blocks', []))}) ---")
for i, b in enumerate(map_data.get("blocks", [])):
    pos = (b["x"] - OFFSET_X, b["y"] - OFFSET_Y)
    size = (b["scale_x"], b["scale_y"])
    block_obj = Block(position=pos, size=size, hex_color=b.get("hex_color"))
    all_blocks.append(block_obj)

player.solid_objects = all_blocks

# --------------------------------------------------
# --- GENEROWANIE FUTER ---
# --------------------------------------------------
print(f"--- [3/6] Generowanie futer (Znaleziono: {len(map_data.get('furs', []))}) ---")
for f in map_data.get("furs", []):
    pos = (f["x"] - OFFSET_X, f["y"] - OFFSET_Y)
    fur_obj = Fur(
        player=player,
        position=pos,
        hold_time=2.0
    )

# --------------------------------------------------
# --- AWARYJNE GENEROWANIE PRZECIWNIKÓW ---
# --------------------------------------------------
print(f"--- [4/6] Generowanie enemies (Znaleziono: {len(map_data.get('enemies', []))}) ---")
for i, e in enumerate(map_data.get("enemies", [])):
    pos = (e["x"] - OFFSET_X, e["y"] - OFFSET_Y)
    
    # KROK 1: Test – tworzymy zwykłą encję Ursina zamiast Enemy, 
    # aby sprawdzić, czy to na pewno wina kodu w Enemy.py
    print(f"    -> Spawnowanie czystej encji testowej na pozycji {pos}...")
    Entity(model='quad', position=(pos[0], pos[1], 0), color=color.red, scale=(1,1))
    print(f"    -> Encja testowa {i} wygenerowana bez problemu.")

print("--- [4.5/6] Przejście przez sekcję wrogów udane! ---")

# --------------------------------------------------
# --- GENEROWANIE OCZU ---
# --------------------------------------------------
print(f"--- [5/6] Generowanie oczu (Znaleziono: {len(map_data.get('eyes', []))}) ---")
for eye_data in map_data.get("eyes", []):
    pos = (eye_data["x"] - OFFSET_X, eye_data["y"] - OFFSET_Y)

    eye_obj = Eye(
        player=player,
        position=pos,
        size=(1, 1),
        zone_radii=(2.0, 4.0, 6.0),
        fov_degrees=110,
        color=color.red,
        use_gravity=False,
        solid_objects=all_blocks,
        show_zones=True
    )
    if hasattr(eye_obj, "rotation_time"):
        eye_obj.rotation_time = eye_data["rotation_time"]

# --------------------------------------------------
# --- GENEROWANIE WENTYLI ---
# --------------------------------------------------
print(f"--- [6/6] Generowanie i łączenie wentyli (Znaleziono: {len(map_data.get('vents', []))}) ---")
for v in map_data.get("vents", []):
    pos = (v["x"] - OFFSET_X, v["y"] - OFFSET_Y)
    vent_obj = Vent(
        player=player,
        position=pos,
        color=color.cyan,
        hold_time=2.0
    )
    created_vents[v["vent_id"]] = {"obj": vent_obj, "target_id": v["target_vent_id"]}

for vent_id, info in created_vents.items():
    current_vent = info["obj"]
    target_id = info["target_id"]
    if target_id in created_vents:
        current_vent.target_vent = created_vents[target_id]["obj"]

# --------------------------------------------------
# --- USTAWIENIA KAMERY I URUCHOMIENIE ---
# --------------------------------------------------
print("--- Inicjalizacja kamery i start aplikacji... ---")
camera.orthographic = True
camera.fov = 12
camera.parent = scene

Sky()

app.run()