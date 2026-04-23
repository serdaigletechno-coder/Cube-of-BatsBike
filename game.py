from math import sin, cos
from random import Random

from ursina import (
    application,
    Button,
    Entity,
    Sky,
    Text,
    Ursina,
    Vec2,
    Vec3,
    camera,
    color,
    destroy,
    mouse,
    scene,
    time,
    window,
)
from ursina.prefabs.first_person_controller import FirstPersonController


app = Ursina()
window.title = "CubeCraft of BatsBike - Minecraft Java Edition (prototype)"
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True

WORLD_SIZE = 24
MAX_HEIGHT = 5
SEED = 42
randomizer = Random(SEED)
voxels = {}


BLOCKS = {
    "grass": {"color": color.rgb(110, 170, 70), "label": "1 Herbe"},
    "dirt": {"color": color.rgb(120, 82, 55), "label": "2 Terre"},
    "stone": {"color": color.rgb(130, 130, 140), "label": "3 Pierre"},
    "sand": {"color": color.rgb(210, 195, 120), "label": "4 Sable"},
    "wood": {"color": color.rgb(140, 95, 45), "label": "5 Bois"},
}
block_order = list(BLOCKS)
selected_block = block_order[0]
info_text = None
paused = False
in_main_menu = True
spawn_position = None
pause_menu = None
start_menu = None
crosshair = None
player = None
menu_panorama_anchor = Vec3(10, 10, -18)
menu_panorama_pitch = -14


def block_color(block_type: str):
    base = BLOCKS[block_type]["color"]
    shade = randomizer.uniform(0.92, 1.08)
    return color.color(base.h, base.s, max(0, min(1, base.v * shade)))


class Voxel(Button):
    def __init__(self, position=(0, 0, 0), block_type="grass"):
        super().__init__(
            parent=scene,
            position=position,
            model="cube",
            origin_y=0.5,
            texture="white_cube",
            color=block_color(block_type),
            highlight_color=color.lime.tint(-0.1),
            collider="box",
        )
        self.block_type = block_type

    def input(self, key):
        if paused or not self.hovered:
            return

        if key == "left mouse down":
            place_block(self.position + mouse.normal, selected_block)
        elif key == "right mouse down":
            destroy_block(self.position)


def place_block(position, block_type):
    grid_position = to_grid(position)
    if grid_position in voxels:
        return

    voxel = Voxel(position=grid_position, block_type=block_type)
    voxels[grid_position] = voxel


def destroy_block(position):
    grid_position = to_grid(position)
    voxel = voxels.get(grid_position)
    if voxel is None or grid_position.y <= 0:
        return

    destroy(voxel)
    del voxels[grid_position]


def to_grid(position):
    return Vec3(round(position.x), round(position.y), round(position.z))


def terrain_height(x, z):
    hills = sin(x * 0.35) + cos(z * 0.28) + sin((x + z) * 0.18)
    height = int((hills + 3) / 6 * MAX_HEIGHT)
    return max(1, height)


def top_block_type(height):
    if height <= 1:
        return "sand"
    if height >= 4:
        return "stone"
    return "grass"


def make_tree(x, y, z):
    if randomizer.random() < 0.82:
        return

    trunk_height = randomizer.randint(3, 4)
    for trunk_y in range(y + 1, y + trunk_height + 1):
        place_block(Vec3(x, trunk_y, z), "wood")

    leaf_top = y + trunk_height
    for lx in range(x - 1, x + 2):
        for lz in range(z - 1, z + 2):
            for ly in range(leaf_top - 1, leaf_top + 2):
                if abs(lx - x) + abs(lz - z) < 3:
                    place_block(Vec3(lx, ly, lz), "grass")


def generate_world():
    for z in range(-WORLD_SIZE, WORLD_SIZE):
        for x in range(-WORLD_SIZE, WORLD_SIZE):
            height = terrain_height(x, z)
            for y in range(height + 1):
                if y == height:
                    block_type = top_block_type(height)
                elif y >= height - 2:
                    block_type = "dirt"
                else:
                    block_type = "stone"
                place_block(Vec3(x, y, z), block_type)

            if top_block_type(height) == "grass":
                make_tree(x, height, z)


def update_hotbar():
    info_text.text = (
        "CubeCraft of BatsBike\n"
        f"Bloc: {BLOCKS[selected_block]['label']}\n"
        "ZQSD/WASD: bouger | Espace: sauter | Souris: regarder\n"
        "Clic gauche: poser | Clic droit: casser | 1-5: changer de bloc | Esc: pause"
    )


def style_menu_button(button):
    button.color = color.rgb(112, 112, 112)
    button.highlight_color = color.rgb(145, 145, 145)
    button.pressed_color = color.rgb(85, 85, 85)
    button.text_entity.scale = 11.2
    button.text_entity.color = color.black
    return button


def add_logo(parent, title, subtitle, y=0.26, scale=2.7):
    Text(
        parent=parent,
        text=title,
        origin=(0, 0),
        y=y - 0.01,
        x=0.006,
        scale=scale,
        color=color.rgba(0, 0, 0, 180),
    )
    Text(
        parent=parent,
        text=title,
        origin=(0, 0),
        y=y,
        scale=scale,
        color=color.black,
    )
    Text(
        parent=parent,
        text=subtitle,
        origin=(0, 0),
        y=y - 0.11,
        x=0.27,
        rotation_z=-12,
        scale=11.05,
        color=color.black,
    )


def apply_gameplay_state(gameplay_enabled):
    player.enabled = gameplay_enabled
    mouse.locked = gameplay_enabled
    mouse.visible = not gameplay_enabled
    crosshair.enabled = gameplay_enabled
    info_text.enabled = gameplay_enabled


def resume_game():
    global paused
    paused = False
    pause_menu.disable()
    apply_gameplay_state(True)


def pause_game():
    global paused
    paused = True
    apply_gameplay_state(False)
    player.velocity = Vec3(0, 0, 0)
    pause_menu.enable()


def toggle_pause():
    if in_main_menu:
        return
    if paused:
        resume_game()
    else:
        pause_game()


def respawn_player():
    player.position = spawn_position
    player.rotation = Vec3(0, 0, 0)
    player.camera_pivot.rotation = Vec3(0, 0, 0)
    resume_game()


def quit_game():
    application.quit()


def start_game():
    global in_main_menu, paused
    in_main_menu = False
    paused = False
    start_menu.disable()
    player.position = spawn_position
    player.rotation = Vec3(0, 0, 0)
    player.camera_pivot.rotation = Vec3(0, 0, 0)
    player.velocity = Vec3(0, 0, 0)
    apply_gameplay_state(True)


def create_start_menu():
    menu = Entity(parent=camera.ui, enabled=True)
    Entity(
        parent=menu,
        model="quad",
        scale=(2, 1),
        color=color.rgba(0, 0, 0, 110),
    )
    Entity(
        parent=menu,
        model="quad",
        scale=(0.78, 0.52),
        y=-0.02,
        color=color.rgba(18, 18, 18, 165),
    )
    add_logo(menu, "CubeCraft", "of BatsBike!", y=0.31, scale=12.85)
    Text(
        parent=menu,
        text="Edition Python inspiree de Minecraft Java",
        origin=(0, 0),
        y=0.11,
        scale=10.95,
        color=color.black,
    )
    style_menu_button(Button(parent=menu, text="Jouer", scale=(0.42, 0.085), y=-0.01, on_click=start_game))
    style_menu_button(Button(parent=menu, text="Quitter", scale=(0.42, 0.085), y=-0.12, on_click=quit_game))
    Text(
        parent=menu,
        text="Construis, casse des blocs et explore ton monde.",
        origin=(0, 0),
        y=-0.25,
        scale=10.9,
        color=color.black,
    )
    return menu


def create_pause_menu():
    menu = Entity(parent=camera.ui, enabled=False)
    Entity(
        parent=menu,
        model="quad",
        scale=(1, 1),
        color=color.rgba(0, 0, 0, 150),
    )
    Entity(
        parent=menu,
        model="quad",
        scale=(0.72, 0.46),
        y=-0.01,
        color=color.rgba(22, 22, 22, 175),
    )
    add_logo(menu, "Pause", "Menu", y=0.24, scale=12.25)
    style_menu_button(Button(parent=menu, text="Reprendre", scale=(0.4, 0.082), y=0.07, on_click=resume_game))
    style_menu_button(Button(parent=menu, text="Reapparaitre", scale=(0.4, 0.082), y=-0.04, on_click=respawn_player))
    style_menu_button(Button(parent=menu, text="Quitter", scale=(0.4, 0.082), y=-0.15, on_click=quit_game))
    Text(
        parent=menu,
        text="Esc pour reprendre",
        origin=(0, 0),
        y=-0.28,
        scale=10.95,
        color=color.black,
    )
    return menu


def input(key):
    global selected_block

    if key == "escape":
        toggle_pause()
    elif in_main_menu:
        return
    elif paused:
        return
    elif key in {"1", "2", "3", "4", "5"}:
        selected_block = block_order[int(key) - 1]
        update_hotbar()


def update():
    if in_main_menu:
        player.position = menu_panorama_anchor
        player.rotation_y += time.dt * 6
        player.camera_pivot.rotation_x = menu_panorama_pitch


generate_world()
Sky(color=color.rgb(135, 206, 235))
spawn_position = Vec3(0, terrain_height(0, 0) + 2, 0)

player = FirstPersonController(
    position=spawn_position,
    speed=6,
    jump_height=1.8,
    gravity=0.65,
)

info_text = Text(
    parent=camera.ui,
    origin=(-0.5, 0.5),
    position=Vec2(-0.86, 0.46),
    scale=0.95,
    background=True,
    color=color.black,
)
update_hotbar()

crosshair = Entity(
    parent=camera.ui,
    model="quad",
    color=color.white,
    scale=0.008,
    rotation_z=45,
)

pause_menu = create_pause_menu()
start_menu = create_start_menu()
apply_gameplay_state(False)
player.position = menu_panorama_anchor
player.rotation_y = 35
player.camera_pivot.rotation_x = menu_panorama_pitch

import os

class ResourceManager:
    def __init__(self, base_path="assets"):
        self.base_path = base_path

    def get_texture_path(self, namespace, path):
        # Transforme "minecraft:block/grass" en "assets/textures/block/grass.png"
        full_path = os.path.join(self.base_path, "textures", path + ".png")
        return full_path

# Utilisation dans votre code
res = ResourceManager()
grass_texture = res.get_texture_path("minecraft", "block/grass") 
# Résultat : "assets/textures/block/grass.png"

app.run()
