import pyxel as px
import datetime
import copy
import dq1const as const
import dq1util as util
import dq1getmaster as gm
from dq1actor import Actor, remove_actor
from dq1fade import Fade
from dq1colors import Colors
from dq1sounds import Sounds
from dq1battle import Battle
from dq1grade import Grade
from dq1map import Map
from dq1window import Window
from dq1firebase import Firebase


master = util.load_json("dq1master")
map_cells = util.load_json("dq1cells")
messages = util.load_json("dq1message")
jumps = util.load_json("dq1jumps")


class App:
    def __init__(self):
        px.init(240, 240, title="Dragon Quest 1 for Pyxel")
        px.load("dq1.pyxres")
        # px.image(0).save("images/image0.png", 1)
        # px.image(1).save("images/image1.png", 1)
        # px.image(2).save("images/image2.png", 1)
        self.visible = True
        self.windows = {}
        Actor.cur_map = None
        Actor.actors = []
        self.next_map = None
        self.next_x = None
        self.next_y = None
        self.reserves = []
        self.wait = 0
        Battle()
        Fade()
        Colors()
        Sounds()
        self.shaking = 0
        self.status_timer = 0
        self.cure_suggestion = False
        self.logs = {
            "frames": 0,
            "loaded": 0,
            "steps": 0,
            "win": 0,
            "dead": 0,
            "escape": 0,
        }
        self.player = Actor({"x": 0, "y": 0, "chr": 0, "movable": True})
        self.name = ""  # ないとエラーになる
        self.hp = 1  # ないとエラーになる
        self.save_code = None
        self.prev_code = None
        self.open_welcome()
        px.run(self.update, self.draw)

    def update(self):
        pl = self.player
        btn = {
            "u_": px.btn(px.KEY_UP) or px.btn(px.GAMEPAD1_BUTTON_DPAD_UP),
            "d_": px.btn(px.KEY_DOWN) or px.btn(px.GAMEPAD1_BUTTON_DPAD_DOWN),
            "l_": px.btn(px.KEY_LEFT) or px.btn(px.GAMEPAD1_BUTTON_DPAD_LEFT),
            "r_": px.btn(px.KEY_RIGHT) or px.btn(px.GAMEPAD1_BUTTON_DPAD_RIGHT),
            "u": px.btnp(px.KEY_UP, 6, 6) or px.btnp(px.GAMEPAD1_BUTTON_DPAD_UP),
            "d": px.btnp(px.KEY_DOWN, 6, 6) or px.btnp(px.GAMEPAD1_BUTTON_DPAD_DOWN),
            "l": px.btnp(px.KEY_LEFT, 6, 6) or px.btnp(px.GAMEPAD1_BUTTON_DPAD_LEFT),
            "r": px.btnp(px.KEY_RIGHT, 6, 6) or px.btnp(px.GAMEPAD1_BUTTON_DPAD_RIGHT),
            "s": px.btnp(px.KEY_S, 6, 6) or px.btnp(px.GAMEPAD1_BUTTON_A, 6, 6),
            "a": px.btnp(px.KEY_A, 6, 6) or px.btnp(px.GAMEPAD1_BUTTON_B, 6, 6),
            "w": px.btnp(px.KEY_W, 6, 6) or px.btnp(px.GAMEPAD1_BUTTON_X, 6, 6),
        }
        pressed = btn["s"] or btn["a"] or btn["u"] or btn["d"] or btn["r"] or btn["l"]
        talk_state = (
            self.windows["talk"].talk_state
            if "talk" in self.windows and not Battle.on
            else -1
        )
        operable = False  # キャラクタ操作（移動）可能か
        # フレーム数計上
        if self.logs:
            self.logs["frames"] += 1
        # マップ切り替え
        if not self.visible:
            return self.change_map()
        # オートモード設定/解除（戦闘）
        if Battle.on and btn["w"]:
            Battle.auto = not Battle.auto
            self.battle_switch_auto()
        # エフェクトカウンタ更新
        Colors.update(btn["s"] or btn["a"])
        # 効果音/音楽→次の音楽
        Sounds.resume(self.hp <= 0)
        # フェード・強制音楽は操作を受け付けない
        if Fade.dist or Colors.flash or Sounds.waiting or talk_state == 0:
            return
        # イベント処理
        elif len(self.reserves) > 0:
            if self.do_event(talk_state, pressed):
                self.reserves.pop(0)
        # はいいいえウィンドウ
        if "yn" in self.windows:
            win = self.windows["yn"].update_cursol(btn)
            if btn["a"] or btn["s"]:
                answer = btn["s"] and win.cur_y == 0
                self.reserve(win.kind, answer, win.parm)
                self.close_win("yn")
        # ウェルカム画面（名前）
        elif "name" in self.windows:
            win = self.windows["name"].update_cursol(btn)
            if win.cur_x == 7 and win.cur_y == 7:
                win.cur_x += 1 if btn["r"] else -1
            if win.cur_x == 9 and win.cur_y == 7:
                win.cur_x -= 9 if btn["r"] else 1
            disp_name = ""
            name = ""
            parm = self.windows["welcome"].parm
            idx = len(parm) if len(parm) < 4 else 3
            for i in range(4):
                if len(parm) > i:
                    name += parm[i]
                    disp_name += parm[i]
                else:
                    disp_name += " " if i == idx and px.frame_count % 20 < 10 else "＊"
            self.next_talk(f"なまえを いれてください\n {disp_name}")
            is_delete = False
            if btn["s"]:
                if win.cur_x == 6 and win.cur_y == 7:
                    is_delete = True
                elif win.cur_x == 8 and win.cur_y == 7:
                    if len(name) > 0:
                        self.name = name
                        self.close_win("name")
                        self.next_talk("あなたの せいかくを きめてください")
                        texts = [f" {p['name']}" for p in master["personalities"]]
                        self.upsert_win("personality_guide", 15, 0, 26, 5, [])
                        self.upsert_win("personality", 3, 0, 12, 5, texts).add_cursol()
                else:
                    letter = const.NAME_TEXTS[win.cur_y][win.cur_x]
                    if len(parm) < 4:
                        parm.append(letter)
                    if idx >= 3:
                        win.cur_x = 9
                        win.cur_y = 7
            if btn["a"] or is_delete:
                if idx > 0:
                    parm.pop(-1)
                elif btn["a"]:
                    self.close_win("name")
                    self.open_welcome()
        # ウェルカム画面（性格）
        elif "personality" in self.windows:
            win = self.windows["personality"].update_cursol(btn)
            idx = win.cur_y
            personality = master["personalities"][idx]
            pname = personality["name"]
            self.windows["personality_guide"].texts = [f"{pname}："] + personality[
                "guide"
            ].split("\n")
            if btn["s"]:
                self.max_hp = personality["max_hp"]
                self.max_mp = personality["max_mp"]
                self.power = personality["power"]
                self.speed = personality["speed"]
                self.close_win(["welcome", "personality", "personality_guide"])
                self.next_talk(f"なまえ： %\nせいかく： {pname}\n\nこれで よろしいですか？", True)
                self.open_yn("make_player", idx)
            elif btn["a"]:
                self.close_win(["personality", "personality_guide"])
                self.open_name()
        elif "save_code" in self.windows:
            win = self.windows["save_code"].update_cursol(btn)
            if win.cur_x == 0 and win.cur_y == 2:
                win.cur_x += 3 if btn["l"] else 1
            if win.cur_x == 2 and win.cur_y == 2:
                win.cur_x += 1 if btn["r"] else -1
            if win.cur_x == 4 and win.cur_y == 2:
                win.cur_x -= 3 if btn["r"] else 1
            disp_code = ""
            code = ""
            parm = self.windows["welcome"].kind
            idx = len(parm) if len(parm) < 6 else 5
            for i in range(6):
                if len(parm) > i:
                    code += parm[i]
                    disp_code += parm[i]
                else:
                    disp_code += " " if i == idx and px.frame_count % 20 < 10 else "＊"
            self.next_talk(f"セーブコードを いれてください\n{disp_code}")
            is_delete = False
            if btn["s"]:
                if win.cur_x == 1 and win.cur_y == 2:
                    is_delete = True
                elif win.cur_x == 3 and win.cur_y == 2:
                    if len(code) >= 6:
                        self.prev_code = code
                        map_name = self.load_data()
                        if map_name:
                            self.close_win()
                            self.set_map(map_name, pl.x, pl.y)
                        else:
                            self.close_win("save_code")
                            self.windows["welcome"].kind = []
                            self.next_talk("セーブコードが まちがっています")
                else:
                    letter = const.SAVE_CODES[win.cur_y][win.cur_x]
                    if len(parm) < 6:
                        parm.append(letter)
                    if idx >= 5:
                        win.cur_x = 3
                        win.cur_y = 2
            if btn["a"] or is_delete:
                if idx > 0:
                    parm.pop(-1)
                elif btn["a"]:
                    self.close_win("save_code")
                    self.open_welcome()
        # ウェルカム画面（はじめから／つづきから）
        elif "welcome" in self.windows:
            win = self.windows["welcome"].update_cursol(btn)
            if btn["s"]:
                if win.cur_y == 0:
                    self.open_name()
                else:
                    texts = []
                    for (idx, line) in enumerate(const.SAVE_CODES):
                        text = ""
                        for letter in line:
                            text += f" {letter}"
                        if idx == 2:
                            text += "   もどる おわり"
                        texts.append(text)
                    self.upsert_win("save_code", 9, 4, 20, 8, texts).add_cursol(3, 5)
        # 商品選択ウィンドウ
        elif "shop_items" in self.windows:
            win = self.windows["shop_items"].update_cursol(btn)
            id = win.cur_ids[win.cur_y]
            self.guide_item(id)
            if btn["s"]:
                item = gm.item(id)
                if item["price"] * 2 > self.gold:
                    if win.kind == "weapon":
                        self.talk("＊「おかねが たりないようだな")
                    else:
                        self.talk("＊「おかねが たりないようですね")
                    return
                self.close_win("item_guide")
                if item["kind"] < 4:
                    equip = gm.item(self.equips[item["kind"]])
                    price = equip["price"]
                    if price:
                        self.talk(
                            f"＊「いまつかっている\n  {equip['name']}を\n  {price}'ゴールドでひきとろうか？"
                        )
                        return self.reserve("yn", "sell_and_buy", id)
                self.buy_item(id, False)
            elif btn["a"]:
                self.shop_other(win.kind, win.parm)
        # どうぐを売るウィンドウ
        elif "shop_sell" in self.windows:
            win = self.windows["shop_sell"].update_cursol(btn)
            id = self.items[win.cur_y]
            kind = win.kind
            if btn["s"]:
                item = gm.item(id)
                if item["price"] == 0:
                    if kind == "weapon":
                        self.talk(f"＊「わるいが それは ひきとれないな。")
                    else:
                        self.talk(f"＊「そちらは おひきとりできません。")
                    return
                self.change_item(None, win.cur_y)
                self.add_gold(item["price"])
                if len(self.items) > 0:
                    if kind == "weapon":
                        self.talk(f"＊「どうも。 ほかにも うるかね？")
                    else:
                        self.talk(f"＊「まいど ありがとうございます。\n  ほかにも おうりですか？")
                    self.open_shop_sell(kind, win.parm)
                else:
                    self.shop_other(kind, win.parm, True)
            elif btn["a"]:
                self.shop_other(kind, win.parm)
        # 買う売るウィンドウ
        elif "shop_buysell" in self.windows:
            win = self.windows["shop_buysell"].update_cursol(btn)
            kind = win.kind
            if btn["a"]:
                self.close_win("shop_buysell")
                if kind == "weapon":
                    self.talk("＊「また きてくれよな。")
                else:
                    self.talk("＊「またのおこしを おまちしております。")
            elif btn["s"]:
                if win.cur_y == 0:
                    if kind == "weapon":
                        self.talk("＊「なにを かうかね？")
                    else:
                        self.talk("＊「どれを おもとめですか？")
                    items = win.parm
                    texts = []
                    cur_ids = []
                    for id in items:
                        item = gm.item(id)
                        texts.append(
                            f" {util.spacing(item['name'], 7)}{util.padding(item['price'] * 2, 5)}G"
                        )
                        cur_ids.append(id)
                    win = self.upsert_win("shop_items", 13, 0, 28, 7, texts)
                    win.add_cursol()
                    win.cur_ids = cur_ids
                    win.kind = kind
                    win.parm = items
                else:
                    if len(self.items) == 0:
                        if kind == "weapon":
                            self.talk("＊「うれるものが ないようだよ")
                        else:
                            self.talk("＊「うれるものが ないようですね")
                        return
                    if kind == "weapon":
                        self.talk("＊「なにを うってくれるんだい？")
                    else:
                        self.talk("＊「どれを おうりですか？")
                    self.open_shop_sell(kind, self.windows["shop_buysell"].parm)
                self.close_win("shop_buysell")
        # 会話ウィンドウ入力待ち
        elif talk_state >= 0:
            if pressed:
                if talk_state == 1:
                    self.windows["talk"].next()
                elif talk_state == 9:
                    self.close_talk()
        # つよさ
        elif "detail_base" in self.windows:
            if pressed:
                self.close_win(["property", "detail_base", "detail_spells"])
        # じゅもん
        elif "spells" in self.windows:
            # じゅもん選択
            if "spells_guide" in self.windows:
                win = self.windows["spells"].update_cursol(btn)
                id = self.update_spells_guide()
                if btn["s"]:
                    if self.can_spell(id):
                        self.close_win("spells_guide")
                        self.use_spell(id)
                elif btn["a"]:
                    self.close_win(["spells_guide", "spells"])
        # どうぐ
        elif "items" in self.windows:
            win = self.windows["items"].update_cursol(btn)
            idx = win.cur_y
            id = self.items[idx]
            self.guide_item(id)
            if btn["s"]:
                self.use_item(id, idx)
            elif btn["a"]:
                self.close_win(["items", "item_guide"])
        # さくせん
        elif "auto_settings" in self.windows:
            win = self.windows["auto_settings"].update_cursol(btn)
            win.texts = [
                f" {util.spacing(s['label'],8)}： {s['options'][self.auto_settings[s['key']]]}"
                for s in master["auto_settings"]
            ]
            idx = win.cur_y
            setting = master["auto_settings"][idx]
            self.windows["auto_settings_guide"].texts = [
                f"{setting['label']}："
            ] + setting["description"].split("\n")
            if btn["s"] or btn["a"]:
                self.close_win(["auto_settings", "auto_settings_guide"])
            elif btn["r"]:
                self.change_auto_settings(idx, 1)
            elif btn["l"]:
                self.change_auto_settings(idx, -1)
        # メニュー（戦闘）
        elif "battle" in self.windows:
            win = self.windows["battle"].update_cursol(btn)
            if btn["s"]:
                # たたかう
                if win.cur_y == 0:
                    self.cmd_blow()
                # じゅもん
                elif win.cur_y == 1:
                    if self.is_sealed:
                        self.next_talk("しかし じゅもんは\nふうじこめられている！")
                    else:
                        self.open_spells()
                # どうぐ
                elif win.cur_y == 2:
                    self.open_items()
                # にげる
                elif win.cur_y == 3:
                    self.close_win("battle")
                    self.cmd_escape()
        # 会話ウィンドウ（戦闘時）
        elif Battle.on:
            if Battle.myturn and not Battle.auto and not Battle.action:
                self.battle_manage()
            elif btn["s"] or btn["a"] or btn["w"]:
                self.battle_manage()
        # メニュー（フィールド）
        elif "menu" in self.windows:
            win = self.windows["menu"].update_cursol(btn)
            if btn["a"]:
                self.close_win("menu")
            elif btn["s"]:
                # つよさ
                if win.cur_y == 0:
                    self.show_property()
                    self.open_detail()
                # じゅもん
                elif win.cur_y == 1:
                    self.open_spells()
                # どうぐ
                elif win.cur_y == 2:
                    self.open_items()
                # さくせん
                elif win.cur_y == 3:
                    self.upsert_win("auto_settings_guide", 2, 9, 27, 14, [])
                    self.upsert_win("auto_settings", 4, 3, 25, 8, []).add_cursol(4)
                # きろく
                elif win.cur_y == 4:
                    self.talk("ぼうけんのせいかを きろくしますか？")
                    self.reserve("yn", "save")
        # 城から強制退去
        elif self.is_curse() and Actor.cur_map.music == "dq1catsle":
            if len(self.reserves) == 0 and not self.next_map:  # 二重発動防止
                self.talk("＊「のろわれしものよ でてゆけっ！")
                self.reserve("deport")
        # 移動操作
        elif pl.dx == 0 and pl.dy == 0:
            # オート回復（強制後退の後で発動）
            if self.cure_suggestion:
                suggestion = None
                hp = self.hp + 6 if self.equip_item(const.RT_ARMOR) else self.hp
                if hp <= self.max_hp / 2 or hp <= self.max_hp - 30:
                    has_herb = self.has_item(const.HERB)
                    if hp <= self.max_hp - 72 and self.can_spell(const.BHIM, True):
                        suggestion = "BHIM"
                    elif self.can_spell(0, True):
                        suggestion = "HIM"
                    elif has_herb:
                        suggestion = "herb"
                    if self.auto_settings["cure"] == 2 and has_herb:
                        suggestion = "herb"
                if suggestion == "BHIM":
                    self.use_spell(const.BHIM)
                elif suggestion == "HIM":
                    self.use_spell(const.HIM)
                elif suggestion == "herb":
                    self.use_item(const.HERB)
                else:
                    self.cure_suggestion = False
            elif len(self.reserves) == 0:
                operable = True
                if btn["s"]:  # メニューを開く
                    self.show_status()
                    self.upsert_win(
                        "menu", 20, 0, 26, 6, [" つよさ", " じゅもん", " どうぐ", " さくせん", " きろく"]
                    ).add_cursol()
                elif not "status" in self.windows:
                    self.status_timer += 1
                    if self.status_timer >= 30:
                        self.show_status()
        # actorが動く
        for actor in Actor.actors:
            actor.update(operable, btn)
        # 主人公の移動中はステータスウィンドウを閉じる
        if pl.steps and not "talk" in self.windows:
            self.close_status()
        # 主人公が何かと衝突
        if pl.collision:
            actor = pl.collision
            self.start_event(actor)
            actor.is_talking = True
            pl.collision = None
        # 主人公が一歩歩いた
        if pl.moved:
            pl.moved = False
            self.logs["steps"] += 1
            cell = map_cells[Actor.cur_map.map_no][pl.y][pl.x]
            # 毒の沼地
            if cell == "2":
                self.poison(1, 14)
            # バリア
            elif cell == "c":
                self.poison(15, 20)
            # ロトのよろいによる回復
            if self.equip_item(const.RT_ARMOR):
                self.add_hp(1, True)
            if pl.overlap:  # イベント発動
                self.start_event(pl.overlap)
                pl.overlap = None
                return
            # ジャンプ判定
            if self.check_jump():
                return
            # 屋根の中へ
            for actor in Actor.actors:
                if actor.chr == 14 and actor.x == pl.x and actor.y == pl.y:
                    self.set_map(Actor.cur_map.name + "b", pl.x, pl.y)
            # 屋根の外へ
            if cell == "s":
                self.set_map(Actor.cur_map.name.rstrip("b"), pl.x, pl.y)
            # 移動補助じゅもんの効果切れ判定
            for key in self.support:
                if self.support[key] > 0:
                    self.support[key] -= 1
                    if self.support[key] == 0:
                        # トヘロス/レミーラ
                        if key in ["THRS", "RMR"]:
                            if key == "THRS" and self.support["HOLYWATER"]:
                                return
                            if key == "RMR" and self.support["TORCHLIGHT"]:
                                return
                            spell = gm.spell(key)
                            id = spell["id"]
                            texts = spell["name"] + "の こうかが なくなった。"
                            reusable = self.can_spell(id, True)
                            if reusable:
                                texts += f"\nもういちど つかいますか？\nしょうひMP {spell['mp']}"
                            self.talk(texts)
                            if reusable:
                                self.show_status()
                                self.reserve("yn", "spell_yn", id)
                        # せいすい/たいまつ
                        if key in ["HOLYWATER", "TORCHLIGHT"]:
                            if key == "HOLYWATER" and self.support["THRS"]:
                                pass
                            elif key == "TORCHLIGHT" and self.support["RMR"]:
                                pass
                            else:
                                id = (
                                    const.HOLYWATER
                                    if key == "HOLYWATER"
                                    else const.TORCHLIGHT
                                )
                                texts = gm.item(id)["name"] + "の こうかが なくなった。"
                                cnt = self.has_item(id)
                                if cnt > 0:
                                    texts += f"\nもういちど つかいますか？\nのこり {cnt}こ"
                                self.talk(texts)
                                if cnt > 0:
                                    self.reserve("yn", "item_yn", id)
                        return
            # エンカウント判定
            danger = 2
            if cell in ["4"]:  # 森、ダンジョン
                danger = 3
            elif cell in ["4", "5"]:  # 森、ダンジョン
                danger = 4
            elif cell in ["2", "7"]:  # 砂地、毒沼
                danger = 5
            elif cell == "6":  # 山
                danger = 6
            self.encount -= danger
            if self.equip_item(const.CURSE_BELT):  # 呪いのベルト効果
                self.encount -= danger
            self.do_encount()
            print(f"座標:{pl.x}, {pl.y} エンカウント値：{self.encount}")

    def draw(self):
        px.cls(0)
        if not self.visible:
            return
        # ウエイト処理
        if self.wait:
            self.wait -= 1
            return
        pl = self.player
        if Fade.dist:  # フェードイン・アウト
            self.visible = Fade.draw()
        else:  # パレット処理
            Colors.draw(self.hp <= 0)
        # マップ
        if Actor.cur_map and not (Battle.on and Battle.rollout == 0):
            vision = 14
            if Actor.cur_map.kind == 2:
                light = max(self.support["RMR"], self.support["TORCHLIGHT"])
                vision = 1 + (light + 31) // 32
            mx = (pl.x - vision / 2) * 16 + pl.sx
            my = (pl.y - vision / 2) * 16 + pl.sy
            u = min(max(mx, 0), (127 - vision) * 16)
            v = min(max(my, 0), (127 - vision) * 16)
            xy = 112 - vision * 8
            wh = vision * 16 + 16
            px.bltm(xy, xy, Actor.cur_map.map_no, u, v, wh, wh)
            # キャラクタ
            for actor in Actor.actors:
                is_dead = False
                if actor.is_player:
                    actor.chr = 16 if self.with_princess else 0
                    is_dead = self.hp <= 0
                actor.draw(u - xy, v - xy, vision, is_dead)
            # ライトの端
            if vision < 14:
                end = xy + wh - 8
                px.blt(xy, xy, 0, 80, 128, 8, 8, const.TRANSPARENT)
                px.blt(end, xy, 0, 96, 128, 8, 8, const.TRANSPARENT)
                px.blt(xy, end, 0, 120, 128, 8, 8, const.TRANSPARENT)
                px.blt(end, end, 0, 136, 128, 8, 8, const.TRANSPARENT)
                px.rect(xy - 8, xy - 16, vision * 16 + 32, 16, 0)
                px.rect(xy - 8, end + 8, vision * 16 + 32, 16, 0)
                px.rect(xy - 16, xy - 8, 16, vision * 16 + 32, 0)
                px.rect(end + 8, xy - 8, 16, vision * 16 + 32, 0)
                for i in range(vision * 2):
                    s = (i + 1) * 8
                    px.blt(xy + s, xy, 0, 88, 128, 8, 8, const.TRANSPARENT)
                    px.blt(xy + s, end, 0, 128, 128, 8, 8, const.TRANSPARENT)
                    px.blt(xy, xy + s, 0, 104, 128, 8, 8, const.TRANSPARENT)
                    px.blt(end, xy + s, 0, 112, 128, 8, 8, const.TRANSPARENT)
            # ロールアウト（戦闘開始）
            if Colors.flash == 0:
                Battle.draw_rollout()
        # 各種ウィンドウ
        if Battle.rollout <= 1:
            for key in self.windows:
                self.windows[key].draw()
        # モンスター
        Battle.draw_enemy()
        # ゆれ
        if self.shaking > 0:
            px.camera(px.rndi(-3, 3), px.rndi(-3, 3))
            self.shaking -= 1
        else:
            px.camera()

    # イベント発動
    def start_event(self, actor):
        if actor.event:
            event = actor.event.split(" ")
            type, parm, id = None, None, None
            if len(event) > 1:
                type = event[0]
                parm = event[1]
            else:
                id = event[0]
            self.show_status()
            if type == "item":
                id = int(parm)
                item = gm.item(id)
                self.talk(f"たからばこには {item['name']}が\nはいっていた！", True)
                if self.add_item(id):
                    self.open_treasure(actor)
            elif type == "gold":
                self.talk(f"たからばこには {parm}G\nはいっていた！", True)
                self.add_gold(int(parm))
                self.open_treasure(actor)
            elif type == "inn":
                self.reserve("inn_open", int(parm))
            elif type == "weapon":
                self.show_property()
                self.talk(f"＊「ここは ぶきとぼうぐの みせだ。\n  なんの ようだね？")
                self.reserve("shop", "weapon", util.list_str2int(parm.split(",")))
            elif type == "tool":
                self.show_property()
                self.talk(f"＊「いらっしゃいませ。\n  ここは どうぐや です。\n  どんな ごようでしょうか？")
                self.reserve("shop", "tool", util.list_str2int(parm.split(",")))
            elif type == "lock":
                self.show_property()
                self.talk(f"＊「どんなとびらも あけてしまう\n  まほうの かぎは いらんかな？\n  ひとつ {parm}ゴールド じゃ。")
                self.reserve("yn", "shop_lock", int(parm))
            elif type == "water":
                self.show_property()
                self.talk(f"＊「まものよけの せいすいは\n  いかがですか？\n  ひとつ {parm}ゴールド です。")
                self.reserve("yn", "shop_water", int(parm))
            elif type == "find":
                id = int(parm)
                item = gm.item(id)
                self.message_find(item["name"])
                self.add_item(id)
                return True
            elif type == "battle":
                self.start_battle(int(parm), True)
            elif type == "msg":
                self.talk(messages[parm])
            else:  # 汎用イベント
                self.reserve(id, actor)
        elif actor.door:
            cnt = self.has_item(const.KEY)
            if cnt == 0:
                self.talk("かぎが かかっている！")
            else:
                Sounds.sound(18)
                self.talk(f"かぎを あけた\nのこり {cnt-1}こ")
                self.consume_item(const.KEY)
                self.opened.append(actor.door)
                remove_actor(actor)

    def do_event(self, talk_state, pressed):
        event = self.reserves[0]["event"]
        parm1 = self.reserves[0]["parm1"]
        parm2 = self.reserves[0]["parm2"]
        parm3 = self.reserves[0]["parm3"]
        pl = self.player
        if event == "reset":  # リセット
            self.talk(
                [
                    f"＊「おお %よ\n  わるいゆめを みていたようじゃな。",
                    "＊「つぎは このようなことがないように\n  きをつけるのじゃぞ。",
                    f"＊「ではゆけ %よ！",
                ]
            )
            self.gold = 0 if self.dispel_curse() else self.gold // 2  # のろいを強制解除
        elif event == "dead":  # 死亡
            Battle.off()
            self.reset_game()
            self.visible = False
        elif event == "yn":  # はいいいえウィンドウを開く
            if talk_state < 9:
                return False
            self.open_yn(parm1, parm2)
        elif event == "make_player":  # キャラメイク完了
            if parm1:
                Grade(1, 0, parm2)
                self.items = []
                self.equips = [None, 7, None, None]
                self.gold = 0
                self.support = {
                    "THRS": 0,
                    "RMR": 0,
                    "HOLYWATER": 0,
                    "TORCHLIGHT": 0,
                }
                self.auto_settings = {"default": 0, "escape": 0, "spell": 1, "cure": 0}
                self.opened = []  # 開けた宝箱
                self.flags = [5, 13]  # イベントフラグ
                self.set_encount()
                self.reset_game(True)
                self.close_win()
                self.reserve("opening")
            else:
                self.open_welcome()
        elif event == "opening":
            self.talk(
                [
                    f"＊「おお %！\n  ゆうしゃロトの ちをひくものよ！\n  そなたがくるのを まっておったぞ。",
                    "＊「その むかし ゆうしゃロトが\n  カミから ひかりのたまをさずかり\n  まものたちを ふうじこめたという。",
                    "＊「しかし いずこともなくあらわれた\n  あくまのけしん りゅうようが\n  そのたまを やみにとざしたのじゃ",
                    f"＊「ゆうしゃ %よ！\n  りゅうおうをたおし そのてから\n  ひかりのたまを とりもどしてくれ！",
                    "＊「わしからの おくりものじゃ！\n  そなたのよこにある\n  たからのはこを とるがよい！",
                    "＊「そして このへやにいる\n  へいしにきけば たびのちしきを\n  おしえてくれよう。",
                    f"＊「では また あおう！\n  ゆうしゃ % よ！",
                ]
            )
        elif event == "battle":  # 戦闘
            self.show_status()
            Colors.set_flash(3 if Battle.is_boss else 2)
            en = Battle.enemy
            if en["id"] == const.DRAGON_KING:
                self.talk(en["name"] + "が しょうたいを\nあらわした！！")
                Sounds.sound(19)
                Sounds.bgm("dq1boss")
            else:
                self.talk(en["name"] + "が あらわれた！")
                if Battle.is_boss:
                    Sounds.bgm("dq1encount", False, "dq1battle")
                else:
                    Sounds.bgm("dq1battle")
            spd_pl = int(self.speed * px.rndf(1.0, 2.0))
            spd_en = int(en["speed"] * px.rndf(0.0, 2.0))
            print("敵のHP：", en["hp"])
            print("すばやさ：", self.speed, "-", en["speed"])
            if spd_pl > spd_en:
                self.battle_myturn()
                surprise = int(1 + self.speed / en["speed"])
                print("先制確率：", surprise, "/32")
                if surprise > px.rndi(0, 31):
                    self.talk("てきはまだ こちらに きづいていない！")
                    en["surprised"] = True
            else:
                self.battle_enemyturn()
                self.talk("てきは こちらがみがまえるより\nはやく おそってきた！")
        elif event == "win":  # 勝利後
            if parm3:
                if parm1 == const.DRAGON:
                    pl.move(0, 1)
                elif parm1 == const.GOLEM:
                    pl.move(0, -1)
                elif parm1 == const.DEVIL_KNIGHT and parm2:
                    pl.move(-1, 0)
            else:
                self.close_status()
                if parm1 == const.DRAGON:
                    self.flags.append(3)
                elif parm1 == const.GOLEM:
                    self.talk("ようせいのふえは おとをたてて\nくずれさった")
                    self.consume_item(const.FLUTE)
                    self.flags.append(7)
                elif parm1 == const.DEVIL_KNIGHT and parm2:
                    self.flags.append(8)
                self.set_actors()
        elif event == "spell_yn":  # じゅもんを使う？
            if parm1:
                self.use_spell(parm2)
            else:
                self.close_talk()
        elif event == "spell_field":  # じゅもん（フィールド）
            symbol = gm.spell(parm1)["symbol"]
            if parm1 in [const.HIM, const.BHIM]:  # ホイミ、ベホイミ
                self.add_hp(gm.calc_cure(symbol))
                # メニュー経由のときは連続使用できるようにする
                if "spells" in self.windows:
                    self.open_spells_guide()
                    self.update_spells_guide()
                    return True
            elif parm1 == const.RMR:  # レミーラ
                self.support[symbol] = const.EFFECT_RMR
            elif parm1 == const.THRS:  # トヘロス
                self.support[symbol] = const.EFFECT_THRS
            elif parm1 == const.RRMT:  # リレミト
                self.close_status()
                self.set_map("field", self.exit_x, self.exit_y, 4)
            elif parm1 == const.RR:  # ルーラ
                self.jump_to_start()
            self.close_win(["spells", "menu"])
        elif event == "item_yn":  # アイテムを使う？
            if parm1:
                self.use_item(parm2)
            else:
                self.close_talk()
        elif event == "abandon_yn":  # アイテムを捨てる？
            self.close_talk()
            if parm1:
                self.open_items(True)
        elif event == "kimera":  # キメラのつばさ
            self.jump_to_start()
        elif event == "flute":  # ようせいのふえ音楽終了
            self.cmd_end("flute")
        elif event == "harp":  # ぎんのたてごと音楽終了
            self.close_win()
            self.do_encount(True)
        elif event == "rainbow":  # にじのかけら音楽終了
            if talk_state > 0:
                return
            Colors.rainbow = True
            self.close_win()
            Sounds.wait("dq1rainbow")
            self.reserve("rainbow_done")
        elif event == "rainbow_done":
            Colors.rainbow = False
            self.flags.append(10)
            self.set_actors()
            self.consume_item(const.RAINBOW_DROP)
        elif event == "save":  # セーブ
            if parm1:
                self.save_code = self.save_data()
                self.talk(
                    f"セーブコードは {self.save_code} です。\nかならず メモをとるか\nスクリーンショットを とってください。"
                )
            else:
                self.close_talk()
        elif event == "deport":  # 強制退去
            if talk_state >= 0:
                return False
            Colors.set_flash(3)
            self.reserve("deport_act")
        elif event == "deport_act":  # 強制退去
            self.deport()
        elif event == "recover_mp":  # ひかりあれ
            Colors.set_flash(3)
            self.reserve("recover_mp_done")
        elif event == "recover_mp_done":
            self.mp = self.max_mp
            self.show_status()
        elif event == "flash":  # ただのフラッシュ
            Colors.set_flash(3)
        elif event == "move":  # キャラクタを動かす（？）
            if talk_state < 9:
                return False
            parm1.move(parm2, parm3)
        elif event == "inn_open":  # 宿屋
            self.show_property()
            self.talk(f"＊「たびびとのやどやへ ようこそ。\n  ひとばん {parm1}ゴールドですが\n  おとまりに なりますか？")
            if self.gold >= parm1:
                self.reserve("yn", "inn_yn", parm1)
            else:
                self.talk("＊「おや おかねが たりないようですね。\n  また どうぞ。")
        elif event == "inn_yn":
            if parm1:
                if self.with_princess:
                    self.talk(f"ローラ「まあ %さま…")
                    self.reserve("inn_princess")
                else:
                    self.gold -= parm2
                    self.recover_full()
                    self.close_talk()
                    Sounds.bgm("dq1inn", False)
                    Fade.start(True)
                    self.reserve("inn_done")
            else:
                self.talk("＊「さようなら たびのひと。\n  あまり むりを なさいませぬように。")
        elif event == "inn_princess":
            if talk_state > 0:
                return
            Sounds.wait("dq1curse")
            self.talk("ローラ「ローラは はやく おしろに\n    かえりとう ございますわ")
        elif event == "inn_done":
            self.show_status()
            self.show_property()
            self.map_bgm()
            self.talk("＊「ゆうべは よく おやすみでしたね。\n  では また どうぞ。")
        elif event == "shop":  # お店
            self.open_shop_buysell(parm1, parm2)
        elif event == "sell_and_buy":
            self.buy_item(parm2, parm1)
        elif event in ["shop_lock", "shop_water"]:
            if parm1:
                if parm2 > self.gold:
                    if event == "shop_lock":
                        self.talk("＊「おかねが たりないようじゃな")
                    else:
                        self.talk("＊「おかねが たりませんよ")
                elif len(self.items) >= 8:
                    if event == "shop_lock":
                        self.talk("＊「それいじょう もてないようじゃな")
                    else:
                        self.talk("＊「それいじょう もてませんよ")
                else:
                    if event == "shop_lock":
                        self.change_item(const.KEY)
                    else:
                        self.change_item(const.HOLYWATER)
                    self.add_gold(-parm2)
                    if event == "shop_lock":
                        self.talk(f"＊「ほれ。 もうひとつ かうかね？")
                    else:
                        self.talk(f"＊「どうぞ。 もうひとつ どうですか？")
                    self.reserve("yn", event, parm2)
            else:
                self.close_talk()
        # ラダトーム
        elif event == "t22":
            if self.is_curse():
                self.talk("＊「のろいをといて しんぜよう。")
                self.reserve("t22_2")
            else:
                self.talk("＊「もし そなたが のろわれたなら\n  ここに くるがよい。\n  きっと ちからになってやるぞ。")
        elif event == "t22_2":
            if talk_state > 0:
                return
            Colors.set_flash(3)
            self.reserve("t22_3")
        elif event == "t22_3":
            self.talk("＊「さあ ゆくがよい。")
            self.dispel_curse()
        # リムルダール
        elif event == "t47":
            if self.equip_item(const.FIGHTER_RING):
                self.talk("＊「おまえがつけている ゆびわには\n  かいしんのいちげきを\n  でやすくする ちからがあるぜ。")
            else:
                self.talk("＊「せんしも ゆびわくらいは\n  みにつけなくては。 それも\n  たしなみの ひとつだからな。")
        # メルキド
        elif event == "t57":
            cnt = len([i for i in self.opened if i < 30])
            self.talk(f"＊「このせかいには そなたが まだ\n  あけていない たからのはこが\n  あと {25-cnt}こ あるはずじゃ。")
        # ラダトーム城
        elif event == "c21":
            if self.with_princess:
                self.talk(
                    [
                        "＊「おお %！ よくぞ\n  ひめを たすけだしてくれた。\n  こころから れいをいうぞ！",
                        "＊「さあ ローラ。 わたしのとなりへ。",
                        "＊ローラ「まってください。 ローラは\n     %さまに おくりものを\n     しとうございます。",
                        "＊ローラ「%さまを おしたいする\n     わたしの こころ。 どうか\n     うけとってくださいませ。",
                        "＊ローラ「ああ！ たとえ はなれて\n     いても ローラは いつも\n     あなたと ともに あります。",
                    ]
                )
                self.reserve("c21_2")
            else:
                lvup_text = (
                    f"＊「そなたが つぎのレベルになるには\n  あと {Grade.to_lvup()}ポイントの\n  けいけんが ひつようじゃ"
                )
                if Grade.is_max_lv():
                    lvup_text = "そなたは もう\n  じゅうぶんに つよい！ なぜに \n  まだ りゅうおうを たおせぬのか？"
                self.talk(
                    [
                        "＊「おお %！\n  よくぞ ぶじで もどってきた。\n  わしは とても うれしいぞ。",
                        lvup_text,
                        "＊「では また あおう！\n  ゆうしゃ %よ！",
                    ]
                )
        elif event == "c21_2":
            if talk_state < 9:
                return False
            self.flags.remove(5)
            self.change_item(const.PRINCESS)
            self.set_actors()
        elif event == "c25":
            if 4 in self.flags:
                self.talk("＊「おお %！\n  すばらしき ゆうしゃよ！")
            else:
                self.talk("＊「ローラひめのことを ごぞんじか？")
                self.reserve("yn", "c25_2")
        elif event == "c25_2":
            texts = []
            if not parm1:
                texts = [
                    "＊「ひめさまが まものたちに\n  さらわれて ひとつきになる…",
                    "＊「おうさまは なにも\n  おっしゃらないが\n  とても くるしんでいるはず。",
                ]
            texts.append("＊「どうか ひめを\n  たすけだして ください！")
            self.talk(texts)
        elif event == "c28":
            if 4 in self.flags:
                self.talk("＊「ああ %さま！\n  ひめさまを たすけてくださって\n  ありがとうございます！")
            else:
                self.talk("＊「ああ ローラひめは\n  いったい どこに…")
        elif event == "c33":
            self.talk("＊「おお カミよ！\n  ふるい いいつたえの ゆうしゃ\n  %に ひかり あれ！")
            self.reserve("recover_mp")
        elif event == "c38":
            logs = self.logs
            self.talk(
                [
                    "＊「そなたの これまでの\n  たたかいの せいせきを\n  おしえてやろう。",
                    f"＊「しょうり {logs['win']}かい\n  とうそう {logs['escape']}かい\n  ぜんめつ {logs['dead']}かい",
                    "＊「まだまだ じゃな。",
                ]
            )
        # 雨のほこら
        elif event == "c10":
            if self.has_item(const.HARP) or 2 in self.flags:
                self.talk(
                    [
                        "＊「おお %\n  たてごとを もってきたな。",
                        "＊「わしは まっておった。\n  そなたのような わかものが\n  あわれることを…",
                        "＊「さあ たからのはこを\n  とるがよい。",
                    ]
                )
                self.reserve("move", parm1, 0, -1)
                if not 1 in self.flags:
                    self.flags.append(1)
                self.consume_item(const.HARP)
            else:
                self.talk(
                    [
                        "＊「そなたが まことの ゆうしゃか\n  どうか ためさせてほしい。",
                        "＊「このちの どこかに まものたちを\n  よびよせる ぎんのたてごとが\n  あるときく。",
                        "＊「それを もちかえったとき\n  そなたを ゆうしゃと みとめ\n  あまぐものつえを さずけよう。",
                    ]
                )
        # 聖なるほこら
        elif event == "c12":
            if self.has_item(const.RAINBOW_DROP) or 10 in self.flags:
                self.talk("＊「ロトの ちをひく ゆうしゃ\n  %に ひかり あれ！")
                self.reserve("recover_mp")
            elif self.has_item(const.RT_MARK) or self.equip_item(const.RT_MARK):
                if self.has_item(const.SUN_STONE) and self.has_item(const.RAIN_STAFF):
                    self.talk(
                        [
                            "＊「ロトの ちをひくものよ。\n  いまこそ あめと たいようが\n  あわさるときじゃ！",
                            "＊「そなたに にじのしずくを\n  あたえよう！",
                        ]
                    )
                    self.consume_item(const.SUN_STONE)
                    self.consume_item(const.RAIN_STAFF)
                    self.consume_item(const.RT_MARK)
                    self.change_item(const.RAINBOW_DROP)
                    self.reserve("c12_2")
                else:
                    self.talk(
                        ["＊「あめと たいようが あわさるとき\n  にじのはしが できる。\n  ゆくがよい。 そして さがすがよい。"]
                    )
            else:
                self.talk(
                    ["＊「そなたが ロトのちをひく\n  まことの ゆうしゃなら\n  しるしが あるはず", "＊「おろかものよ たちされい！"]
                )
                self.reserve("deport")
        elif event == "c12_2":
            if talk_state < 9:
                return False
            self.reserve("flash")
        # 沼地の洞窟 ローラ姫
        elif event == "d13":
            self.talk(
                [
                    "ローラ「ああ！ たすけたしてくださる\n    かたが ほんとうにいたなんて\n    まだ しんじられませんわ！",
                    "ローラ「わたしは ラルス16せいの\n    むすめ ローラです。",
                    "ローラ「わたしを おしろまで\n    つれてかえってくれますね？",
                    "あなたは ひめを だきかかえた",
                ]
            )
            self.reserve("d13_2")
        elif event == "d13_2":
            if talk_state < 9:
                return False
            Sounds.wait("dq1princess")
            self.reserve("d13_3")
        elif event == "d13_3":
            self.flags.append(4)
            self.set_actors()
            self.talk("ローラ「うれしゅうございます。 ぽっ")
        # 竜王の城
        elif event == "d21":
            self.message_find("かいだん")
            self.reserve("d21_2")
            self.flags.append(11)
            self.set_actors()
        elif event == "d21_2":
            if talk_state > 0:
                return False
            self.check_jump()
        elif event == "d19":
            self.talk(
                [
                    "＊「よくきた %よ。\n  わしが おうのなかの おう\n  りゅうおうだ。",
                    "＊「わしは まっておった。\n  そなたのような わかものが\n  あらわれることを…",
                    "＊「もし わしの みかたになれば\n  せかいの はんぶんを\n  %に やろう。",
                    "＊「どうじゃ？\n  わしの みかたに なるか？",
                ]
            )
            self.reserve("yn", "d19_2")
        elif event == "d19_2":
            if parm1:
                self.talk(
                    [
                        "＊「よろしい！では %に\n  せかいのはんぶん やみのせかいを\n  あたえよう！",
                        "＊「わあっ はっ はっ はっ はっ\n  わっ はっ はっ はっ はっ はっ",
                    ]
                )
                self.reserve("d19_3")
            else:
                self.talk("＊「おろかものめ！\n  おもいしるがよい！")
                self.reserve("d19_4")
        elif event == "d19_3":
            if talk_state > 0:
                return
            Fade.start(True)
            Sounds.wait("dq1inn")
            self.reset_game()
        elif event == "d19_4":
            self.close_win()
            return self.start_battle(const.DRAGON_LOAD, True)
        elif event == "finale":
            Battle.off()
            self.talk(
                [
                    "ひかりのたまを\nりゅうおうのてから とりもどした！",
                    "あなたが ひかりのたまを かざすと\nまばゆいばかりの ひかりが\nあふれだす…",
                    "このくにに へいわが もどったのだ。",
                ]
            )
            Actor.cur_map = None
            self.reserve("finale_1")
        elif event == "finale_1":
            if talk_state > 0:
                return
            if self.with_princess:
                self.flags.remove(5)
                self.flags.remove(13)
            self.visible = False
            self.wait = 20
            self.set_map("catsle1-4", 18, 56, 4)
            self.reserve("finale_2")
        elif event == "finale_2":
            self.talk(
                [
                    "＊「おお！ %！\n  すべては ふるい いいつたえの\n  ままで あった！",
                    "＊「すなわち そなたこそは\n  ゆうしゃロトの ちをひくもの！",
                    "＊「そなたこそ このせかいを\n  おさまるに ふさわしい おかた\n  なのじゃ！",
                    "＊「わしに かわって\n  このくにを おさめてくれるな？",
                    "しかし %は いいました。",
                    "＊「いいえ。 わたしの おさめる\n  くにが あるなら それは\n  わたしじしんで さがしたいのです。",
                ]
            )
            if 5 in self.flags and not 4 in self.flags:
                self.reserve("finale_6")  # ローラ姫未救出
            else:
                self.reserve("finale_3")
        elif event == "finale_3":
            if talk_state > 0:
                return
            self.talk("ローラ「まってくださいませ！")
            if 4 in self.flags and 13 in self.flags:
                target = Actor({"x": 7, "y": 7, "chr": 1})
                Actor.actors.append(target)
                target.move(1, 0, 3)
            self.reserve("finale_4", target)
        elif event == "finale_4":
            if talk_state > 0 or parm1.steps > 0:
                return
            self.talk(
                [
                    "ローラ「その あなたの たびに\n    ローラも\n    おともしとうございます。",
                    "ローラ「このローラも つれていって\n    くださいますわね？",
                    "あなたは つよく うなずいた。",
                ]
            )
            self.reserve("finale_5")
        elif event == "finale_5":
            if talk_state < 9:
                return
            self.talk("ローラ「うれしゅうございます。 ぽっ")
            self.flags.append(12)
            if not 13 in self.flags:
                self.flags.append(13)
            self.set_actors()
            self.reserve("finale_6")
        elif event == "finale_6":
            if talk_state > 0:
                return
            self.talk([f"\n %の\n   あらたなたびが はじまる。"])
            self.reserve("finale_7")
        elif event == "finale_7":
            for actor in Actor.actors:
                if actor.chr == 4:
                    actor.chr = 5
            Sounds.wait("dq1fanfare", "dq1finale")
            self.reserve("finale_8")
        elif event == "finale_8":
            self.is_ending = True
            self.save_code = self.save_data()
            self.talk(f"さいごまで プレイしてくれて\nありがとう！\nセーブコード：{self.save_code}")
            self.reserve("finale_9")
        elif event == "finale_9":
            if talk_state > 0:
                return
            logs = self.logs
            self.show_status()
            self.show_property()
            self.talk(
                [
                    f"プレイじかん {util.get_play_time(logs)}\nほすう {logs['steps']}\nロードかいすう {logs['loaded']}",
                    f"しょうり {logs['win']}かい\nとうそう {logs['escape']}かい\nぜんめつ {logs['dead']}かい",
                    "タイトルに もどりますか？\n\n",
                ],
            )
            self.reserve("yn", "finale_10")
        elif event == "finale_10":
            if parm1:
                Actor.cur_map = None
                self.close_status()
                self.open_welcome()
            else:
                self.close_talk()
                self.open_detail()
                self.reserve("finale_11")
        elif event == "finale_11":
            if not pressed:
                return False
            self.close_win(["detail_base", "detail_spells"])
            self.reserve("finale_9")
        return True

    # リザーブオブジェクト生成
    def reserve(self, event, parm1=None, parm2=None, parm3=None):
        self.reserves.append(
            {
                "event": event,
                "parm1": parm1,
                "parm2": parm2,
                "parm3": parm3,
            }
        )

    ### セーブ・ロード ###

    # リセット処理
    def reset_game(self, is_opening=False):
        # ドラゴンとローラ姫は救出前に死ぬと再登場する
        if self.with_princess:
            self.flags.remove(3)
            self.flags.remove(4)
        self.exit_x = 47
        self.exit_y = 47
        self.set_map("catsle1-1", 59, 12)
        self.recover_full()
        self.reserve("opening" if is_opening else "reset")

    # セーブ
    def save_data(self):
        pl = self.player
        data = {
            "map": Actor.cur_map.name,
            "x": pl.x,
            "y": pl.y,
            "name": self.name,
            "personality": Grade.personality,
            "lv": Grade.lv,
            "max_hp": self.max_hp,
            "hp": self.hp,
            "max_mp": self.max_mp,
            "mp": self.mp,
            "power": self.power,
            "speed": self.speed,
            "exp": Grade.exp,
            "gold": self.gold,
            "items": self.items,
            "equips": self.equips,
            "encount": self.encount,
            "support": self.support,
            "exit_x": self.exit_x,
            "exit_y": self.exit_y,
            "opened": self.opened,
            "flags": self.flags,
            "auto_settings": self.auto_settings,
            "logs": self.logs,
            "prev_code": self.prev_code,
            "updated": str(datetime.datetime.utcnow() + datetime.timedelta(hours=9)),
        }
        return Firebase.set(self.save_code, data)

    # ロード
    def load_data(self):
        data = Firebase.get(self.prev_code)
        if not data:
            return None
        pl = self.player
        pl.x = data["x"]
        pl.y = data["y"]
        self.name = data["name"]
        Grade(data["lv"], data["exp"], data["personality"])
        self.max_hp = data["max_hp"]
        self.hp = data["hp"]
        self.max_mp = data["max_mp"]
        self.mp = data["mp"]
        self.power = data["power"]
        self.speed = data["speed"]
        self.gold = data["gold"]
        self.items = data["items"] if "items" in data else []
        self.equips = data["equips"]
        self.encount = data["encount"]
        self.support = data["support"]
        self.exit_x = data["exit_x"]
        self.exit_y = data["exit_y"]
        self.opened = data["opened"] if "opened" in data else []
        self.flags = data["flags"] if "flags" in data else []
        self.auto_settings = data["auto_settings"]
        self.logs = data["logs"]
        self.logs["loaded"] += 1
        restart_map = data["map"]
        if 12 in self.flags:  # エンディング後再開
            self.flags.remove(12)
            pl.x = 47
            pl.y = 46
            restart_map = "field"
        while len(self.equips) < 4:
            self.equips.append(None)
        return restart_map

    ### ウィンドウ関連 ###

    # 会話ウィンドウオープン
    def talk(self, texts_in, head=False):
        texts_arr = [texts_in] if type(texts_in) is str else texts_in
        texts = self.replace_text(texts_arr)
        win = self.windows["talk"] if "talk" in self.windows else None
        if not win:
            win = self.open_talk()
        for text in texts:
            if win.is_battle:
                line = text.split("\n")
                if head:
                    self.next_talk(line)
                else:
                    win.texts.extend(line)
                    win.feed()
            else:
                win.push(text)
        return win

    # ウィンドウクローズ
    def close_win(self, target=None):
        if target is None:
            windows_copy = copy.deepcopy(self.windows)
            for key in windows_copy:
                del self.windows[key]
        else:
            targets = target if type(target) is list else [target]
            for key in targets:
                if key in self.windows:
                    del self.windows[key]

    # トークウィンドウのクローズ
    def close_talk(self):
        self.close_win("talk")
        for actor in Actor.actors:
            actor.is_talking = False

    # ウィンドウオープン＆上書き
    def upsert_win(self, target, x1, y1, x2, y2, texts=[]):
        if target in self.windows:
            if len(texts) > 0:
                self.windows[target].texts = texts
        else:
            self.windows[target] = Window(x1, y1, x2, y2, texts)
        return self.windows[target]

    # 会話内容切り替え
    def next_talk(self, texts_in, feed=False):
        win = self.open_talk()
        texts = texts_in.split("\n") if type(texts_in) is str else texts_in
        win.texts = self.replace_text(texts)
        if win.is_battle or feed:
            win.feed()

    # 会話ウィンドウ生成
    def open_talk(self):
        win = self.upsert_win("talk", 4, 9, 25, 14, [])
        win.is_talk = True
        win.is_battle = Battle.on
        return win

    # %を主人公の名前に置換
    def replace_text(self, texts_in):
        return [t.replace("%", self.name) for t in texts_in]

    ### マップ関連 ###

    # マップ移動
    def set_map(self, name, x, y, sound_id=None):
        Fade.start(True)
        self.next_map = name
        self.next_x = x
        self.next_y = y
        self.close_win()
        if not sound_id is None:  # 移動音（階段など）
            Sounds.sound(sound_id)

    # マップ切り替え
    def change_map(self):
        pl = self.player
        if (not Sounds.nocut and px.play_pos(3) is None) or px.play_pos(0) is None:
            if self.next_map:
                pl.x = self.next_x
                pl.y = self.next_y
                pl.reset_move()
                if not Actor.cur_map or Actor.cur_map.name != self.next_map:
                    before_kind = Actor.cur_map.kind if Actor.cur_map else 0
                    Actor.cur_map = Map(self.next_map)
                    self.map_bgm()
                    self.set_actors()
                    self.next_map = None
                    if Actor.cur_map.kind == 0:
                        self.support["RMR"] = 0
                        self.support["TORCHLIGHT"] = 0
                    elif Actor.cur_map.kind == 2 and before_kind != 2:
                        spell = gm.spell(const.RMR)
                        cnt = self.has_item(const.TORCHLIGHT)
                        if self.can_spell(const.RMR, True) and self.support["RMR"] == 0:
                            self.talk(
                                f"{spell['name']}の じゅもんを つかいますか？\nしょうひMP {spell['mp']}"
                            )
                            self.show_status()
                            self.reserve("yn", "spell_yn", const.RMR)
                        elif (
                            cnt > 0
                            and self.support["RMR"] == 0
                            and self.support["TORCHLIGHT"] == 0
                        ):
                            self.talk(
                                f"{gm.item(const.TORCHLIGHT)['name']}を つかいますか？\nのこり {cnt}こ"
                            )
                            self.reserve("yn", "item_yn", const.TORCHLIGHT)
            Fade.start()
            self.visible = True

    # Actorsを配置
    def set_actors(self):
        actors = []
        for value in Actor.cur_map.actors:
            actor = Actor(value)
            if not (
                actor.lock in self.opened
                or actor.door in self.opened
                or actor.flag in self.flags
            ):
                actors.append(actor)
        Actor.actors = [self.player] + actors

    # ジャンプ判定
    def check_jump(self):
        pl = self.player
        x = pl.x - Actor.cur_map.base_x
        y = pl.y - Actor.cur_map.base_y
        key = f"{Actor.cur_map.name},{x},{y}"
        if key in jumps:
            nmap = jumps[key]
            if not nmap is None:
                if Actor.cur_map.kind == 0:
                    self.exit_x = pl.x
                    self.exit_y = pl.y
                if type(nmap) is str:
                    self.set_map(nmap, self.exit_x, self.exit_y, 4)
                else:
                    ms = Map(nmap[0])
                    self.set_map(ms.name, nmap[1] + ms.base_x, nmap[2] + ms.base_y, 4)
                return True
        if Actor.cur_map.is_out(pl.x, pl.y):
            self.deport()
            return True

    # ルーラ・キメラのつばさ
    def jump_to_start(self):
        self.close_win()
        self.set_map("field", 47, 46, 8)

    # フィールドへ出る
    def deport(self):
        self.set_map("field", self.exit_x, self.exit_y, 4)

    # マップBGMを流す
    def map_bgm(self):
        Sounds.bgm(Actor.cur_map.music)

    ### じゅもん関連 ###

    # じゅもんウィンドウ
    def open_spells(self):
        texts = []
        cur_ids = []
        spell_key = "onBattle" if Battle.on else "onMap"
        for i, spell in enumerate(master["spells"]):
            if i <= Grade.learned_spell() and spell[spell_key]:
                texts.append(" " + spell["name"])
                cur_ids.append(i)
        if len(texts) > 0:
            self.open_spells_guide()
            win = self.upsert_win("spells", 20, 0, 27, 7, texts).add_cursol()
            win.cur_ids = cur_ids
        else:
            self.talk(f"%は まだ じゅもんを\nつかえない。")

    # じゅもんガイドオープン
    def open_spells_guide(self):
        adjust_y = 4 if Battle.on else 0
        self.upsert_win("spells_guide", 13, 7 + adjust_y, 28, 10 + adjust_y)

    # じゅもんガイド更新
    def update_spells_guide(self):
        win = self.windows["spells"]
        spell = gm.spell(win.cur_ids[win.cur_y])
        self.windows["spells_guide"].texts = [f"しょうひMP {spell['mp']}", spell["guide"]]
        return spell["id"]

    # じゅもん使用
    def use_spell(self, id):
        spell = gm.spell(id)
        self.close_win("spells_guide")
        Sounds.sound(7)
        self.next_talk(f"%は {spell['name']}の\nじゅもんを となえた！")
        Colors.set_flash(4)
        self.mp -= spell["mp"]
        self.show_status()
        if Battle.on:
            self.cmd_end(spell["symbol"])
        else:
            self.reserve("spell_field", id)

    # じゅもん使用可否判定
    def can_spell(self, id, skip_talk=False):
        if id > Grade.learned_spell() or self.is_sealed:
            return False
        if self.mp < gm.spell(id)["mp"]:
            if not skip_talk:
                self.next_talk("MPが たりない")
            return False
        kind = Actor.cur_map.kind
        failure = False
        if id == const.RMR and kind != 2:
            failure = True  # レミーラはダンジョン（ラスダン最新部除く）
        elif id == const.RRMT and kind in [0, 1]:
            failure = True  # リレミトはダンジョンのみ
        elif id == const.RR and kind in [2, 3]:
            failure = True  # ルーラはダンジョンでは使えない
        elif id == const.THRS and kind != 0:
            failure = True  # トヘロスはフィールドのみ
        if failure:
            if not skip_talk:
                self.next_talk("そのじゅもんは ここでは つかえない")
            return False
        if id in [const.HIM, const.BHIM] and self.is_full_hp():
            return False
        if (
            id == const.RMR
            and self.support["RMR"] // 32 >= (const.EFFECT_RMR - 1) // 32
        ):
            if not skip_talk:
                self.next_talk("まわりは じゅうぶんに あかるい！")
            return False
        return True

    ### どうぐ関連 ###

    # どうぐ所持個数取得
    def has_item(self, id):
        return len([i for i in self.items if i == id])

    # どうぐウィンドウ
    def open_items(self, is_abandon=False):
        if len(self.items) == 0:
            return self.talk("どうぐを なにも もっていない！")
        self.upsert_win("item_guide", 13, 9, 28, 12)
        texts = [f" {gm.item(i)['name']}" for i in self.items]
        win = self.upsert_win("items", 19, 0, 28, 9, texts).add_cursol()
        win.parm = is_abandon

    # どうぐガイド
    def guide_item(self, id):
        item = gm.item(id)
        if item["kind"] < 4:
            atc_old = util.padding(self.atc, 3)
            dfc_old = util.padding(self.dfc, 3)
            esc_id = self.equips[item["kind"]]
            self.equips[item["kind"]] = id
            atc_new = util.padding(self.atc, 3)
            dfc_new = util.padding(self.dfc, 3)
            self.equips[item["kind"]] = esc_id
            if item["kind"] == 0:
                texts = f"ぶき\nこうげきカ： {atc_old}→{atc_new}"
            elif item["kind"] == 3:
                texts = f"そうしょくひん\n{item['guide']}"
            else:
                kind = "よろい" if item["kind"] == 1 else "たて"
                texts = f"{kind}\n しゅびカ： {dfc_old}→{dfc_new}"
        else:
            texts = item["guide"]
        self.upsert_win("item_guide", 13, 7, 28, 10, texts.split("\n"))

    # どうぐ使用
    def use_item(self, id, idx=None):
        item = gm.item(id)
        header = "%は " + item["name"]
        consume = False
        if "items" in self.windows and self.windows["items"].parm:  # 捨てるモード
            return self.discard_item(id)
        notHere = f"ここでは {item['name']} は\nつかえない"
        no_effect = False
        # 武具
        if item["kind"] < 4:
            if Battle.on:
                no_effect = True
            else:
                pos = item["kind"]
                tmp = self.equips[pos]
                if not self.set_equip(pos, id):
                    return False
                if not self.is_curse():
                    self.talk(header + "を そうびした")
                if idx is not None:
                    self.change_item(tmp, idx)
        # ようせいのふえ
        elif id == const.FLUTE:
            if Battle.on:
                self.talk(header + "を ふいた")
                self.close_win("item_guide")
                Sounds.wait("dq1flute", "dq1battle")
                return self.reserve("flute")
            else:
                no_effect = True
        # おうじょのあい
        elif id == const.PRINCESS:
            texts = ["＊「おうじょのこえが きこえる。"]
            if not Grade.is_max_lv():
                texts.append(
                    f"ローラ「あなたが レベルをあげるには\n    あと {Grade.to_lvup()}ポイント\n    けいかんちが ひつようです。"
                )
            if Actor.cur_map.kind == 0:
                dist_x = self.player.x - 47
                dist_y = self.player.y - 47
                direction1 = f"ひがしに {-dist_x}" if dist_x < 0 else f"にしに {dist_x}"
                direction2 = f"みなみに {-dist_y}" if dist_y < 0 else f"きたに {dist_y}"
                texts.append(
                    f"ローラ「わたしのいる おしろは\n    {direction1} {direction2}\n    の ほうこう です。"
                )
            texts.append(f"ローラ「%さまを ローラは\n    おしたい もうしております。")
            self.talk(texts)
        # ぎんのたてごと
        elif id == const.HARP:
            if Battle.on or Actor.cur_map.kind == 1:
                no_effect = True
            else:
                self.talk(header + "を\nかきならした")
                self.close_win()
                Sounds.wait("dq1harp")
                self.reserve("harp")
        # あまぐものつえ
        elif id == const.RAIN_STAFF:
            if Battle.on:
                self.talk(header + "を\nふりかざした！")
                Battle.action = "MHTN"
            else:
                no_effect = True
        # やくそう
        elif id == const.HERB:
            if not self.is_full_hp():
                self.talk(header + "を つかった！")
                if Battle.on:
                    Battle.action = "HERB"
                else:
                    self.add_hp(gm.calc_cure("HERB"))
                consume = True
            # たいまつ
        elif id == const.TORCHLIGHT:
            if Battle.on:
                self.talk(header + "を なげつけた！")
                Battle.action = "TORCHLIGHT"
                consume = True
            elif Actor.cur_map.kind == 2:
                if (
                    self.support["TORCHLIGHT"] // 32
                    < (const.EFFECT_TORCHLIGHT - 1) // 32
                ):
                    self.talk(header + "に\nひをともした！")
                    self.support["TORCHLIGHT"] = const.EFFECT_TORCHLIGHT
                    consume = True
                else:
                    self.talk("まわりは じゅうぶんに あかるい")
            else:
                self.talk(notHere)
        # せいすい
        elif id == const.HOLYWATER:
            if Battle.on:
                self.talk(header + "を なげつけた！")
                Battle.action = "HOLYWATER"
                consume = True
            elif Actor.cur_map.kind == 0:
                self.talk(header + "を ふりまいた")
                self.support["HOLYWATER"] = const.EFFECT_HOLYWATER
                consume = True
            else:
                self.talk(notHere)
        # キメラのつばさ
        elif id == const.WING:
            if Battle.on:
                no_effect = True
            elif Actor.cur_map.kind in [2, 3]:
                self.talk(notHere)
            else:
                self.talk(header + "を\nそらたかく ほうりなげた")
                self.reserve("kimera")
                consume = True
        # にじのしずく
        elif id == const.RAINBOW_DROP:
            texts = [header + "を\nてんに かざした。"]
            if Actor.cur_map.kind == 0 and self.player.x == 69 and self.player.y == 53:
                self.reserve("rainbow")
            else:
                texts.append("しかし ここに にじは\nかからなかった。")
            self.talk(texts)
        # その他（かぎなど）
        else:
            no_effect = True
        if consume:
            self.consume_item(id, idx)
        # 戦闘中であればターンをまわす
        if Battle.on:
            self.next_talk(header + "を つかった！")
            self.cmd_end("none")
        elif no_effect:
            self.talk(header + "を つかった！\nしかし なにも おこらなかった")

    # どうぐ入れ替え
    def change_item(self, id, idx_in=None):
        items = self.items
        idx = len(items) if idx_in == None else idx_in
        if id is None:
            del items[idx]
        elif idx >= len(items):
            items.append(id)
            if len(items) > 8:
                garbage = items[0]
                for i in items:
                    price = gm.item(i)["price"]
                    if price > 0 and price < gm.item(garbage)["price"]:
                        garbage = i
                self.discard_item(garbage)
        else:
            items[idx] = id
        items.sort()
        # どうぐウィンドウ表示中＆捨てるモード以外なら書き換える
        if "items" in self.windows:
            win = self.windows["items"]
            if len(items) > 0 and not win.parm:
                win.cur_y = min(win.cur_y, len(items) - 1)
                self.open_items()
            else:
                self.close_win(["items", "item_guide"])

    # アイテムを捨てる
    def discard_item(self, id):
        item = gm.item(id)
        if item["price"] == 0:
            self.talk(f"{item['name']} は\nすてることが できない")
        else:
            self.talk(f"%は {item['name']}を\nなげすてた！")
            self.consume_item(id)
        return

    # アイテム消費
    def consume_item(self, id, idx=None):
        for i, _ in enumerate(self.equips):
            if self.equips[i] == id:
                self.equips[i] = None
        if idx is None:
            for i, item in enumerate(self.items):
                if item == id:
                    idx = i
                    break
            else:
                return
        self.change_item(None, idx)

    # アイテムを追加
    def add_item(self, id):
        if len(self.items) >= 8:
            self.talk("しかし もちものがいっぱいで\nこれいじょう もてない。\nもちものを すてますか？")
            self.reserve("yn", "abandon_yn")
            return False
        else:
            self.change_item(id)
            if id == const.FLUTE:  # ようせいのふえ
                self.flags.append(2)
            elif id == const.RT_MARK:  # ロトのしるし
                self.flags.append(6)
            elif id == const.RT_ARMOR:  # ロトのよろい
                self.flags.append(9)
            return True

    ### 装備関連 ###

    # 装備変更
    def set_equip(self, pos, id):
        if self.is_curse(pos):
            item = gm.item(self.equips[pos])
            self.talk(f"{item['name']} は のろわれているため\nはずすことが できない！")
            Sounds.wait("dq1curse")
            return False
        self.equips[pos] = id
        if self.is_curse(pos):
            item = gm.item(id)
            self.talk(f"{item['name']} には\nのろいが かかっていた！\n%は のろわれてしまった！")
            self.show_status()
            Sounds.wait("dq1curse")
        return True

    # 装備特殊効果の判定
    def equip_item(self, *args):
        return len([i for i in self.equips if i in list(args)]) > 0

    # のろい判定
    def is_curse(self, pos=None):
        for idx, id in enumerate(self.equips):
            if pos is None or idx == pos:
                if id in [const.DEATH_NECKLACE, const.CURSE_BELT]:
                    return True
        return False

    # のろいを解く
    def dispel_curse(self):
        dispeled = False
        for idx, _ in enumerate(self.equips):
            if self.is_curse(idx):
                self.equips[idx] = None
                dispeled = True
        self.show_status()
        return dispeled

    ### その他メニュー関連 ###

    # つよさウィンドウオープン
    def open_detail(self):
        texts = [
            " せいかく： " + master["personalities"][Grade.personality]["name"],
            "  ちから： " + util.padding(self.power, 3),
            " すばやさ： " + util.padding(self.speed, 3),
            "こうげきカ： " + util.padding(self.atc, 3),
            " しゅびカ： " + util.padding(self.dfc, 3),
            "   ぶき： " + gm.item(self.equips[0])["name"],
            "  よろい： " + gm.item(self.equips[1])["name"],
            "   たて： " + gm.item(self.equips[2])["name"],
            "そうしょく： " + gm.item(self.equips[3])["name"],
        ]
        self.upsert_win("detail_base", 13, 0, 28, 10, texts)
        texts = ["おぼえたじゅもん：", " ", " "]
        for i, spell in enumerate(master["spells"]):
            if i <= Grade.learned_spell():
                texts[1 + i // 5] += util.spacing(spell["name"], 5)
        self.upsert_win("detail_spells", 1, 10, 28, 14, texts)

    # さくせんを変更
    def change_auto_settings(self, idx, dist):
        setting = master["auto_settings"][idx]
        length = len(setting["options"])
        ats = self.auto_settings
        ats[setting["key"]] = (ats[setting["key"]] + dist + length) % length

    ### ショップ関連 ###

    # ショップウィンドウウープン（売買）
    def open_shop_buysell(self, kind, parm):
        win = self.upsert_win(
            "shop_buysell", 20, 5, 27, 8, [" かいにきた", " うりにきた"]
        ).add_cursol()
        win.kind = kind
        win.parm = parm

    # どうぐ購入
    def buy_item(self, id, with_sell):
        item = gm.item(id)
        idx = len(self.items)
        kind = self.windows["shop_items"].kind
        if idx >= 8 and not with_sell:
            if kind == "weapon":
                self.talk(f"＊「それいじょう もてないようだ")
            elif kind == "tool":
                self.talk(f"＊「それいじょう もてないようですよ")
            return
        if item["kind"] < 4:
            old_id = self.equips[item["kind"]]
            if not self.set_equip(item["kind"], id):
                return
            if not old_id is None:
                if with_sell:
                    self.gold += gm.item(old_id)["price"]
                else:
                    self.change_item(old_id, idx)
        else:
            self.change_item(id, idx)
        self.add_gold(-item["price"] * 2)
        if kind == "weapon":
            self.talk(f"＊「まいどあり。 ほかにも どうかね？")
        elif kind == "tool":
            self.talk(f"＊「まいど ありがとうございます。\n  ほかにも いかがですか？")

    # 売るもの一覧
    def open_shop_sell(self, kind, parm):
        texts = [
            f" {util.spacing(gm.item(i)['name'], 7)}{util.padding(gm.item(i)['price'], 5)}G"
            for i in self.items
        ]
        if "shop_sell" in self.windows:
            self.windows["shop_sell"].cur_y = max(
                self.windows["shop_sell"].cur_y - 1, 0
            )
        win = self.upsert_win("shop_sell", 13, 0, 28, 9, texts).add_cursol()
        win.kind = kind
        win.parm = parm

    # ほかにごようは？
    def shop_other(self, kind, parm, with_thank=False):
        self.close_win(["item_guide", "shop_items", "shop_sell"])
        if with_thank:
            if kind == "weapon":
                self.talk(f"＊「どうも ありがとう。\n  ほかに ようは あるかね？")
            elif kind == "tool":
                self.talk(f"＊「まいど ありがとうございます。\n  ほかに ごようは ありますか？")
        else:
            if kind == "weapon":
                self.talk("＊「ほかに ようは あるかね？")
            elif kind == "tool":
                self.talk("＊「ほかに ごようは ありますか？")
        self.open_shop_buysell(kind, parm)

    ### ステータス関連 ###

    # ステータスウィンドウ
    def show_status(self):
        health = ""
        if self.hp <= 0:
            health = "しに"
        elif self.is_sleeping:
            health = "ねる"
        elif self.is_sealed:
            health = "マホトン"
        elif self.is_curse():
            health = "のろい"
        texts = [
            f"{self.name} {health}",
            f"レベル {util.padding(Grade.lv, 2)}",
            f"H {util.padding(self.hp, 3)}/{util.padding(self.max_hp, 3)}",
            f"M {util.padding(self.mp, 3)}/{util.padding(self.max_mp, 3)}",
        ]
        self.upsert_win("status", 1, 0, 11, 5, texts)

    # プロパティ（お金と経験値）ウィンドウ
    def show_property(self):
        texts = [
            "G" + util.padding(self.gold, 6),
            "E" + util.padding(Grade.exp, 6),
        ]
        self.upsert_win("property", 2, 5, 10, 8, texts)

    # タイマー表示ウィンドウのクローズ
    def close_status(self):
        self.status_timer = 0
        self.close_win(["status", "property"])

    # フル回復
    def recover_full(self):
        self.hp = self.max_hp
        self.mp = self.max_mp
        self.cure_suggestion = False

    # HP回復
    def add_hp(self, value, skip_talk=False):
        self.hp = min(self.hp + value, self.max_hp)
        if not skip_talk:
            self.talk(self.name + "は キズが かいふくした！")
            self.show_status()

    # HP減少
    def decrease_hp(self, value, show=True):
        self.hp = max(self.hp - value, 0)
        if self.hp <= 0:
            self.logs["dead"] += 1
            if Battle.on:
                Battle.auto = False
            else:
                self.dead()
        if show:
            self.show_status()
        self.suggest_cure()

    # 自動回復
    def suggest_cure(self):
        if self.auto_settings["cure"] > 0:
            self.cure_suggestion = True

    # HPフル判定
    def is_full_hp(self):
        if self.hp >= self.max_hp:
            self.next_talk("HPが まんたんです")
            return True

    # 死んだ
    def dead(self):
        self.talk(self.name + "は しにました")
        self.reserve("dead")
        Sounds.wait("dq1dead")

    # レベルアップ判定
    def judge_lvup(self):
        Battle.state = 3 if Grade.to_lvup() <= 0 else 9

    # お金取得
    def add_gold(self, value):
        self.gold = min(self.gold + value, 65535)
        self.show_status()
        self.show_property()

    ### その他イベント ###

    # ウェルカム画面オープン
    def open_welcome(self):
        self.talk("ぴくせるばん ドラゴンクエスト1へ\nようこそ！\n")
        win = self.upsert_win("welcome", 4, 0, 11, 3, [" はじめから", "　つづきから"]).add_cursol()
        win.kind = []  # セーブコード入力用
        win.parm = []  # なまえ入力用
        Sounds.bgm("dq1town")

    # 名前ウィンドウオープン
    def open_name(self):
        texts = []
        for (idx, line) in enumerate(const.NAME_TEXTS):
            text = ""
            for letter in line:
                text += f" {letter}"
            if idx == 7:
                text += " もどる おわり"
            texts.append(text)
        self.upsert_win("name", 4, 0, 25, 9, texts).add_cursol(8, 10)

    # はいいいえウィンドウを開く
    def open_yn(self, kind, parm=None):
        win = self.upsert_win("yn", 20, 6, 25, 9, [" はい", " いいえ"]).add_cursol()
        win.kind = kind
        win.parm = parm

    # エンカウント値セット
    def set_encount(self):
        self.encount = px.rndi(32, 63)

    # エンカウント判定
    def do_encount(self, is_force=False):
        if not is_force and self.encount > 0:
            return
        self.set_encount()
        pl = self.player
        idx = None
        if Actor.cur_map.kind == 0:
            idx = master["encountmap"][pl.y // 16][pl.x // 16]
        else:
            idx = Actor.cur_map.encount
        if not idx is None:
            group = master["encountgroup"][idx]
            id = group[px.rndi(0, len(group) - 1)]
            en = master["enemies"][id]
            print("候補モンスター：")
            for tmp_id in group:
                print(master["enemies"][tmp_id]["name"])
            if (
                Actor.cur_map.kind == 0
                and (self.support["THRS"] or self.support["HOLYWATER"])
                and en["atc"] <= self.dfc
            ):
                return  # トヘロスとせいすいによる回避
            self.start_battle(id)

    # 毒ダメージ
    def poison(self, dmg, sound_id):
        if not self.equip_item(const.RT_ARMOR):
            Colors.poison = 2
            self.decrease_hp(dmg, False)
            Sounds.sound(sound_id)

    # 宝箱を開けた
    def open_treasure(self, target):
        Sounds.sound(17)
        self.opened.append(target.lock)
        remove_actor(target)

    # なにかを見つけた
    def message_find(self, text):
        self.talk(f"%は あしもとを しらべた\nなんと {text}を みつけた")

    # ローラがいっしょにいる？
    @property
    def with_princess(self):
        flags = self.flags
        return 12 in flags or (4 in flags and 5 in flags)

    ### バトル関連 ###

    # 攻撃力
    @property
    def atc(self):
        value = self.power
        for idx in self.equips:
            value += gm.item(idx)["atc"]
        return value

    # 守備力
    @property
    def dfc(self):
        value = self.speed // 2
        for idx in self.equips:
            value += gm.item(idx)["dfc"]
        return value

    # 戦闘開始
    def start_battle(self, id, is_boss=False):
        Battle.start(id, is_boss, self.auto_settings["default"] == 1)
        self.reserve("battle")
        return True

    # 戦闘ターン経過
    def battle_manage(self):
        en = Battle.enemy
        action = Battle.action
        if Battle.state == 1:
            if self.hp <= 0:  # 自分が死亡
                return self.dead()
            elif en["hp"] <= 0:  # 敵をたおした
                self.next_talk(f"{en['name']}を たおした！")
                px.stop()
                if en["id"] in [const.DRAGON_LOAD, const.DRAGON_KING]:
                    Sounds.next_music = None
                    Sounds.sound(16)
                else:
                    Sounds.sound(16, Actor.cur_map.music)
                Battle.state = 2
                return
            elif Battle.myturn:  # 自分のターン
                if action is None:
                    if Battle.auto:
                        return self.think_player()
                    else:
                        win = self.upsert_win(
                            "battle", 20, 0, 26, 5, [" たたかう", " じゅもん", " どうぐ", " にげる"]
                        )
                        win.add_cursol()
                        return
                elif action == "sleeping":
                    self.next_talk(f"%は ねむっている…")
                elif action == "escape":
                    if self.esc_rate > px.rndi(0, 31):
                        Battle.state = 9
                        self.logs["escape"] += 1
                        return self.battle_manage()
                    else:
                        self.talk("しかし てきに まわりこまれた！")
                elif action in ["HIM", "BHIM", "HERB"]:
                    self.add_hp(gm.calc_cure(action))
                elif action in ["RRH", "flute"]:
                    if self.calc_special(action):
                        self.talk(f"{en['name']}を ねむらせた！")
                        sleep_min = 3 if action == "flute" else 2
                        en["sleeping"] = px.rndi(sleep_min, sleep_min + 1)
                    else:
                        Battle.action = "fail"
                elif action == "MHTN":
                    if self.calc_special(action):
                        self.talk(f"{en['name']}の じゅもんを\nふうじこめた！")
                        en["sealed"] = True
                    else:
                        Battle.action = "fail"
                elif action == "none":
                    self.talk("しかし なにも おこらなかった！")
                else:
                    self.battle_dmg(action)
                if Battle.action == "fail":
                    self.talk(f"{en['name']}には きかなかった！")
                self.battle_enemyturn()
            else:  # 敵のターン
                if action is None:
                    return self.think_enemry()
                elif action == "sleeping":
                    self.next_talk(f"{en['name']}は ねむっている…")
                elif action == "escape":
                    en["hp"] = 0
                    Battle.state = 9
                    return self.battle_manage()
                elif action in ["HIM", "BHIM"]:
                    val = gm.calc_cure(action)
                    en["hp"] = min(en["hp"] + val, en["max_hp"])
                    self.talk(f"{en['name']}の キズが かいふくした！")
                    print(en["hp"], "/", en["max_hp"])
                elif action == "RRH":
                    if self.calc_special(action):
                        self.talk(f"%は ねむらされた！")
                        Battle.sleeping = px.rndi(2, 4)
                        self.show_status()
                    else:
                        Battle.action = "fail"
                elif action == "MHTN":
                    if self.calc_special(action):
                        self.talk(f"%は じゅもんを\nふうじこめられた！")
                        Battle.sealed = True
                        self.show_status()
                    else:
                        Battle.action = "fail"
                else:
                    self.battle_dmg(action)
                if Battle.action == "fail":
                    self.talk(f"%には きかなかった！")
                self.battle_myturn()
        elif Battle.state == 2:
            self.logs["win"] += 1
            if en["id"] == const.DRAGON_LOAD:  # りゅうおう連戦
                return self.start_battle(const.DRAGON_KING, True)
            elif en["id"] == const.DRAGON_KING:
                self.close_talk()
                self.recover_full()
                return self.reserve("finale")
            if en["exp"] > 0:
                self.talk(f"けいけんち {en['exp']}ポイントかくとく\n{en['gold']}ゴールドを てにいれた！")
                Grade.exp = min(Grade.exp + en["exp"], 65535)
                self.add_gold(en["gold"])
            self.judge_lvup()
        elif Battle.state == 3:
            Sounds.bgm("dq1lvup", False, Actor.cur_map.music)
            texts = f"%は レベルが あがった！\n"
            Grade.lv += 1
            self.next_talk(texts)
            self.show_status()
            self.suggest_cure()
            Battle.state = 4
        elif Battle.state == 4:
            texts = ""
            (h_up, m_up, p_up, s_up) = Grade.lvup_parms()
            if h_up > 0:
                self.max_hp += h_up
                texts += f"さいだいHPが {h_up} あがった！\n"
            if m_up > 0:
                self.max_mp += m_up
                texts += f"さいだいMPが {m_up} あがった！\n"
            if p_up > 0:
                self.power += p_up
                texts += f"ちからが {p_up} あがった！\n"
            if s_up > 0:
                self.speed += s_up
                texts += f"すばやさが {s_up} あがった！"
            self.next_talk(texts)
            self.show_status()
            if Grade.learned_spell() > Grade.learned_spell(-1):
                Battle.state = 5
            else:
                self.judge_lvup()
        elif Battle.state == 5:
            texts = f"{master['spells'][Grade.learned_spell()]['name']}の じゅもんを おぼえた！"
            self.next_talk(texts)
            self.judge_lvup()
        elif Battle.state == 9:
            self.close_win(["property", "talk", "auto"])
            if px.play_pos(3):
                px.stop()
            # イベントバトル後処理
            self.reserve("win", en["id"], Battle.is_boss, en["hp"] > 0)
            Battle.off()
            self.map_bgm()

    # 戦闘自ターン
    def battle_myturn(self):
        if self.hp <= 0:  # 死亡時
            return
        Battle.myturn = True
        if Battle.call_player():
            self.talk(f"%は めをさました")
            self.show_status()
        if Battle.action != "sleeping":
            self.battle_switch_auto()

    # オートモード切り替え
    def battle_switch_auto(self):
        if Battle.auto:
            self.close_win("battle")
            self.upsert_win("auto", 20, 0, 27, 2, ["オートバトル"])
        else:
            self.close_win("auto")
            # if Battle.myturn and not Battle.action:

    # 敵のターン
    def battle_enemyturn(self):
        en = Battle.enemy
        if en["hp"] > 0 and Battle.call_enemy():
            self.talk(f"{en['name']}は めをさました")

    # ダメージ処理
    def battle_dmg(self, action):
        en = Battle.enemy
        if action == "blow":
            (dmg, is_crt) = self.calc_blow()
        else:
            dmg = self.calc_spell(action)
            is_crt = False
        target = en["name"] if Battle.myturn else self.name
        if dmg > 0:
            if Battle.myturn:
                if is_crt:
                    self.talk("かいしんの いちげき！！")
                    Sounds.sound(13)
                else:
                    Sounds.sound(12)
                self.talk(f"{target}に {dmg}ポイントの\nダメージを あたえた！")
                Battle.enemy_blinking = 11
                en["hp"] -= dmg
            else:
                self.talk(f"{target}は {dmg}ポイントの\nダメージを うけた！")
                Sounds.sound(14)
                self.shaking = 7
                self.decrease_hp(dmg)
        else:
            if action:
                msg = "ダメージを うけない！" if dmg == 0 else "ひらりと みをかわした！"
                self.talk(f"ミス！ {target}は \n{msg}")
                Sounds.sound(15)
            else:
                self.talk(f"{target}には きかなかった！")

    # 自分の思考ルーチン（オートバトル）
    def think_player(self):
        en = Battle.enemy
        (blow_min, blow_max, blow_avg) = self.calc_blow(True, True)
        (gr_min, _, gr_avg) = self.calc_spell("GR", True)
        (bgrm_min, _, bgrm_avg) = self.calc_spell("BGRM", True)
        dmg_max = 0
        for action in en["actions"]:
            tmp = 0
            if action == "blow":
                (_, tmp, _) = self.calc_blow(True, False)
            elif action in ["GR", "BGRM", "fire1", "fire2"]:
                (_, tmp, _) = self.calc_spell(action, True, False)
            dmg_max = max(dmg_max, tmp)
        danger = dmg_max >= self.hp  # 一撃でやられる
        allow_spell = dmg_max > 1 and self.auto_settings["spell"] > 0
        allow_seal = (
            en["hp"] > blow_max * 2
            and not en["sealed"]
            and self.auto_settings["escape"] == 0
            and en["avoid_seal"] <= px.rndi(0, 15)
        )
        print("dmg_max", dmg_max, "danger", danger, "allow_spell", allow_spell)
        # rint("====== Auto  ======")
        # rint("自分の最小ダメージ", blow_min, gr_min, bgrm_min)
        # rint("敵のHP", en["hp"])
        # rint("敵の最大ダメージ", dmg_max)
        can_fairy = (not en["sleeping"]) and self.has_item(const.FLUTE)
        can_sleep = (
            (not en["sleeping"])
            and self.can_spell(const.RRH)
            and self.auto_settings["spell"] > 0
        )
        if blow_min >= en["hp"]:
            self.cmd_blow()
        elif self.esc_rate >= (48 - self.auto_settings["escape"] * 16):
            self.cmd_escape()  # にげる
        elif allow_spell and self.can_spell(const.GR) and gr_min >= en["hp"]:
            self.use_spell(const.GR)  # ギラ
        elif allow_spell and self.can_spell(const.BGRM) and bgrm_min >= en["hp"]:
            self.use_spell(const.BGRM)  # ベギラマ
        elif can_fairy and en["avoid_fairy"] == 0:
            self.use_item(const.FLUTE)  # ようせいのふえ1
        elif allow_spell and can_sleep and en["avoid_sleep"] == 0:
            self.use_spell(const.RRH)  # ラリホー1
        elif danger and self.can_spell(const.BHIM):
            self.use_spell(const.BHIM)  # ベホイミ
        elif danger and self.can_spell(const.HIM):
            self.use_spell(const.HIM)  # ホイミ
        elif danger and self.has_item(const.HERB):
            self.use_item(const.HERB)  # やくそう
        elif (
            allow_spell
            and can_sleep
            and en["hp"] > blow_min * 2
            and en["avoid_sleep"] <= px.rndi(0, 15)
        ):
            self.use_spell(const.RRH)  # ラリホー2
        elif allow_seal and self.has_item(const.RAIN_STAFF):
            self.use_item(const.RAIN_STAFF)  # あまぐものつえ
        elif allow_spell and allow_seal and self.can_spell(const.MHTN):
            self.use_spell(const.MHTN)  # マホトーン
        elif self.auto_settings["spell"] == 2 or (
            self.auto_settings["spell"] == 1 and blow_avg < 1
        ):
            if allow_spell and self.can_spell(const.GR) and gr_avg > blow_avg:
                self.use_spell(const.GR)  # ギラ
            elif allow_spell and self.can_spell(const.BGRM) and bgrm_avg > blow_avg:
                self.use_spell(const.BGRM)  # ベギラマ
            else:
                self.cmd_blow()
        else:
            self.cmd_blow()

    # 敵の思考ルーチン
    def think_enemry(self):
        en = Battle.enemy
        actions = en["actions"]
        selected = actions[px.rndi(0, len(actions) - 1)]
        health = en["hp"] / en["max_hp"]
        atc_ratio = self.atc / en["atc"]
        # rint("敵の行動選択肢：", actions)
        # rint("atc_ratio：", atc_ratio)
        if self.equip_item(const.DEATH_NECKLACE):
            atc_ratio = 0  # しのくびかざり効果
        action = "blow"
        if (
            selected in ["GR", "BGRM"]
            or (selected == "RRH" and not self.is_sleeping)
            or (selected == "MHTN" and not self.is_sealed)
            or (selected in ["HIM", "BHIM"] and health < 0.5)
        ):
            spell = gm.spell(selected)
            if en["mp"] >= spell["mp"] and not en["sealed"]:
                Sounds.sound(7)
                self.next_talk(f"{en['name']}は {spell['name']}の\nじゅもんを となえた！")
                en["mp"] -= spell["mp"]
                print("敵の残MP", en["mp"])
                action = selected
        elif selected in ["fire1", "fire2"]:  # ひのいき
            Sounds.sound(19)
            breath = "ひのいき" if selected == "fire1" else "ほのお"
            self.next_talk(f"{en['name']}は {breath}をはいた！")
            action = selected
        elif selected == "escape" and atc_ratio >= 2:  # にげる
            self.next_talk(f"{en['name']}は にげだした！")
            Sounds.sound(9)
            action = selected
        if action == "blow":
            self.next_talk(f"{en['name']}の こうげき！")
            Sounds.sound(11)
        print(f"選択された行動 / 実際の行動：{selected} / {action}")
        Battle.action = action

    # ダメージシミュレート（物理）
    def calc_blow(self, simulate=False, is_myturn=None):
        en = Battle.enemy
        myturn = Battle.myturn if is_myturn is None else is_myturn
        if myturn:
            atc = self.atc
            dfc = en["dfc"]
            avoid = en["avoid"]
            if en["sleeping"] > 0 or en["surprised"]:
                avoid = 0

            crt = Grade.crt_chance()
            if self.equip_item(const.FIGHTER_RING):
                crt += 1  # せんしのゆびわ効果
            if en["surprised"]:
                crt += 1  # 先制攻撃
            if en["disable_critical"]:  # 会心の一撃無効化（竜王様）
                crt = 0
        else:
            atc = Battle.enemy["atc"]
            dfc = self.dfc
            crt = 0
            avoid = 0 if self.is_sleeping else Grade.avoid_chance()
        dmg_base = max((atc - dfc / 2) / 2, 0)
        dmg_min = int(dmg_base * 3 / 4)
        dmg_max = int(dmg_base + 1)
        tmp_rnd = px.rndi(0, 31)
        print("会心率：", crt, "/32")
        print("回避率：", avoid, "/32")
        print("ダメージ最小 最大：", dmg_min, dmg_max)
        if simulate:
            dmg_avg = (dmg_min + dmg_max) * (32 - avoid) / 64
            dmg_min = 0 if avoid > 0 else dmg_min
            return (dmg_min, dmg_max, dmg_avg)
        else:
            is_crt = False
            if tmp_rnd < avoid:
                dmg = -1
            elif tmp_rnd >= 32 - crt and not simulate:  # かいしん
                dmg = px.rndi(int(atc * 3 / 4), atc)
                is_crt = True
            else:
                dmg = px.rndi(dmg_min, dmg_max)
            return (dmg, is_crt)

    # ダメージシミュレート（じゅもんなど）
    def calc_spell(self, kind, simulate=False, is_myturn=None):
        myturn = Battle.myturn if is_myturn is None else is_myturn
        if kind == "GR":
            if myturn:
                (dmg_min, dmg_max) = (16, 20)
            else:
                (dmg_min, dmg_max) = (6, 12)
        elif kind == "BGRM":
            if myturn:
                (dmg_min, dmg_max) = (50, 65)
            else:
                (dmg_min, dmg_max) = (30, 45)
        elif kind == "fire1":
            (dmg_min, dmg_max) = (12, 20)
        elif kind == "fire2":
            (dmg_min, dmg_max) = (65, 72)
        elif kind == "TORCHLIGHT":
            (dmg_min, dmg_max) = (4, 6)
        elif kind == "HOLYWATER":
            (dmg_min, dmg_max) = (16, 20)
        tmp_rnd = px.rndi(0, 31)
        reduciton_rate = 1.0
        if Battle.myturn:
            avoid = Battle.enemy["avoid_dmg"]
            if kind in ["TORCHLIGHT", "HOLYWATER"]:
                avoid = max(avoid - 16, 0)
        else:
            avoid = 0
            # まほうのよろいとロトのよろいの軽減
            if kind in ["GR", "BGRM"] and self.equip_item(
                const.MAGIC_ARMOR, const.RT_ARMOR
            ):
                reduciton_rate = 2 / 3
            elif kind in ["fire1", "fire2"] and self.equip_item(const.RT_ARMOR):
                reduciton_rate = 2 / 3
        dmg_min = int(dmg_min * reduciton_rate)
        dmg_max = int(dmg_max * reduciton_rate)
        if simulate:
            dmg_avg = (dmg_min + dmg_max) * (32 - avoid) / 64
            dmg_min = 0 if avoid > 0 else dmg_min
            return (dmg_min, dmg_max, dmg_avg)
        else:
            print("呪文回避率", avoid, "/32")
            dmg = 0 if tmp_rnd < avoid else px.rndi(dmg_min, dmg_max)
            return dmg

    # 成功判定（じゅもんなど）
    def calc_special(self, kind):
        en = Battle.enemy
        if Battle.myturn:
            if kind == "RRH":
                avoid = 32 if en["sleeping"] else en["avoid_sleep"]
            elif kind == "flute":
                avoid = 32 if en["sleeping"] else en["avoid_fairy"]
            elif kind == "MHTN":
                avoid = 32 if en["sealed"] else en["avoid_seal"]
        else:
            avoid = Grade.nullify_chance()
            if kind == "RRH" and (self.is_sleeping or self.equip_item(const.RT_MARK)):
                avoid = 32
            elif kind == "MHTN" and (
                self.is_sealed or self.equip_item(const.MAGIC_ARMOR)
            ):
                avoid = 32
        print("呪文回避率", avoid, "/32")
        return px.rndi(0, 31) >= avoid

    # たたかう
    def cmd_blow(self):
        self.next_talk("%の こうげき！")
        Sounds.sound(10)
        self.cmd_end("blow")

    # にげる
    def cmd_escape(self):
        self.next_talk("%は にげだした！")
        Sounds.sound(9)
        self.cmd_end("escape")

    # コマンド終了
    def cmd_end(self, action):
        if not Battle.action:
            Battle.action = action
        self.close_win(["battle", "spells", "items", "item_guide"])

    # 眠っているか
    @property
    def is_sleeping(self):
        return Battle.on and Battle.sleeping > 0

    # マホトーン状態か
    @property
    def is_sealed(self):
        return Battle.on and Battle.sealed

    # 逃走成功率
    @property
    def esc_rate(self):
        en = Battle.enemy
        esc_rate = min(int(self.speed / en["speed"] * 8) + 16, 32)
        if en["sleeping"] or en["surprised"]:
            esc_rate = 32
        if en["disable_critical"]:
            esc_rate = 0  # りゅうおうからは逃げられない
        print("逃走成功率", esc_rate, "/32")
        return esc_rate


App()
