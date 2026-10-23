#!/usr/bin/env bash
#
# Bumps the version, commits pyproject.toml and uv.lock, tags vX.Y.Z, and
# pushes; the tag triggers .github/workflows/release.yml. Run through make:
#
#   make patch|minor|major   start a release candidate: 0.4.0 -> 0.4.1rc1,
#                            0.5.0rc1, or 1.0.0rc1. On a candidate, only a
#                            higher level is allowed (0.5.1rc1 -> 0.6.0rc1).
#   make rc                  the next candidate: 0.5.0rc1 -> 0.5.0rc2
#   make release             release the candidate: 0.5.0rc2 -> 0.5.0
#
# Every step needs docs/changelog/<X.Y.Z>-changelog.md for the release it
# leads up to; candidates use it as their release notes too.

set -euo pipefail

die() {
    echo "$*" >&2
    exit 1
}

# The release a version leads up to: 0.5.0rc1 -> 0.5.0, 0.5.0 -> 0.5.0.
base_version() {
    sed -E 's/(a|b|rc)[0-9]+$//' <<<"$1"
}

# Which kind of release X.Y.Z is: 0.5.1 patch, 0.6.0 minor, 1.0.0 major.
level_of() {
    local minor patch
    IFS=. read -r _ minor patch <<<"$1"
    if [ "$patch" != 0 ]; then
        echo patch
    elif [ "$minor" != 0 ]; then
        echo minor
    else
        echo major
    fi
}

rank() {
    case $1 in
    patch) echo 1 ;;
    minor) echo 2 ;;
    major) echo 3 ;;
    esac
}

action=${1:-}
[ -z "$(git status --porcelain)" ] ||
    die "Working tree is not clean; commit or stash changes first."

old=$(uv version --short)
base=$(base_version "$old")
candidate=$([ "$base" != "$old" ] && echo true || echo false)

case $action in
patch | minor | major)
    if $candidate; then
        level=$(level_of "$base")
        [ "$(rank "$action")" -gt "$(rank "$level")" ] ||
            die "$old is a release candidate for $level release $base;" \
                "make $action can only move a candidate up a level." \
                "Run 'make rc' for another candidate, or 'make release' to release it."
    fi
    args=(--bump "$action" --bump rc)
    ;;
rc)
    $candidate ||
        die "$old is not a release candidate; start one with" \
            "'make patch', 'make minor', or 'make major'."
    args=(--bump rc)
    ;;
release)
    $candidate ||
        die "$old is not a release candidate, so there is nothing to release." \
            "Start one with 'make patch', 'make minor', or 'make major', test it," \
            "then run 'make release'."
    args=(--bump stable)
    ;;
*)
    die "Usage: $0 patch|minor|major|rc|release"
    ;;
esac

new=$(uv version "${args[@]}" --dry-run --short)
notes="docs/changelog/$(base_version "$new")-changelog.md"
[ -f "$notes" ] || die "Missing $notes (the release notes)."

echo "Releasing $new (was $old)"
uv version "${args[@]}"
git add pyproject.toml uv.lock
git commit -m "Bump version: $old → $new"
git tag "v$new"
git push
git push origin "v$new"
