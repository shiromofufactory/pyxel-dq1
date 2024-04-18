pyxel package ./src ./src/dq1.py
pyxel app2html src.pyxapp
rm -rf public/*
mv src.html public/index.html
cp favicon.ico public/
cp src/*.json public/
cp -r src/musics public/
mv -f src.pyxapp dq1pyxel.pyxapp
cd public
python3 -m http.server 8000