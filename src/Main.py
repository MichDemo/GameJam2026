from ursina import *
from ursina.prefabs.platformer_controller_2d import PlatformerController2d

player = PlatformerController2d(
    y=1, 
    scale_y=1, 
    max_jumps=1, 
    color=color.red, 
    jump_height=3, 
    jump_duration=.2, 
    gravity=.8, 
    speed=8
    )

app = Ursina()

floor = Entity(model='quad', y=-3, scale_x=10, scale_y=1, texture_scale=(10,1),texture='white_cube', collider='box')
przeskoda = Entity(model='quad', y=-1.5, scale_x=1, scale_y=3, texture_scale=(10,1),texture='white_cube', collider='box')

camera.orthographic = True
camera.fov = 10
camera.position = (0, 0, -20)
camera.rotation = (0, 0, 0)

app.run()


