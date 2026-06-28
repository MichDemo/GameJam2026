# class SwitchVent(Vent):
#     def __init__(self, player, target_vent=None, music_sewers=Audio('../assets/audio/scieki_safezone.mp3'), music_house=Audio()'../assets/audio/dom.mp3'), target_mode='dom', **kwargs):
#         # Wywołujemy konstruktor klasy bazowej (Vent), który ogarnie całą resztę parametrów
#         super().__init__(player, target_vent, **kwargs)

#         self.music_sewers = music_sewers  # Obiekt Audio dla ścieków
#         self.music_house = music_house    # Obiekt Audio dla domu
#         self.target_mode = target_mode    # 'dom' lub 'ścieki' - dokąd ten wentyl prowadzi

#     def start_teleport(self):
#         # Jeśli wentyl nie ma przypisanego celu, przerywamy zanim cokolwiek zmienimy
#         if not self.target_vent:
#             print("Ten wentyl nie ma ustawionego celu.")
#             return

#         # Odpalamy całą magię oryginalnej teleportacji (ruch, animacje kamery, dźwięk "kliknięcia")
#         super().start_teleport()

#         # --- ZMIANA MUZYKI ---
#         if self.music_sewers and self.music_house:
#             if self.target_mode == 'dom':
#                 self.music_sewers.stop()   # Zatrzymujemy ścieki
#                 self.music_house.play()    # Włączamy dom
#                 print("Muzyka zmieniona na: DOM")
#             elif self.target_mode == 'ścieki':
#                 self.music_house.stop()    # Zatrzymujemy dom
#                 self.music_sewers.play()   # Włączamy ścieki
#                 print("Muzyka zmieniona na: ŚCIEKI")
