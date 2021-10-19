import os
from base64 import b64encode

import requests
from dotenv import dotenv_values, find_dotenv
from nacl import encoding, public


def encrypt(public_key: str, secret_value: str) -> str:
    """Encrypt a Unicode string using the public key."""
    # https://docs.github.com/en/rest/reference/actions#example-encrypting-a-secret-using-python
    public_key = public.PublicKey(
        public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")


headers = {'Accept': 'application/vnd.github.v3+json'}
S = requests.Session()
p_key = p_key_id = None


def get_repo_public_key():
    print("Fetch repo public key...")
    # https://docs.github.com/en/rest/reference/actions#get-a-repository-public-key
    r = S.get(
        "https://api.github.com/repos/{}/actions/secrets/public-key".format(
            os.environ['GITHUB_REPO']),
        headers=headers
    )
    if r.status_code != 200:
        print("Failed to get public key")
        print(r.status_code, r.text)
        exit(1)
    return r.json()['key_id'], r.json()['key']


def create_secret(key: str, value: str):
    global p_key, p_key_id
    if p_key is None or p_key_id is None:
        p_key_id, p_key = get_repo_public_key()
    if key.startswith("GITHUB_"):
        # Not allowed
        return

    value = encrypt(p_key, value)
    data = {"encrypted_value": value, "key_id": p_key_id}
    print("Creating secret", key)
    # https://docs.github.com/en/rest/reference/actions#create-or-update-a-repository-secret--code-samples
    r = S.put(
        'https://api.github.com/repos/{}/actions/secrets/{}'.format(
            os.environ['GITHUB_REPO'],
            key,
        ),
        headers=headers,
        json=data
    )
    if not str(r.status_code).startswith("20"):
        print(r.status_code, "Not a 200s status")
        print(r.text)
        exit(1)


if __name__ == "__main__":
    env_vars = dotenv_values(find_dotenv())
    if env_vars is None or env_vars == {}:
        print("No dotenv found or is empty")
        exit(1)
    pat = env_vars.get("PAT")
    if pat is None or pat == "":
        print("No Personal access key found or is empty")
        exit(1)

    headers['Authorization'] = 'token {}'.format(pat)

    for k, v in env_vars.items():
        os.environ[k] = v

    for k, v in env_vars.items():
        create_secret(k, v)
