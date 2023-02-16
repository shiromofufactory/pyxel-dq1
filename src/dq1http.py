try:
    from pyodide.http import open_url
except:
    print("ローカルモード")
import json
import dq1util as util

base = "https://us-central1-pyxel-dq1.cloudfunctions.net/"


class Http:
    # 書き込み
    def set(save_code, data):
        try:
            url = f"{base}save?id={save_code}&data={json.dumps(data).encode()}"
            return open_url(url).read().decode("utf-8")
        except:
            with open("./dq1save.json", "w") as fout:
                fout.write(json.dumps(data))
                return "＊＊＊＊＊＊"

    # 読み込み
    def get(save_code):
        try:
            url = f"{base}load?id={save_code}"
            return json.loads(open_url(url))
        except:
            return util.load_json("dq1save")
