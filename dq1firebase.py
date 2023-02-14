import pyxel as px
import firebase_admin
from firebase_admin import db, credentials
import json
import dq1util as util

try:
    cred = credentials.Certificate("./serviceAccount.json")
except FileNotFoundError:
    cred = credentials.Certificate()
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "https://pyxel-dq1-default-rtdb.firebaseio.com/",
        "databaseAuthVariableOverride": {"uid": "my-service-worker"},
    },
)


class Firebase:
    # 書き込み
    def set(save_code, data):
        with open("./dq1save.json", "w") as fout:
            fout.write(json.dumps(data))
        if save_code is None:
            keys = db.reference().get(shallow=True)
            while True:
                save_code = f"{util.padding(px.rndi(0,999999),6,'0')}"
                if not save_code in keys:
                    break
        db.reference(save_code).set(data)
        return save_code

    # 読み込み
    def get(save_code):
        # try:
        #    data = util.load_json("dq1save")
        # except FileNotFoundError:
        #    return False
        return db.reference(save_code).get()
