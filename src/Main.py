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

# --- DYNAMICZNE WYSZUKIWANIE PLIKÓW Z MAPAMI ---
def get_available_levels():
    """Skanuje folder assets/maps w poszukiwaniu plików JSON."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    maps_dir = os.path.join(project_root, "assets", "maps")
    
    if os.path.exists(maps_dir):
        return [f for f in os.listdir(maps_dir) if f.endswith('.json')]
    return []

# --- GLOBALNE ZMIENNE GRY ---
player = None
all_furs = []
total_furs = 0
have_won = False
licznik_tekst = None
ikona_futra = None  
game_active = False

# Referencje do UI menu (będą nadpisywane przy odbudowie)
main_menu = None
level_menu = None
menu_bg = None
level_buttons = []


# --------------------------------------------------
# --- INICJALIZACJA / ODBUDOWA MENU ---
# --------------------------------------------------
def init_ui(show_level_menu=False):
    """Buduje całą strukturę menu od zera (wywoływane na starcie i po czystce)."""
    global main_menu, level_menu, menu_bg
    
    # Tworzymy kontenery przypięte do UI kamery
    main_menu = Entity(parent=camera.ui, enabled=not show_level_menu)
    level_menu = Entity(parent=camera.ui, enabled=show_level_menu)

    # Tło menu głównego
    menu_bg = Sprite(
        parent=main_menu,
        texture='../assets/textures/szczur.png',       
        z=1,                     
        scale=(1.8, 1)          
    )

    # --- PRZYCISKI: MAIN MENU ---
    Text(parent=main_menu, text="MENU GŁÓWNE", scale=3, origin=(0, 0), y=0.3)

    Button(
        parent=main_menu, text='Graj', scale=(0.4, 0.1), y=0, 
        on_click=lambda: [main_menu.disable(), level_menu.enable(), refresh_level_menu()]
    )
    Button(
        parent=main_menu, text='Wyjdź', scale=(0.4, 0.1), y=-0.15, 
        on_click=application.quit
    )
    
    # Od razu przygotowujemy listę poziomów w kontenerze
    refresh_level_menu()


def refresh_level_menu():
    """Dynamicznie generuje przyciski map wewnątrz level_menu."""
    global level_buttons
    for b in level_buttons:
        destroy(b)
    level_buttons.clear()
    
    levels = get_available_levels()
    
    level_buttons.append(
        Text(parent=level_menu, text="Wybierz Poziom", scale=2, origin=(0, 0), y=0.3)
    )
    
    if not levels:
        level_buttons.append(
            Text(parent=level_menu, text="Nie znaleziono map w assets/maps!", scale=1.5, origin=(0, 0), y=0, color=color.red)
        )
    
    for i, level_file in enumerate(levels):
        display_name = level_file.replace('.json', '').replace('_', ' ').title()
        
        btn = Button(
            parent=level_menu,
            text=display_name,
            scale=(0.5, 0.08),
            y=0.1 - (i * 0.1),
            on_click=lambda lf=level_file: start_game(lf)
        )
        level_buttons.append(btn)
        
    btn_back = Button(
        parent=level_menu, text='Wstecz', scale=(0.2, 0.08), y=-0.3, color=color.dark_gray,
        on_click=lambda: [level_menu.disable(), main_menu.enable()]
    )
    level_buttons.append(btn_back)


# --------------------------------------------------
# --- SYSTEM RESETU I POWROTU ---
# --------------------------------------------------
def hard_reset_to_level_menu():
    """Brutalnie niszczy wszystko w silniku i stawia menu poziomów na czysto."""
    global game_active, player
    game_active = False
    player = None
    
    # Ostateczne rozwiązanie: czyści absolutnie całą pamięć sceny Ursina
    scene.clear()
    
    # Budujemy UI od zera, od razu włączając menu wyboru poziomów
    init_ui(show_level_menu=True)


# --------------------------------------------------
# --- ROZGRYWKA (START GAME) ---
# --------------------------------------------------
def start_game(map_filename):
    global player, all_furs, total_furs, have_won, licznik_tekst, ikona_futra, game_active
    
    # Chowamy menu
    level_menu.disable()
    if menu_bg: 
        menu_bg.disable()
        
    all_furs.clear()        
    total_furs = 0
    have_won = False
    game_active = True

    # Scieżka do wybranego JSON-a
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    full_path = os.path.join(project_root, "assets", "maps", map_filename)

    print(f"--- Wczytuję mapę z: {full_path} ---")
    with open(full_path, "r", encoding="utf-8") as f:
        map_data = json.load(f)

    # --- POZYCJA STARTOWA GRACZA ---
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

    all_blocks = []
    created_vents = {}

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


# --------------------------------------------------
# --- PĘTLA UPDATE ---
# --------------------------------------------------
def update():
    global all_furs, total_furs, have_won, licznik_tekst

    if not game_active:
        return

    all_furs = [f for f in all_furs if f and f.enabled]
    furs_left = len(all_furs)
    collected_furs = total_furs - furs_left

    if licznik_tekst:
        licznik_tekst.text = f'{collected_furs}/{total_furs}'

    if furs_left == 0 and total_furs > 0 and not have_won:
        have_won = True
        print("You've got all the Furs! Wygrałeś!")
        
        Text(text="WYGRAŁEŚ!", scale=5, origin=(0, 0), color=color.green)

        # Odpalamy brutalny reset z opóźnieniem
        invoke(hard_reset_to_level_menu, delay=3.0)

Sky()

# --- AUDIO ---
# autoplay=True sprawi, że muzyka ruszy od razu
# Inicjalizacja muzyki (autoplay=False, loop=True)
# music_house = Audio('assets/audio/dom.mp3', loop=True, autoplay=False)
music_sewers = Audio('../assets/audio/scieki_safezone.mp3', loop=True, autoplay=True)

licznik_tekst = Text(text=f'Futra: 0/{total_furs}', position=(-0.8, 0.45), scale=2)

app.run()
