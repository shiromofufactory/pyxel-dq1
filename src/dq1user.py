LOCAL = False
try:
    from js import window
except:
    import os

    LOCAL = True
    local_path = os.path.expanduser("~/.config/.pyxel/pyxel-dq1")
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    print("ローカルモード")
import json
import dq1util as util


class User:
    # 書き込み
    def save(data):
        try:
            if LOCAL:
                util.save_json("save", json.dumps(data), local_path)
            else:
                window.localStorage.setItem(
                    "pyxel-dq1", json.dumps(data).replace(" ", "")
                )

        except:
            print("Save Failed.")
            return None

    # 読み込み
    def load():
        try:
            if LOCAL:
                return util.load_json("save", local_path)
            else:
                return json.loads(window.localStorage.getItem("pyxel-dq1"))
        except:
            print("Load Failed.")
            return None

    # リセット（webのみ）
    def reset():
        if not LOCAL:
            window.location.reload()
