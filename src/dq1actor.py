import pyxel as px
import dq1const as const
import dq1util as util

ACTORS_UI = [
    (0, 5, 1, 5),  # 自分0
    (4, 5, 4, 5),  # 姫1
    (5, 5, 5, 5),  # 王2
    (6, 5, 7, 5),  # 兵士槍3
    (0, 6, 1, 6),  # 兵士素手4
    (2, 6, 2, 6),  # 兵士ラッパ5
    (3, 6, 4, 6),  # 戦士6
    (5, 6, 6, 6),  # じじい7
    (7, 6, 0, 7),  # 女子8
    (1, 7, 2, 7),  # 商人9
    (3, 7, 4, 7),  # 男子10
    (5, 7, 5, 7),  # 竜王様11
    (4, 2, 4, 2),  # 宝箱12
    (5, 2, 5, 2),  # ドア13
    (0, 2, 0, 2),  # 屋根14
    (6, 7, 6, 7),  # 暗闇15
    (2, 5, 3, 5),  # 自分with姫16
    (5, 1, 5, 1),  # 海17
    (0, 4, 0, 4),  # バリア18
]
map_cells = util.load_json("dq1cells")


class Actor:
    def __init__(self, actor):
        base_x = Actor.cur_map.base_x if Actor.cur_map is not None else 0
        base_y = Actor.cur_map.base_y if Actor.cur_map is not None else 0
        self.x = actor["x"] + base_x
        self.y = actor["y"] + base_y
        self.chr = actor["chr"] if "chr" in actor else None
        self.movable = actor["movable"] if "movable" in actor else False
        self.event = actor["event"] if "event" in actor else None
        self.lock = actor["lock"] if "lock" in actor else None
        self.door = actor["door"] if "door" in actor else None
        self.flag = actor["flag"] if "flag" in actor else None
        self.through = actor["through"] if "through" in actor else None
        self.reverse = actor["reverse"] if "reverse" in actor else None
        self.is_player = self.chr == 0
        self.is_talking = False
        self.moved = False
        self.collision = None
        self.overlap = None
        self.prev_dx = 0
        self.prev_dy = 0
        self.reset_move()

    def update(self, operable, btn):
        if self.dx == 0 and self.dy == 0:
            if not self.movable or self.is_talking:
                return
            if self.is_player:
                if operable:
                    (dx, dy) = (0, 0)
                    if btn["l_"]:
                        dx = -1
                    elif btn["r_"]:
                        dx = 1
                    if btn["u_"]:
                        dy = -1
                    elif btn["d_"]:
                        dy = 1
                    can_x = self.move(dx, 0, simulate=True)
                    can_y = self.move(0, dy, simulate=True)
                    if can_x and (not can_y or self.prev_dy != 0):
                        self.move(dx, 0)
                    elif can_y and (not can_x or self.prev_dx != 0):
                        self.move(0, dy)
            else:
                r = px.rndi(0, 99)
                if r == 0:
                    self.move(-1, 0)
                elif r == 1:
                    self.move(1, 0)
                elif r == 2:
                    self.move(0, -1)
                elif r == 3:
                    self.move(0, 1)
        if self.dx != 0 or self.dy != 0:
            move_speed = 4 if Actor.cur_map.map_no != 0 and self.is_player else 2
            self.sx += self.dx * move_speed
            self.sy += self.dy * move_speed
            if abs(self.sx) >= 16:
                x = 1 if self.sx > 0 else -1
                self.sx -= x * 16
                self.x += x
                self.steps -= 1
            if abs(self.sy) >= 16:
                y = 1 if self.sy > 0 else -1
                self.sy -= y * 16
                self.y += y
                self.steps -= 1
            if self.steps == 0:
                self.prev_dx = self.dx
                self.prev_dy = self.dy
                self.dx = 0
                self.dy = 0
                if self.is_player:
                    self.moved = True
        return

    def draw(self, scroll_x, scroll_y, vision, is_dead=False):
        if self.chr is None:
            return
        idx = self.chr
        chr = ACTORS_UI[idx]
        chr_pos = 0 if px.frame_count % 20 < 10 or is_dead else 1
        u = chr[chr_pos * 2] * 16
        v = chr[chr_pos * 2 + 1] * 16
        x = self.x * 16 + self.sx - scroll_x
        y = self.y * 16 + self.sy - scroll_y
        w = -16 if self.reverse else 16
        if abs(112 - x) < vision * 8 + 16 and abs(112 - y) < vision * 8 + 16:
            px.blt(x, y, 0, u, v, w, 16, const.TRANSPARENT)

    def reset_move(self):
        self.dx = 0
        self.dy = 0
        self.steps = 0
        self.sx = 0
        self.sy = 0

    def move(self, x, y, loop=1, simulate=False):
        if x == 0 and y == 0:
            return False
        nx = self.x + x
        ny = self.y + y
        cell = map_cells[Actor.cur_map.map_no][ny][nx]
        blocked = cell in ["0", "1", "h", "i", "j", "k", "p", "q"]
        for actor in Actor.actors:
            if (actor.x == nx and actor.y == ny) or (
                actor.x + actor.dx == nx and actor.y + actor.dy == ny
            ):
                if (
                    self.is_player
                    and not actor.is_talking
                    and (actor.event or actor.door)
                ):
                    if (blocked or not actor.chr is None) and not actor.through:
                        self.collision = actor
                    else:
                        self.overlap = actor
                if not actor.through and not actor.chr is None:
                    blocked = True
        if not self.is_player and Actor.cur_map.is_out(nx, ny):
            blocked = True  # NPCは建物の外に出れない
        if blocked:
            self.overlap = None
            return False
        if not simulate:
            self.dx = x
            self.dy = y
            self.steps = loop
        return True


# Actorを削除
def remove_actor(actor):
    del Actor.actors[Actor.actors.index(actor)]
