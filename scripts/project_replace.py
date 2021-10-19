"""\
Usage:
    (-i, --info, -info)\t\tto print project template information, Detect and tell user these need to be filled
    (-r, --replace, -replace)\tReplace them from user provided values across the whole project
    ('-v', '-verbose', '--verbose')\tEnable verbose output
Goes through the whole project
All file_names, folder_names, files, folders except the ones mentioned in .gitignore\
"""

import json
import os
import re
import subprocess
import sys
from re import Pattern
from typing import Iterable

import magic
from dotenv import dotenv_values
from dotenv.main import find_dotenv

DEF_REG = re.compile(
    r"(\$\{[\s]*PROJECT[_\-][\da-zA-Z_\-]*[\s]*\})|(\$\{[\s]*GITHUB[_\-][\da-zA-Z_\-]*[\s]*\})")


def git_ls_files():
    """runs `git ls-files` gets all tracked files (so builtin .gitignore support)"""
    PIPE = subprocess.PIPE

    # git ls-files to get all tracked files
    process = subprocess.Popen(['git', 'ls-files'], stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if stderroutput != b'':
        print(stderroutput)
        exit(1)
    return stdoutput.decode('utf-8').splitlines()


def find_template_vars(
    git_files=[],
    desired_reg: Pattern = DEF_REG,
    skip_exts=[".env"],
):
    """
    Loop over given files and find any paths, or instances of template params
    which match the given regex pattern.
    `skip_exts` means these files will not be opened and read
    but their names will be changed if it contains given regex
    examples:
        `${PROJECT_*} or ${GITHUB_*}`
    """

    matches_ = {}
    # files need not be a set, can be a list
    rep_paths_ = set()
    vars_set = set()
    for file_name in git_files:
        # ignore current file
        if os.path.samefile(file_name, sys.argv[0]):
            continue
        if desired_reg.search(file_name):
            rep_paths_.add(file_name)
            for m in desired_reg.finditer(file_name):
                # m.string for the matched string
                if m.lastindex not in matches_:
                    matches_[m.lastindex] = {}
                for g in m.groups():
                    if g is not None:
                        vars_set.add(g)
                        if g not in matches_[m.lastindex]:
                            matches_[m.lastindex][g] = set()
                        matches_[m.lastindex][g].add(file_name)
        if os.path.splitext(file_name)[1] in skip_exts:
            # don't read .env file contents but filename changes allowed
            continue
        # only read text files, ignore binary, images etc.
        if magic.from_file(file_name, mime=True).startswith("text/"):
            with open(file_name, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    for m in desired_reg.finditer(line):
                        if m.lastindex not in matches_:
                            matches_[m.lastindex] = {}
                        for g in m.groups():
                            if g is not None:
                                vars_set.add(g)
                                if g not in matches_[m.lastindex]:
                                    matches_[m.lastindex][g] = set()
                                matches_[m.lastindex][g].add(file_name)
    return {
        'matches': matches_,
        'paths': rep_paths_,
        'vars_set': vars_set,
    }


def strip_env_syntax(string: str):
    """${x} -> x"""
    return re.compile(r'[\$\{\}]').sub('', string).strip()


def load_vars(configs: Iterable = []):
    """
    Load variables from `configs`,
    each assumed to be a dot env file as of now
    """
    conf = {}
    for c in configs:
        conf.update(dotenv_values(find_dotenv(c)))
    return conf


def replace_project_vars(verbose=False):
    files = git_ls_files()
    templ_vars = find_template_vars(files, DEF_REG)
    envs = []
    for fpath in files:
        if fpath.endswith(".env") and 'secret' not in fpath:
            envs.append(fpath)
    print("\nUsing config files")
    print('\t|__ ' + "\n\t|__ ".join(envs), '\n')
    provided_vars = load_vars(envs)
    # print(json.dumps(provided_vars, indent=2))
    need = set([strip_env_syntax(x) for x in templ_vars['vars_set']])
    got_ = set(provided_vars.keys())

    missing = need - got_
    if len(missing) > 0:
        print("Required but missing:")
        print('\t|__ ' + "\n\t|__ ".join(missing))
        print("Not replacing as some are missing and this might make your project unusable")
        exit(1)

    # start replace
    with open('scripts/.vars.txt', 'w+', encoding='utf-8') as f:
        for k, v in provided_vars.items():
            print("${"+k+"}", "==>", v, sep='', file=f)
            if verbose:
                print("${"+k+"}", "==>", v, sep='')

    with open('scripts/.paths.txt', 'w+', encoding='utf-8') as f:
        for file_name in templ_vars['paths']:
            rep_name = file_name
            for var in got_:
                if var in file_name:
                    rep_name = (
                        rep_name
                        .replace(
                            "${"+var+"}",
                            provided_vars[var]
                        )
                    )
            print(file_name, "==>", rep_name, sep='', file=f)
            if verbose:
                print(file_name, "==>", rep_name, sep='')

    # get confirmation
    yes = input("Sure you want to replace?")
    if yes.startswith("y"):
        git_filter_repo(verbose=verbose)


def git_filter_repo(
    vars_path="scripts/.vars.txt",
    paths_path="scripts/.paths.txt",
    verbose=False,
):
    """runs `git filter-repo` with given files"""
    PIPE = subprocess.PIPE

    # git ls-files to get all tracked files
    cmd = f"git filter-repo --replace-text {vars_path} --paths-from-file {paths_path} --force"
    if verbose:
        print("Running command:")
        print(cmd)
    process = subprocess.Popen(cmd.split(' '), stdout=PIPE, stderr=PIPE)
    stdoutput, stderroutput = process.communicate()
    if stderroutput != b'':
        print(stderroutput.decode('utf-8'))
        exit(1)
    if verbose:
        print(stdoutput.decode('utf-8'))


# python -m pip install git-filter-repo
# scoop install git-filter-repo
# generate the vars.txt and paths.txt files
# remove dry run
# git filter-repo --replace-text scripts\vars.txt --paths-from-file scripts\paths.txt --dry-run
# push to repo

class SetEncoder(json.JSONEncoder):
    """JSON decoder allows set serialization"""
    # https://stackoverflow.com/a/8230505/8608146

    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def project_report(verbose=False):
    files = git_ls_files()
    templ_vars = find_template_vars(files, DEF_REG)
    if verbose:
        print(json.dumps(templ_vars, indent=2, cls=SetEncoder))
    envs = []
    for fpath in files:
        if fpath.endswith(".env") and 'secret' not in fpath:
            envs.append(fpath)
    print("\nUsing config files")
    print('\t|__ ' + "\n\t|__ ".join(envs), '\n')
    provided_vars = load_vars(envs)
    if verbose:
        print(json.dumps(provided_vars, indent=2))
    need = set([strip_env_syntax(x) for x in templ_vars['vars_set']])
    got_ = set(provided_vars.keys())

    missing = need - got_
    if len(missing) > 0:
        print("Required but missing:")
        print('\t|__ ' + "\n\t|__ ".join(missing))
    else:
        print("No missing vars")
    print()
    extras = got_ - need
    if len(extras) > 0:
        print("Extras found (not using as template params)")
        print('\t|__ ' + "\n\t|__ ".join(extras))
    else:
        print("No extra vars")


def main():
    no_usage = False
    verbose = False
    if len({'-h', 'help', '-help', '--help'} & set(sys.argv)) > 0:
        print(__doc__)
        return
    if len({'-v', '-verbose', '--verbose'} & set(sys.argv)) > 0:
        verbose = True
    if len({'-i', '-info', '--info'} & set(sys.argv)) > 0:
        project_report(verbose)
        no_usage = True
    if len({'-r', '-replace', '--replace'} & set(sys.argv)) > 0:
        replace_project_vars(verbose)
        no_usage = True
    if not no_usage:
        print(__doc__)


if __name__ == "__main__":
    main()
