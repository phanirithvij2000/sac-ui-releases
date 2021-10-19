### sac-ui-releases

### Setup

First `Use as template`

Linux

```sh
cd scripts
python3 -m venv venv
source ./venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt

# OR one line
python3 -m venv venv && source ./venv/bin/activate && python -m pip install -U pip && python -m pip install -r requirements.txt
```

Windows

```powershell
cd scripts
python3 -m venv venv
.\venv\Scripts\activate.bat
python -m pip install -U pip
python -m pip install -r requirements-win.txt

# OR one line
python3 -m venv venv && .\venv\Scripts\activate.bat && python -m pip install -U pip && python -m pip install -r requirements-win.txt
```

#### Template configuration (REQUIRED):

Look at `config/` folder and change all of them.

Then use

```sh
cd #root
# this must be run from root so config/ can be read
python scripts/project_replace.py -h # -r -v -i
```

This will replace all the project variables with values from the `config/` files.

### Setup actions secrets (REQUIRED)

```sh
cd #root
mv config/secrets.env .env
# Enter github actions secrets
# Publish secrets to repo
cd scripts
source ./venv/bin/activate
# on windows
# .\venv\Scripts\activate.bat
python setup_actions_secrets.py
```

Push your local changes

```sh
git add .
git commit -m "configure project [skip ci]"
# or amend (dangerous)
# git commit --amend --no-edit
```

### How to release

TODO
