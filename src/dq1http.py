LOCAL = False
try:
    from pyodide.http import open_url
except:
    LOCAL = True
    print("ローカルモード")
import json
import dq1util as util

base = "https://us-central1-pyxel-dq1.cloudfunctions.net/"


class Http:
    # 書き込み
    def set(save_code, pwd, data):
        if LOCAL:
            with open("../local/dq1save.json", "w") as fout:
                fout.write(json.dumps(data))
                return ["＊＊＊＊＊＊", "00000000"]
        else:
            try:
                url = f"{base}save?id={save_code}&pwd={pwd}&data={json.dumps(data)}"
                res = open_url(url).read()
                return res.split(",")
            except:
                return None

    # 読み込み
    def get(save_code):
        if LOCAL:
            return util.load_json("../local/dq1save")
        else:
            try:
                url = f"{base}load?id={save_code}"
                return json.loads(open_url(url).read())
            except:
                return None
