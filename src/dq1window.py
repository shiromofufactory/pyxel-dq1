import pyxel as px
import dq1util as util

TRANSPARENT = 2
TEXTS = util.load_json("texts")


class Window:
    def __init__(self, x1, y1, x2, y2, texts):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.has_cur = False
        self.cur_x = None
        self.cur_y = None
        self.cur_fix = False
        self.texts = [texts] if type(texts) is str else texts
        self.is_talk = False
        self.is_battle = False
        self.open_cnt = 0
        self.talk_pos = 0
        self.talk_line = 0
        self.talk_stock = []
        self.talk_state = 0  # 0:会話、1:続きあり、9:完了
        self.flash = 0
        self.parm = None
        self.kind = None

    def add_cursol(self, h=None, w=1):
        self.cur_w = w
        self.cur_h = len(self.texts) if h is None else h
        self.cur_x = 0
        if self.cur_y is None:
            self.cur_y = 0
        if self.cur_x is None:
            self.cur_x = 0
        self.has_cur = True
        self.start_cur = False
        return self

    def push(self, texts_in):
        texts = texts_in.split("\n")
        if len(self.texts) > 0:
            self.talk_stock.append(texts)
            if self.talk_state == 9:
                self.next()
        else:
            self.texts = texts

    def next(self):
        util.beep()
        self.texts.extend(self.talk_stock.pop(0))
        self.talk_state = 0

    def feed(self):
        while len(self.texts) > 4:
            self.texts.pop(0)
        self.talk_line = len(self.texts) - 1
        self.talk_pos = 99

    def update_cursol(self, btn):
        (mx, my) = (0, 0)
        if not btn["u_"] and not btn["d_"]:
            self.start_cur = True
        if self.start_cur:
            self.cur_fix = False
            if btn["u"]:
                my = -1
            elif btn["d"]:
                my = 1
            if btn["l"]:
                mx = -1
            elif btn["r"]:
                mx = 1
            if my != 0:
                self.cur_y = util.loop(self.cur_y, my, self.cur_h)
                self.flash = 0
            if mx != 0:
                self.cur_x = util.loop(self.cur_x, mx, self.cur_w)
                self.flash = 0
        if btn["s"] or btn["a"]:
            self.cur_fix = True
            util.beep()
        return self

    def draw(self):
        x1 = self.x1
        y1 = self.y1
        x2 = self.x2
        y2 = self.y2

        # 枠描写とオープンアニメーション
        px.blt(x1 * 8, y1 * 16, 0, 0, 128, 8, 16, TRANSPARENT)
        px.blt(x2 * 8, y1 * 16, 0, 16, 128, 8, 16, TRANSPARENT)
        for i in range(x1 + 1, x2):
            px.blt(i * 8, y1 * 16, 0, 8, 128, 8, 16, TRANSPARENT)
        if self.open_cnt > 0:
            y_to = min(y1 + 1 + self.open_cnt, y2)
            for i in range(y1 + 1, y_to):
                px.blt(x1 * 8, i * 16, 0, 24, 128, 8, 16, TRANSPARENT)
                px.blt(x2 * 8, i * 16, 0, 32, 128, 8, 16, TRANSPARENT)
            px.rect(
                x1 * 8 + 8, y1 * 16 + 16, (x2 - x1 - 1) * 8, (y_to - y1 - 1) * 16, 0
            )
        if y1 + 1 + self.open_cnt > y2:
            px.blt(x1 * 8, y2 * 16, 0, 40, 128, 8, 16, TRANSPARENT)
            px.blt(x2 * 8, y2 * 16, 0, 56, 128, 8, 16, TRANSPARENT)
            for i in range(x1 + 1, x2):
                px.blt(i * 8, y2 * 16, 0, 48, 128, 8, 16, TRANSPARENT)
        height = y2 - y1 - 1

        # 文字描画
        if self.open_cnt <= height:
            self.open_cnt += 1
        if self.is_talk:
            if self.open_cnt <= height:
                return
            if self.is_battle:
                self.talk_line = height
            else:
                if (
                    self.talk_pos > 0
                    and self.talk_state == 0
                    and px.play_pos(3) is None
                ):
                    px.play(3, 5)
                if self.talk_state > 0:
                    if self.talk_state == 1 and self.flash < 15:
                        draw_text((x1 + x2) / 2, y1 + 4, "↓")
                    self.flash = (self.flash + 1) % 30
                elif self.talk_pos < len(self.texts[self.talk_line]):
                    self.talk_pos += 2
                else:
                    self.talk_line += 1
                    self.talk_pos = 0
                    if self.talk_line >= height:
                        self.texts.pop(0)
                        self.talk_line -= 1
                    if self.talk_line >= len(self.texts):
                        self.talk_state = 1 if len(self.talk_stock) > 0 else 9
            for i, text in enumerate(self.texts):
                if i <= height and i <= self.talk_line:
                    if i == self.talk_line:
                        text = self.texts[i][0 : self.talk_pos]
                    else:
                        text = self.texts[i]
                    draw_text(x1 + 1, y1 + i + 1, text)
        else:
            for i, text in enumerate(self.texts):
                if i <= self.open_cnt - 2:
                    draw_text(x1 + 1, y1 + i + 1, text)

        # カーソル
        if self.has_cur:
            fixed = self.cur_fix or not self.start_cur
            if fixed or self.flash < 10:
                draw_text(x1 + self.cur_x * 2 + 1, y1 + self.cur_y + 1, "→")
            if not fixed:
                self.flash = (self.flash + 1) % 20


# テキスト描画
def draw_text(x, y, txt):
    for i, t in enumerate(txt):
        if t in TEXTS:
            tx, ty = TEXTS[t]
            px.blt((x + i) * 8, y * 16, 0, tx * 8, 144 + ty * 16, 8, 16)
