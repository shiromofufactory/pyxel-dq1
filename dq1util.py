import pyxel as px
import json


# 「ピッ」音
def beep():
    if px.play_pos(3) is None:
        px.play(3, 6)


# JSONロード
def load_json(file):
    with open("./" + file + ".json", "r") as fin:
        return json.loads(fin.read())


# パディング右よせ
def padding(val, length, fill=" "):
    return str(val).rjust(length, fill)


# パディング左よせ
def spacing(val, length):
    return str(val).ljust(length)


# ループ計算
def loop(target, dist, length, min_val=0):
    if dist is None:
        return target
    value = target + dist if target else dist
    if value >= length + min_val:
        value -= length
    if value < min_val:
        value += length
    return value


# 配列の要素を数値に
def list_str2int(ls):
    return [int(value) for value in ls]


# プレイ時間取得
def get_play_time(logs):
    seconds = logs["frames"] // 30
    minutes = (seconds // 60) % 60
    hours = min(seconds // 3600, 99)
    seconds = seconds % 60
    return f"{padding(hours,2,'0')}：{padding(minutes,2,'0')}：{padding(seconds,2,'0')}"
