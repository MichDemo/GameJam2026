import os
import json
import pathlib
from ursina import *

# Importy klas dedykowanych
from Block import Block
from Enemy import Enemy
from Eye import Eye
from Fur import Fur
from Player import Player
from Vent import Vent

# 1. NAJPIERW kalkulujemy ścieżki, zanim wystartujemy silnik
current_dir = pathlib.Path(__file__).parent.resolve()          # GameJam2026/src
project_root = current_dir.parent                             # GameJam2026
correct_assets_path = project_root / "assets"

# 2. Przekazujemy właściwą ścieżkę bezpośrednio do konstruktora Ursina()
app = Ursina(asset_folder=correct_assets_path)
# --------------------------------------------------
# --- SFORMAZOWANIE ŚCIEŻEK ZASOBÓW (URYSNA ASSETS) ---
# --------------------------------------------------
current_dir = pathlib.Path(__file__).parent.resolve()          
project_root = current_dir.parent                             

# Wskazujemy główne zasoby projektu: GameJam2026/assets
application.asset_folder = project_root / "assets"

def get_available_levels():
    """Skanuje folder GameJam2026/assets/maps w poszukiwaniu plików JSON."""
    maps_dir = os.path.join(str(application.asset_folder), "maps")
    if os.path.exists(maps_dir):
        return sorted([f for f in os.listdir(maps_dir) if f.endswith('.json')])
    return []

# --- GLOBALNE ZMIENNE GRY ---
player = None
all_furs = []
total_furs = 0
have_won = False
have_lost = False             # <-- DODANO: Flaga przegranej (identyczna jak have_won)
licznik_tekst = None
ikona_futra = None  
game_active = False
napis_wygrana = None
napis_przegrana = None       # <-- Zmienna na napis porażki

# POPRAWIONE LISTY NA POTRZEBY CLEANUPU:
all_blocks = []
all_enemies = []
all_eyes = []
all_vents = []
game_sky = None 

# Referencje do muzyki
menu_music = None  
game_music = None  
win_music = None

# Referencje do UI menu
main_menu = None
level_menu = None
menu_bg = None
level_buttons = []


# --------------------------------------------------
# --- INICJALIZACJA / ODBUDOWA MENU ---
# --------------------------------------------------
def init_ui(show_level_menu=False):
    """Buduje całą strukturę menu od zera (wywoływane na starcie i po czystce)."""
    global main_menu, level_menu, menu_bg, menu_music
    
    main_menu = Entity(parent=camera.ui, enabled=not show_level_menu)
    level_menu = Entity(parent=camera.ui, enabled=show_level_menu)

    menu_bg = Sprite(
        parent=main_menu,
        texture='szczur',       
        z=1,                     
        scale=(1.8, 1)          
    )

    if not show_level_menu and menu_music is None:
        try:
            menu_music = Audio('glowne_menu', loop=True, autoplay=True)
        except Exception as e:
            print(f"Nie wyłapano audio menu: {e}")

    Text(parent=main_menu, text="MENU GŁÓWNE", scale=3, origin=(0, 0), y=0.3)

    Button(
        parent=main_menu, text='Graj', scale=(0.4, 0.1), y=0, 
        on_click=lambda: [main_menu.disable(), level_menu.enable(), refresh_level_menu()]
    )
    Button(
        parent=main_menu, text='Wyjdź', scale=(0.4, 0.1), y=-0.15, 
        on_click=application.quit
    )
    
    refresh_level_menu()


def refresh_level_menu():
    """Dynamicznie generuje przyciski map wewnątrz level_menu w siatce."""
    global level_buttons
    
    for b in level_buttons:
        if isinstance(b, Entity):
            destroy(b)
    level_buttons.clear()
    
    levels = get_available_levels()
    
    title = Text(parent=level_menu, text="Wybierz Poziom", scale=2.5, origin=(0, 0), y=0.4)
    level_buttons.append(title)
    
    if not levels:
        error_msg = Text(parent=level_menu, text="Nie znaleziono map w assets/maps!", scale=1.5, origin=(0, 0), y=0, color=color.red)
        level_buttons.append(error_msg)
    else:
        MAX_COLS = 3            
        BTN_WIDTH = 0.4         
        BTN_HEIGHT = 0.08       
        SPACING_X = 0.05        
        SPACING_Y = 0.04        
        START_Y = 0.22          
        
        total_grid_width = (MAX_COLS * BTN_WIDTH) + ((MAX_COLS - 1) * SPACING_X)
        start_x = -(total_grid_width / 2) + (BTN_WIDTH / 2) 
        
        for i, level_file in enumerate(levels):
            row = i // MAX_COLS
            col = i % MAX_COLS
            
            display_name = level_file.replace('.json', '').replace('_', ' ').title()
            
            pos_x = start_x + (col * (BTN_WIDTH + SPACING_X))
            pos_y = START_Y - (row * (BTN_HEIGHT + SPACING_Y))
            
            btn = Button(
                parent=level_menu,
                text=display_name,
                scale=(BTN_WIDTH, BTN_HEIGHT),
                position=(pos_x, pos_y),
                color=color.azure.tint(-0.2),
                on_click=lambda lf=level_file: start_game(lf)
            )
            
            if len(display_name) > 14:
                btn.text_entity.scale = 0.75
                
            level_buttons.append(btn)
        
    btn_back = Button(
        parent=level_menu, text='Wstecz do Menu', scale=(0.3, 0.08), position=(0, -0.4), color=color.dark_gray,
        on_click=lambda: [level_menu.disable(), main_menu.enable()]
    )
    level_buttons.append(btn_back)


def hard_reset_to_level_menu():
    """Niszczy precyzyjnie wszystkie obiekty gry i stawia menu na czysto."""
    global game_active, player, menu_music, game_music, win_music
    global all_blocks, all_enemies, all_eyes, all_vents, all_furs, game_sky, licznik_tekst, ikona_futra
    global napis_wygrana, napis_przegrana
    
    game_active = False
    
    if game_music:
        game_music.stop()
        destroy(game_music)
        game_music = None

    if win_music:
        win_music.stop()
        destroy(win_music)
        win_music = None
    
    if player:
        destroy(player)
        player = None
        
    if game_sky:
        destroy(game_sky)
        game_sky = None

    # Bezpieczne czyszczenie pętli za pomocą index-based loop chroniącej przed błędami stringów
    for item in list(all_blocks):
        if hasattr(item, 'enabled'): destroy(item)
    for item in list(all_enemies):
        if hasattr(item, 'enabled'): destroy(item)
    for item in list(all_eyes):
        if hasattr(item, 'enabled'): destroy(item)
    for item in list(all_vents):
        if hasattr(item, 'enabled'): destroy(item)
    for item in list(all_furs):
        if hasattr(item, 'enabled'): destroy(item)

    all_blocks.clear()
    all_enemies.clear()
    all_eyes.clear()
    all_vents.clear()
    all_furs.clear()

    if licznik_tekst:
        destroy(licznik_tekst)
        licznik_tekst = None
    if ikona_futra:
        destroy(ikona_futra)
        ikona_futra = None
        
    if napis_wygrana:
        destroy(napis_wygrana)
        napis_wygrana = None

    if napis_przegrana:
        destroy(napis_przegrana)
        napis_przegrana = None

    init_ui(show_level_menu=True)

# --------------------------------------------------
# --- ROZGRYWKA (START GAME) ---
# --------------------------------------------------
def start_game(map_filename):
    global player, all_furs, total_furs, have_won, have_lost, licznik_tekst, ikona_futra, game_active, menu_music, game_music, win_music
    global all_blocks, all_enemies, all_eyes, all_vents, game_sky
    
    if menu_music:
        menu_music.stop()
        destroy(menu_music)
        menu_music = None
    
    all_blocks.clear()
    all_enemies.clear()
    all_eyes.clear()
    all_vents.clear()
    all_furs.clear()        

    level_menu.disable()
    main_menu.disable()
        
    total_furs = 0
    have_won = False
    have_lost = False # Reset flagi przegranej
    game_active = True

    full_path = os.path.join(str(application.asset_folder), "maps", map_filename)

    print(f"--- Wczytuję mapę z: {full_path} ---")
    with open(full_path, "r", encoding="utf-8") as f:
        map_data = json.load(f)

    env_type = map_data.get("environment", "house").lower()
    print(env_type)

    env_music_mapping = {
        "house": "dom",
        "sewers": "muza_scieki_safezone" 
    }

    chosen_track = env_music_mapping.get(env_type, "dom")

    if game_music is None:
        try:
            game_music = Audio(f'audio/{chosen_track}', loop=True, autoplay=True)
            print(f"[Audio] Odpalam muzykę dla środowiska '{env_type}': audio/{chosen_track}")
        except Exception as e:
            print(f"Nie wyłapano audio poziomu ({chosen_track}): {e}")

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

    created_vents = {}

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

    # Bezpieczne przekazanie wyzwalacza przegranej dla wrogów i oczu
    def trigger_loss():
        global have_lost
        have_lost = True
    scene.game_over_func = trigger_loss

    # --- GENEROWANIE BLOKÓW ---
    for b in map_data.get("blocks", []):
        grid_pos = (b["x"], b["y"])
        block_size = (b["scale_x"], b["scale_y"])
        t_index = b.get("tile_indices", 0)

        block_obj = Block(position=grid_pos, size=block_size, tile_indices=t_index, has_collision=b["has_collision"])
        if "hex_color" in b:
            block_obj.color = color.hex(b["hex_color"])
            
        all_blocks.append(block_obj)

    solid_blocks = [block for block in all_blocks if block.has_collision]
    player.solid_objects = solid_blocks

    # --- GENEROWANIE FUTER ---
    for f in map_data.get("furs", []):
        pos = (f["x"], f["y"])
        fur_obj = Fur(player=player, position=pos, hold_time=0.6)
        all_furs.append(fur_obj)

    total_furs = len(all_furs)

    # --- GENEROWANIE PRZECIWNIKÓW ----
    color_to_variant = {
        "#ff0000": "horror",
        "#ffffff": "white",
        "#8b5a2b": "brown",
        "#ffd700": "rich"
    }

    for e in map_data.get("enemies", []):
        pos = (e["x"], e["y"])
        size = (e["scale_x"], e["scale_y"])
        hex_col = e.get("hex_color", "#ff0000").lower()
        chosen_variant = color_to_variant.get(hex_col, "brown")

        enemy_obj = Enemy(
            player=player, position=pos, size=size,
            zone1=e["zone1"], zone2=e["zone2"], zone3=e["zone3"],
            fov_degrees=110, use_gravity=True, solid_objects=solid_blocks,
            show_zones=False, variant=chosen_variant 
        )
        all_enemies.append(enemy_obj)

    # --- GENEROWANIE OCZU ---
    for eye_data in map_data.get("eyes", []):
        pos = (eye_data["x"], eye_data["y"])
        eye_obj = Eye(
            player=player, position=pos, size=(1, 1),
            zone_radii=(2.0, 4.0, 6.0), fov_degrees=110,
            color=color.red, use_gravity=False, solid_objects=all_blocks,
            show_zones=False
        )
        if hasattr(eye_obj, "rotation_time"):
            eye_obj.rotation_time = eye_data["rotation_time"]
        all_eyes.append(eye_obj)

    # --- GENEROWANIE WENTYLI ---
    for v in map_data.get("vents", []):
        pos = (v["x"], v["y"])
        tx = v.get("tile_x", 0)
        ty = v.get("tile_y", 0)

        vent_obj = Vent(player=player, position=pos, tile_x=tx, tile_y=ty)
        all_vents.append(vent_obj) 
        created_vents[v["vent_id"]] = {"obj": vent_obj, "target_id": v["target_vent_id"]}

    # --- ŁĄCZENIE WENTYLI ZE SOBĄ ---
    for vent_id, info in created_vents.items():
        current_vent = info["obj"]
        target_id = info["target_id"]
        if target_id in created_vents:
            current_vent.target_vent = created_vents[target_id]["obj"]

    # Konfiguracja kamery
    camera.orthographic = True
    camera.fov = 12
    camera.parent = scene
    game_sky = Sky()
    
    # --- UI ROZGRYWKI ---
    ikona_futra = Sprite(
        texture='GENERIC_ICONS',
        texture_scale=(0.5, 0.5),
        parent=camera.ui,
        scale=(0.1, 0.1),     
        position=(-0.82, 0.45)   
    )
    
    licznik_tekst = Text(text=f'0/{total_furs}', position=(-0.77, 0.46), scale=2)


# --------------------------------------------------
# --- PĘTLA UPDATE ---
# --------------------------------------------------
def update():
    global all_furs, total_furs, have_won, have_lost, licznik_tekst, game_music, win_music, napis_wygrana, napis_przegrana

    if not game_active:
        return

    # --- WARUNEK PRZEGRANEJ (IDENTYCZNY JAK WYGRANA) ---
    if have_lost and not have_won:
        print("Przegrałeś!")
        
        if game_music:
            game_music.stop()
            destroy(game_music)
            game_music = None

        napis_przegrana = Text(text="PRZEGRAŁEŚ!", scale=5, origin=(0, 0), color=color.red)
        invoke(hard_reset_to_level_menu, delay=3.0)
        return

    # Normalna pętla zbierania futer
    all_furs = [f for f in all_furs if f and getattr(f, 'enabled', False)]
    furs_left = len(all_furs)
    collected_furs = total_furs - furs_left

    if licznik_tekst:
        licznik_tekst.text = f'{collected_furs}/{total_furs}'

    # --- WARUNEK WYGRANEJ ---
    if furs_left == 0 and total_furs > 0 and not have_won and not have_lost:
        have_won = True
        print("Wygrałeś!")
        
        if game_music:
            game_music.stop()
            destroy(game_music)
            game_music = None

        if win_music is None:
            try:
                win_music = Audio('audio/wygrana', loop=False, autoplay=True)
                win_music.volume = 1.0
            except Exception as e:
                print(f"Nie udało się załadować muzyki wygranej: {e}")

        napis_wygrana = Text(text="WYGRAŁEŚ!", scale=5, origin=(0, 0), color=color.green)
        invoke(hard_reset_to_level_menu, delay=3.0)


# Pierwsze uruchomienie
init_ui() 
app.run()