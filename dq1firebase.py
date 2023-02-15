import urllib.request
import json

# import dq1util as util

url = "https://us-central1-pyxel-dq1.cloudfunctions.net/api"


class Firebase:
    # 書き込み
    def set(save_code, save_data):
        # with open("./dq1save.json", "w") as fout:
        #    fout.write(json.dumps(data))
        #    return "******"
        data = {"id": save_code, "data": save_data}
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, json.dumps(data).encode(), headers)
        with urllib.request.urlopen(req) as res:
            return res.read().decode("utf-8")

    # 読み込み
    def get(save_code):
        # return util.load_json("dq1save")
        req = urllib.request.Request(f"{url}?id={save_code}")
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
