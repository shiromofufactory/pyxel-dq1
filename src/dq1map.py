import dq1util as util

map_settings = util.load_json("dq1maps")


class Map:
    def __init__(self, name):
        for ms in map_settings:
            if ms["name"] == name:
                self.name = ms["name"]
                self.kind = ms["kind"]
                self.map_no = ms["map_no"]
                self.base_x = ms["base_x"]
                self.base_y = ms["base_y"]
                self.size = ms["size"] if "size" in ms else None
                self.music = ms["music"]
                self.actors = ms["actors"] if "actors" in ms else []
                self.encount = ms["encount"] if "encount" in ms else None
                break
        else:
            print("マップ読み込みエラー", name)

    # マップ外に出たか
    def is_out(self, abs_x, abs_y):
        if not self.size:
            return False
        x = abs_x - self.base_x
        y = abs_y - self.base_y
        return x < 0 or y < 0 or x >= self.size or y >= self.size
