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
    full_path = os.path.join(project_root, "assets", "maps", "level_dupa.json")
    
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
    # Wyciągamy dane z JSON-a
    pos = (b["x"], b["y"])  
    size = (b["scale_x"], b["scale_y"])
    
    # Pobieramy unikalny kod/indeks tekstury przypisany do bloku (domyślnie 0)
    t_index = b.get("tile_indices", 0)
    
    # Tworzymy blok
    block_obj = Block(position=pos, size=size, tile_indices=t_index, has_collision=b["has_collision"])
    print(f"Collision for block at {pos}: {b['has_collision']}")
    
    if "hex_color" in b:
        block_obj.color = color.hex(b["hex_color"]) 
        
    all_blocks.append(block_obj)

# Filtrujemy bloki! Przekazujemy graczowi TYLKO te, które mają włączoną kolizję.
solid_blocks = [block for block in all_blocks if block.has_collision]
player.solid_objects = solid_blocks

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
# --- GENEROWANIE PRZECIWNIKÓW ----sounds
# --------------------------------------------------
# Słownik mapujący kolory z pliku JSON na warianty spritów (na podstawie obraz.png)
color_to_variant = {
    "#ff0000": "horror",  # Czerwony -> RAT_ENEMY_HORROR.png
    "#ffffff": "white",   # Biały     -> RAT_ENEMY_WHITE.png
    "#8b5a2b": "brown",   # Brązowy   -> RAT_ENEMY_BROWN.png
    "#ffd700": "rich"     # Złoty     -> RAT_ENEMY_RICH.png
}

for e in map_data.get("enemies", []):
    pos = (e["x"], e["y"])
    size = (e["scale_x"], e["scale_y"])
    radii = (e["zone1"], e["zone2"], e["zone3"])

    # Pobieramy kolor z JSON-a (zamieniamy na małe litery dla pewności)
    hex_col = e.get("hex_color", "#ff0000").lower()

    # Wybieramy odpowiedni wariant sprita (jeśli brak w słowniku, domyślnie "brown")
    chosen_variant = color_to_variant.get(hex_col, "brown")

    Enemy(
        player=player,
        position=pos,
        size=size,
        zone1=e["zone1"], # Przekaż to jako osobne parametry
        zone2=e["zone2"],
        zone3=e["zone3"],
        fov_degrees=110,
        use_gravity=True,
        solid_objects=solid_blocks,  # <--- Podmieniono na solid_blocks (tylko bloki z kolizją)
        show_zones=False,
        variant=chosen_variant
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
        show_zones=False
    )
    if hasattr(eye_obj, "rotation_time"):
        eye_obj.rotation_time = eye_data["rotation_time"]

# --------------------------------------------------
# --- GENEROWANIE WENTYLI W MAIN.PY ---
# --------------------------------------------------
for v in map_data.get("vents", []):
    pos = (v["x"], v["y"])

    # Pobieramy współrzędne kafelka z JSON-a (zapisane przez edytor)
    # Jeśli ich nie ma w starym zapisie mapy, dajemy domyślne (np. 0, 0)
    tx = v.get("tile_x", 0)
    ty = v.get("tile_y", 0)

    # Tworzymy obiekt wentyla z dynamicznym kafelkiem z arkusza 32x32
    vent_obj = Vent(
        player=player,
        position=pos,
        tile_x=tx,
        tile_y=ty
    )

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

# --- AUDIO ---
# autoplay=True sprawi, że muzyka ruszy od razu
# Inicjalizacja muzyki (autoplay=False, loop=True)
# music_house = Audio('assets/audio/dom.mp3', loop=True, autoplay=False)
music_sewers = Audio('../assets/audio/scieki_safezone.mp3', loop=True, autoplay=True)

licznik_tekst = Text(text=f'Futra: 0/{total_furs}', position=(-0.8, 0.45), scale=2)

app.run()
