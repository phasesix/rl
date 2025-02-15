import curses
import random

from rlgame.item_stack import ItemStack, FloorItemStacks
from rlgame.tiles import WallTile, DoorTile
from rlgame.colors import OutsideSightColor


class RoomBase:
    def __init__(self, game):
        self.challenge_rating_modifier = random.randint(-1, 2)
        self.enemies = []
        self.exit = None
        self.game = game
        self.was_entered = False
        self.floor_item_stacks = FloorItemStacks(self)

        self.height = self.challenge_rating * random.randint(15, 25)
        self.width = self.challenge_rating * random.randint(10, 12)
        self.tiles = self.generator.generate_room()
        self.create_enemies()
        # self.create_exit()  # No exit until all enemies are defeated

    @property
    def name(self):
        raise NotImplementedError("name method must be implemented in subclass")

    @property
    def generator(self):
        raise NotImplementedError("generator method must be implemented in subclass")

    @property
    def challenge_rating(self):
        return max(1, self.game.challenge_rating + self.challenge_rating_modifier)

    def create_enemies(self):
        self.enemies = []

    def create_exit(self):
        return None

    def position_player(self, player):
        if self.exit:
            player.x, player.y = self.exit
        else:
            player.x, player.y = self.width // 2, self.height - 2

    def is_walkable(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x].is_walkable
        return False

    def get_map_position_in_viewport(self, map_x, map_y) -> tuple | None:
        """Convert map coordinates to viewport coordinates. Return None if the map position is not in the viewport."""
        player = self.game.player
        viewport_width = self.game.viewport_width
        viewport_height = self.game.viewport_height
        offset_x = player.x - viewport_width // 2
        offset_y = player.y - viewport_height // 2

        x = map_x - offset_x
        y = map_y - offset_y

        if 0 <= y < viewport_height and 0 <= x < viewport_width:
            return x, y
        return None

    def draw_map(self, player):
        """Draw the map around the player in the viewport."""
        viewport_width = self.game.viewport_width
        viewport_height = self.game.viewport_height
        offset_x = player.x - viewport_width // 2
        offset_y = player.y - viewport_height // 2

        for y in range(viewport_height):
            for x in range(viewport_width):
                if 0 <= y + offset_y < self.height and 0 <= x + offset_x < self.width:
                    tile = self.tiles[y + offset_y][x + offset_x]
                else:
                    tile = WallTile(self.game)

                if self.game.player.is_in_view_distance(x + offset_x, y + offset_y):
                    tile.is_discovered = True
                    self.game.stdscr.addch(
                        y, x, tile.char, curses.color_pair(tile.color) | curses.A_BOLD
                    )
                else:
                    if tile.is_discovered:
                        self.game.stdscr.addch(
                            y,
                            x,
                            tile.char,
                            curses.color_pair(OutsideSightColor.pair_number),
                        )
                    else:
                        self.game.stdscr.addch(y, x, " ", curses.color_pair(0))

    def move_enemies(self):
        for enemy in self.enemies:
            enemy.update_movement()
            if enemy.can_move_by_speed():
                if enemy.can_attack_player():
                    enemy.attack(self.game.player)
                elif not enemy.has_ammo():
                    enemy.reload_ammo()
                else:
                    dx, dy = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                    enemy.move(dx, dy)

    def draw_enemies(self, stdscr):
        for enemy in self.enemies:
            enemy.draw(stdscr)

    def add_item_stack_to_floor(self, x: int, y: int, item_stack: ItemStack):
        """Add an item stack to the floor. The items are scattered randomly around the x, y position up to 3 tiles away,
        only in walkable tiles. If a position is already occupied, the item stack is added to another random position.
        """
        while True:
            dx = random.randint(-3, 3)
            dy = random.randint(-3, 3)
            if self.is_walkable(
                x + dx, y + dy
            ) and not self.floor_item_stacks.get_item_stack(x + dx, y + dy):
                self.floor_item_stacks.add_item_stack(x + dx, y + dy, item_stack)
                break

    def draw_item_stacks(self, stdscr):
        for (x, y), item_stack in self.floor_item_stacks.item_stacks.items():
            if pos := self.get_map_position_in_viewport(x, y):
                x, y = pos
                stdscr.addch(
                    y,
                    x,
                    item_stack.item.char,
                    curses.color_pair(item_stack.item.color_pair),
                )

    def draw(self, stdscr):
        self.draw_map(self.game.player)

        if self.exit:
            if pos := self.get_map_position_in_viewport(*self.exit):
                x, y = pos
                door_tile = DoorTile(self.game)
                stdscr.addch(
                    y,
                    x,
                    door_tile.char,
                    curses.color_pair(door_tile.color),
                )

        self.draw_item_stacks(stdscr)
        self.draw_enemies(stdscr)
