import pyxel as px
import copy
import dq1util as util


master = util.load_json("dq1master")


class Battle:
    def __init__(self):
        Battle.on = False
        Battle.auto = False
        Battle.rollout = 0
        Battle.state = 0

    def off():
        Battle.on = False
        Battle.rollout = 0

    def start(enemy_id, is_boss, auto):
        if not Battle.on:
            Battle.on = True
            Battle.rollout = 7
        Battle.state = 1
        Battle.enemy = copy.deepcopy(master["enemies"][enemy_id])
        en = Battle.enemy
        max_hp = en["hp"]
        en["max_hp"] = max_hp
        en["hp"] = max_hp if is_boss else px.rndi(int(max_hp * 0.8 + 1), max_hp)
        en["sleeping"] = 0
        en["sealed"] = False
        en["surprised"] = False
        Battle.is_boss = is_boss
        Battle.auto = auto
        Battle.enemy_blinking = 0
        Battle.action = None
        Battle.myturn = True
        Battle.sleeping = False
        Battle.sealed = False

    # モンスターを表示
    def draw_enemy():
        if Battle.on and Battle.rollout <= 5:
            enemy = Battle.enemy
            if enemy["hp"] > 0 or Battle.state == 1:
                if Battle.enemy_blinking % 4 < 2:
                    px.blt(
                        128 - enemy["width"] / 2,
                        152 - enemy["height"],
                        enemy["img_no"],
                        enemy["img_x"],
                        enemy["img_y"],
                        enemy["width"],
                        enemy["height"],
                        0,
                    )
                Battle.enemy_blinking = max(Battle.enemy_blinking - 1, 0)

    # ロールアウト（バトル突入）
    def draw_rollout():
        if Battle.on:
            blk_pos = Battle.rollout * 16
            blk_size = (7 - Battle.rollout) * 32 + 16
            px.rect(blk_pos, blk_pos, blk_size, blk_size, 0)
            Battle.rollout -= 1

    # 自分のターン
    def call_player():
        Battle.myturn = True
        Battle.action = None
        if Battle.sleeping > 0:
            Battle.sleeping -= 1
            if Battle.sleeping == 0:
                return True
            else:
                Battle.action = "sleeping"
        return False

    # 敵のターン
    def call_enemy():
        Battle.myturn = False
        Battle.action = None
        en = Battle.enemy
        en["surprised"] = False
        if en["sleeping"] > 0:
            en["sleeping"] -= 1
            if en["sleeping"] == 0:
                return True
            else:
                Battle.action = "sleeping"
        return False
