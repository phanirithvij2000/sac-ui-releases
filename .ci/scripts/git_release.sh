set -x

event_name=$1
release_tag_name=$2
commit_message=$3
manual_version_name=$4
prerelease_suffix=$5

which yq
which jq

# Set git credentials
git config user.name github-actions[bot]
git config user.email github-actions[bot]@users.noreply.github.com

# Determine version based on the workflow event
version=""
if [ "$event_name" = "release" ]; then
    version=$release_tag_name
elif [ "$event_name" = "push" ]; then
    version=$(echo $commit_message | cut -d']' -f2 | sed 's/^[[:space:]]*//' | cut -d' ' -f1)
else
    if [ "$prerelease_suffix" = "" ]; then
        version="v$manual_version_name"
    else
        version="v$manual_version_name-$prerelease_suffix"
    fi
fi

# jq inplace replacement
function jq_i {
    tmp=$(mktemp)
    jq "$@" > "$tmp"
    mv "$tmp" "${@:$#}"
}

jq_i --arg v "$version" '.version = $v' package.json
jq_i --arg v "$version" '.version = $v' release/app/package.json
jq_i --arg v "$version" '.packages."".version = $v' release/app/package-lock.json | jq --arg v "$version" '.version = $v'

version_num=$(echo $version | cut -d'-' -f1 | cut -d'v' -f2-)

if [[ "$version" == *"-"* ]]; then
    prerelease_suffix=$(echo $version | cut -d'-' -f2-)
else
    prerelease_suffix=""
fi

# Modify default value to version in workflow
# requires a Personal access token with workflow scope
yq e "
(.on.workflow_dispatch.inputs.versionName.default = \"$version_num\") |
(.on.workflow_dispatch.inputs.versionName.description = \"Default values show the last released version\nName of version (ie $version_num) without v prefix\") |
(.on.workflow_dispatch.inputs.preReleaseSuffix.default = \"$prerelease_suffix\") |
(.on.workflow_dispatch.inputs.preReleaseSuffix.description = \"Pre Release suffix, appends -$prerelease_suffix to tag (alpha, beta, dev etc.)\")" \
-i ../.github/workflows/publish.yml

# commit version change
git add .
git commit -am "[auto-bump] $version"
git push -u origin releases/$version --force
git status

# if event is workflow_dispatch or release commit
# TODO if release repo is different from the current repo
# then we need to tag
if [ "$event_name" != "release" ]; then
    git tag $version
fi

# push tags
# FIXME might need to remove --force
git push --tags --force
set +x
