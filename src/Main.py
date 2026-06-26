from ursina import *
from src.Player import Player

app = Ursina()
player = Player(position=(-2,0), size=(1,1), color=color.orange, use_gravity=True)
floor = Entity(model='quad', y=-3, scale_x=10, scale_y=1, texture_scale=(10,1),texture='white_cube', collider='box')
przeskoda = Entity(model='quad', y=-1.5, scale_x=1, scale_y=3, texture_scale=(10,1),texture='white_cube', collider='box')

camera.orthographic = True
camera.fov = 10
camera.position = (0, 0, -20)
camera.rotation = (0, 0, 0)

app.run()


