import pyxel as px


class Colors:
    def __init__(self):
        Colors.flash = 0
        Colors.poison = 0
        Colors.rainbow = False

    def draw(is_dead):
        for c in range(16):
            c_flash = c
            if Colors.rainbow and c == 12:
                idx = (px.frame_count // 2) % 7
                c_flash = [8, 9, 10, 11, 12, 5, 2][idx]
            elif Colors.flash % 4 == 1:
                c_flash = 7
            elif Colors.poison % 4 == 1:
                c_flash = 8
            if is_dead and c == 7:
                c_flash = 14
            px.pal(c, c_flash)

    def update(pressed):
        Colors.flash = max(0 if pressed else Colors.flash - 1, 0)
        Colors.poison = max(Colors.poison - 1, 0)

    def set_flash(times):
        Colors.flash = times * 4 - 3
