# ==========================================
# PLIK: main.py
# ==========================================
from ursina import *
# Importujemy funkcję z naszego drugiego pliku:

# Inicjalizacja silnika (TYLKO JEDEN RAZ)
app = Ursina()
window.title = "Szcurwy hood"
window.borderless = False


# --- AUDIO ---
# autoplay=True sprawi, że muzyka ruszy od razu
menu_music = Audio('../assets/audio/glowne_menu.mp3', loop=True, autoplay=True)

# --- STAN GRY ---
stan_gry = "menu"

# --- ELEMENTY MENU ---
menu_container = Entity(enabled=True)

# Tytuł gry
tytul = Text(
    text='Szcurwy hood', 
    scale=15,          # Zmniejszyłem lekko scale z 15 na 5, bo przy orthographic/UI 15 może uciekać z ekranu
    origin=(0, 0), 
    y=3,            # Wartości pozycji UI w Ursinie najlepiej trzymać w zakresie od -0.5 do 0.5
    parent=menu_container,
    color=color.gold
)

# Funkcje dla przycisków
def start_gry():
    global stan_gry
    stan_gry = "rozgrywka"
    menu_container.disable()  # Ukrywamy menu

    # Zatrzymujemy muzykę menu i odpalamy muzykę z gry
    menu_music.stop()
    game_music.play()


    uruchom_gre()             # Odpalamy grę

def pokaz_opcje():
    print("Opcje kliknięte!")

def wyjdz_z_gry():
    application.quit()

# Przyciski menu (skalowane pod standardowe proporcje UI)
przycisk_start = Button(
    text='Start', 
    color=color.azure, 
    scale=(2, 1), 
    y=0, 
    parent=menu_container,
    on_click=start_gry
)

przycisk_opcje = Button(
    text='Opcje', 
    color=color.azure, 
    scale=(2, 1), 
    y=-1.5, 
    parent=menu_container,
    on_click=pokaz_opcje
)

przycisk_wyjscie = Button(
    text='Wyjdź', 
    color=color.gray, 
    scale=(2, 1), 
    y=-3, 
    parent=menu_container,
    on_click=wyjdz_z_gry
)


# --- ELEMENTY ROZGRYWKI ---
game_container = Entity(enabled=False)

def uruchom_gre():
    game_container.enable()
    # Wywołujemy naszą funkcję z drugiego pliku, przekazując kontener

# Uruchomienie aplikacji (TYLKO JEDEN RAZ na samym końcu)
app.run()
