LOCAL = False
try:
    from js import window
except:
    LOCAL = True
    print("ローカルモード")
import json
import dq1util as util


class User:
    # 書き込み
    def save(data):
        try:
            if LOCAL:
                with open("../local/dq1save.json", "w") as fout:
                    fout.write(json.dumps(data))
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
                return util.load_json("../local/dq1save")
            else:
                return json.loads(window.localStorage.getItem("pyxel-dq1"))
        except:
            print("Load Failed.")
            return None

    # リセット（webのみ）
    def reset():
        if not LOCAL:
            window.location.reload()
