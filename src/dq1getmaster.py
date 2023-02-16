import pyxel as px
import dq1util as util

master = util.load_json("dq1master")


# 呪文取得（key未指定の場合、現在カーソル位置）
def spell(key):
    if type(key) is int:
        return master["spells"][key]
    for spell in master["spells"]:
        if spell["symbol"] == key:
            return spell


# 道具情報取得
def item(id):
    if id is None:
        return {"name": "", "atc": 0, "dfc": 0, "price": None}
    else:
        return master["items"][id]


# 回復量計算
def calc_cure(key):
    val_min = 85 if key == "BHIM" else 25
    val_max = 100 if key == "BHIM" else 30
    return px.rndi(val_min, val_max)
