import dq1util as util

master = util.load_json("dq1master")
map_settings = util.load_json("dq1maps")


class Grade:
    def __init__(self, lv, exp, personality):
        Grade.lv = lv
        Grade.exp = exp
        Grade.personality = personality

    # おぼえた呪文
    def learned_spell(add=0):
        spells = [
            s
            for s in master["spells"]
            if s["lv"] <= Grade.lv + add + (1 if Grade.personality == 3 else 0)
        ]
        return len(spells) - 1

    # つぎのレベルまで
    def to_lvup():
        return master["lvup"][Grade.lv]["exp"] - Grade.exp

    # レベルアップ時上昇値
    def lvup_parms():
        lv_master = master["lvup"][Grade.lv - 1]
        h_up = lv_master["hp1" if Grade.personality in [0, 1] else "hp2"]
        m_up = lv_master["mp1" if Grade.personality in [1, 3] else "mp2"]
        p_up = lv_master["power1" if Grade.personality in [0, 2] else "power2"]
        s_up = lv_master["speed1" if Grade.personality in [2, 3] else "speed2"]
        return (h_up, m_up, p_up, s_up)

    # レベル最大か
    def is_max_lv():
        return Grade.lv >= 30

    # かいしんの一撃確率
    def crt_chance():
        return 2 if Grade.personality == 0 else 1

    # 回避率
    def avoid_chance():
        return 3 if Grade.personality == 2 else 2

    # 状態異常無効化率
    def nullify_chance():
        return 24 if Grade.personality == 1 else 16
