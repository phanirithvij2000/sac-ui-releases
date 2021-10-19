# Use this script to deploy to some repo
# todo install hub, poetry etc yourself
set -x

rm -rf .git
rm -rf "$LOCALAPPDATA\pypoetry\Cache"
rm -rf server/venv

hub init
hub create -p
hub add . && hub commit -m "inital commit [skip ci]"

cd server

# On windows it is py.exe
# On linux use python3 normally

echo using python $(py -V) $(where py)
py -m venv venv
set +x
echo "++ source ./venv/Scripts/activate"
source ./venv/Scripts/activate
set -x
where python
python -mpip install -U pip wheel
poetry install -v
python ../scripts/setup_actions_secrets.py

hub push -u origin main
