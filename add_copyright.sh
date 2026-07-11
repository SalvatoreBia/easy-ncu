#!/bin/bash

YEAR="2026"
AUTHOR="Salvatore Biamonte"
PROJECT_NAME="easy-ncu"
DESCRIPTION="A smart CLI tool for NVIDIA Nsight Compute report analysis."

read -r -d '' COPYRIGHT_TEXT << EOM
# $PROJECT_NAME - $DESCRIPTION
# Copyright (C) $YEAR  $AUTHOR
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

EOM

echo "Starting copyright header injection (GPLv3)..."
echo "----------------------------------------------------------------"

find . -maxdepth 1 -type f -name "*.py" | while read -r file; do
    
    if [ ! -s "$file" ]; then
        continue
    fi

    if head -n 5 "$file" | grep -iq "copyright"; then
        echo "[SKIPPED] $file already contains a copyright header."
    else
        echo "[ADDED] Injecting copyright header into: $file"
        
        echo "$COPYRIGHT_TEXT" > "$file.tmp"
        cat "$file" >> "$file.tmp"
        mv "$file.tmp" "$file"
    fi
done

echo "----------------------------------------------------------------"
echo "Operation completed successfully!"