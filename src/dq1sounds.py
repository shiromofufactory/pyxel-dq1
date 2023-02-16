import pyxel as px
import os
import dq1util as util

FADE_LIST = [
    (0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 4, 0, 0, 0, 0, 4),
    (0, 0, 0, 0, 0, 1, 5, 13, 2, 4, 9, 3, 5, 0, 4, 9),
]


class Sounds:
    def __init__(self):
        Sounds.nocut = False
        Sounds.waiting = False
        Sounds.cur_music = None
        Sounds.next_music = None
        Sounds.musics = {}
        path = "musics/"
        files = os.listdir(path)
        for file in files:
            if file.split(".")[-1] == "json":
                key = file.replace(".json", "")
                Sounds.musics[key] = util.load_json(path + key)

    # 効果音
    def sound(id, next_music=None):
        px.play(3, id)
        Sounds.nocut = False
        if next_music:
            Sounds.next_music = next_music

    # BGM設定
    def bgm(music, loop=True, next_music=None):
        if Sounds.nocut:
            Sounds.next_music = music
            return
        if Sounds.cur_music != music:
            if not loop:
                Sounds.nocut = True
                Sounds.next_music = (
                    Sounds.cur_music if next_music is None else next_music
                )
            for ch, sound in enumerate(Sounds.musics[music]):
                if sound is None or ch > 2:
                    continue
                px.sound(ch).set(
                    sound["notes"],
                    sound["tones"],
                    sound["volumes"],
                    sound["effects"],
                    1,
                )
                px.play(ch, ch, loop=loop)
        Sounds.cur_music = music

    # BGM同期待ち
    def wait(music, next_music=None):
        Sounds.nocut = False
        Sounds.bgm(music, False)
        Sounds.waiting = True
        if next_music:
            Sounds.next_music = next_music

    # 止まっていた曲を再生
    def resume(is_dead):
        if Sounds.next_music and px.play_pos(0) is None and px.play_pos(3) is None:
            Sounds.nocut = False
            Sounds.waiting = False
            if not is_dead:
                Sounds.bgm(Sounds.next_music)
                Sounds.next_music = None
