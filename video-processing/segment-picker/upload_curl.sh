#!/bin/bash
# Upload remaining looped clips to Vimeo using curl (more reliable for SSL)
set -e

TOKEN="${VIMEO_ACCESS_TOKEN:-f91a90f3c8886a8c2f8eb2eb8a2f6b51}"
MP4_DIR="$(dirname "$0")/exports_looped/mp4"
MAPPING_FILE="$(dirname "$0")/exports_looped/vimeo_mapping.json"
FOLDER_URI="/users/57827402/projects/28234454"

# Already uploaded old IDs
DONE_IDS="1164244151 1164243753 1164244034 1164243895"

# Clips to upload: old_vimeo_id filename
declare -a CLIPS=(
    "1164243847 2026-02-07_19-42-19_seg005_loop.mp4"
    "1164244113 2026-02-08_18-37-52_seg007_loop.mp4"
    "1164244944 2026-02-09_19-44-56_seg069_loop.mp4"
    "1164245084 2026-02-09_19-44-56_seg101_loop.mp4"
    "1164244722 2026-02-09_19-44-56_seg013_loop.mp4"
    "1164244176 2026-02-08_21-49-46_seg001_loop.mp4"
    "1164243870 2026-02-07_19-42-19_seg008_loop.mp4"
    "1164244958 2026-02-09_19-44-56_seg073_loop.mp4"
)

for entry in "${CLIPS[@]}"; do
    OLD_ID=$(echo "$entry" | cut -d' ' -f1)
    FILENAME=$(echo "$entry" | cut -d' ' -f2)
    FILEPATH="$MP4_DIR/$FILENAME"
    NAME="${FILENAME%.mp4}"
    FILESIZE=$(stat -f%z "$FILEPATH")

    echo "=== Uploading $FILENAME ($((FILESIZE / 1024 / 1024))MB, replaces Vimeo $OLD_ID) ==="

    # Step 1: Create video entry
    CREATE_RESP=$(curl -s -X POST "https://api.vimeo.com/me/videos" \
        -H "Authorization: bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"upload\": {\"approach\": \"tus\", \"size\": \"$FILESIZE\"},
            \"name\": \"$NAME\",
            \"privacy\": {\"view\": \"anybody\", \"embed\": \"public\"}
        }")

    VIDEO_URI=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['uri'])" 2>/dev/null)
    UPLOAD_LINK=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['upload']['upload_link'])" 2>/dev/null)

    if [ -z "$VIDEO_URI" ] || [ -z "$UPLOAD_LINK" ]; then
        echo "  ERROR: Failed to create video entry"
        echo "  Response: $CREATE_RESP"
        continue
    fi

    NEW_ID=$(echo "$VIDEO_URI" | rev | cut -d/ -f1 | rev)
    echo "  Created: $VIDEO_URI"

    # Step 2: Upload via tus with curl (retry up to 3 times)
    UPLOAD_OK=false
    for attempt in 1 2 3; do
        echo "  Uploading (attempt $attempt)..."
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            --retry 3 --retry-delay 5 \
            -X PATCH "$UPLOAD_LINK" \
            -H "Tus-Resumable: 1.0.0" \
            -H "Upload-Offset: 0" \
            -H "Content-Type: application/offset+octet-stream" \
            --data-binary "@$FILEPATH" \
            --max-time 300)

        if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
            echo "  Upload OK (HTTP $HTTP_CODE)"
            UPLOAD_OK=true
            break
        else
            echo "  Upload failed (HTTP $HTTP_CODE), retrying..."
            sleep 5
        fi
    done

    if [ "$UPLOAD_OK" = false ]; then
        echo "  FAILED after 3 attempts"
        continue
    fi

    # Step 3: Add to folder
    curl -s -o /dev/null -X PUT \
        "https://api.vimeo.com${FOLDER_URI}/videos/${NEW_ID}" \
        -H "Authorization: bearer $TOKEN"

    echo "  OK → Vimeo $NEW_ID (old: $OLD_ID)"
    echo ""
done

echo "Done! Check vimeo_mapping.json for results."
