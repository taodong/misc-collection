#!/usr/bin/env bash
#
# cpprf - copy all non-directory, non-hidden files from a source folder to a
#         destination folder, adding a given prefix to each copied file's name.
#
# Usage: cpprf <source> <dest> <prefix>

set -euo pipefail

usage() {
    echo "Usage: cpprf <source> <dest> <prefix>" >&2
    echo "  source: an existing folder (may be '.')" >&2
    echo "  dest:   destination folder (created if it does not exist)" >&2
    echo "  prefix: string to prepend to each file name" >&2
    exit 1
}

# --- Validate argument count -------------------------------------------------
# All three parameters are required.
if [ "$#" -ne 3 ]; then
    echo "Error: exactly 3 arguments are required, got $#." >&2
    usage
fi

src="$1"
dest="$2"
prefix="$3"

# --- Validate source ---------------------------------------------------------
if [ ! -d "$src" ]; then
    echo "Error: source '$src' is not an existing directory." >&2
    exit 1
fi

# --- Validate prefix ---------------------------------------------------------
if [ -z "$prefix" ]; then
    echo "Error: prefix must be a non-empty string." >&2
    exit 1
fi

# A prefix that contains a path separator would create files in another folder.
case "$prefix" in
    */*) echo "Error: prefix must not contain '/'." >&2; exit 1 ;;
esac

# --- Create destination if needed --------------------------------------------
mkdir -p "$dest"

# --- Resolve absolute paths so same-folder detection is reliable -------------
# (Handles '.', trailing slashes, relative paths, etc.)
src_abs="$(cd "$src" && pwd)"
dest_abs="$(cd "$dest" && pwd)"

same_folder=0
if [ "$src_abs" = "$dest_abs" ]; then
    same_folder=1
fi

# --- Copy files --------------------------------------------------------------
copied=0
shopt -s nullglob   # empty glob expands to nothing instead of a literal '*'
shopt -u dotglob    # ensure the '*' glob does NOT match hidden (dot) files

for path in "$src_abs"/*; do
    # Skip anything that is not a regular file: this excludes directories,
    # symlinks to directories, sockets, fifos, etc.
    [ -f "$path" ] || continue

    base="$(basename "$path")"

    # Skip hidden files (those whose name starts with a dot). The glob above
    # already won't match them, but this guards against edge cases.
    case "$base" in
        .*) continue ;;
    esac

    target="$dest_abs/$prefix$base"

    # When copying into the same folder, skip files that are already prefixed
    # so repeated runs don't keep stacking the prefix.
    if [ "$same_folder" -eq 1 ]; then
        case "$base" in
            "$prefix"*)
                echo "Skipping already-prefixed file: $base" >&2
                continue
                ;;
        esac
    fi

    cp -p -- "$path" "$target"
    echo "Copied: $base -> $prefix$base"
    copied=$((copied + 1))
done

echo "Done. $copied file(s) copied to '$dest_abs'."