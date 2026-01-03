#!/bin/bash

PHOTO_DIR="/Volumes/Archive/Photos"
OUTPUT_DIR="/Volumes/Workspace/sublingualism/andc"
OUTPUT_FILE="$OUTPUT_DIR/solstice-equinox-photos.txt"

echo "Finding solstice and equinox photos in $PHOTO_DIR"
echo "Output: $OUTPUT_FILE"
echo ""

# Create/clear output file
> "$OUTPUT_FILE"

echo "Searching for Spring Equinox (March 19-21)..."
exiftool -r -if '($DateTimeOriginal =~ /:03:19/ or $DateTimeOriginal =~ /:03:20/ or $DateTimeOriginal =~ /:03:21/)' \
    -printFormat '$Directory/$FileName' "$PHOTO_DIR" >> "$OUTPUT_FILE"

echo "Searching for Summer Solstice (June 20-22)..."
exiftool -r -if '($DateTimeOriginal =~ /:06:20/ or $DateTimeOriginal =~ /:06:21/ or $DateTimeOriginal =~ /:06:22/)' \
    -printFormat '$Directory/$FileName' "$PHOTO_DIR" >> "$OUTPUT_FILE"

echo "Searching for Fall Equinox (September 22-24)..."
exiftool -r -if '($DateTimeOriginal =~ /:09:22/ or $DateTimeOriginal =~ /:09:23/ or $DateTimeOriginal =~ /:09:24/)' \
    -printFormat '$Directory/$FileName' "$PHOTO_DIR" >> "$OUTPUT_FILE"

echo "Searching for Winter Solstice (December 20-23)..."
exiftool -r -if '($DateTimeOriginal =~ /:12:20/ or $DateTimeOriginal =~ /:12:21/ or $DateTimeOriginal =~ /:12:22/ or $DateTimeOriginal =~ /:12:23/)' \
    -printFormat '$Directory/$FileName' "$PHOTO_DIR" >> "$OUTPUT_FILE"

echo ""
echo "Searching by filename patterns (for photos without EXIF dates)..."
find "$PHOTO_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.tif" -o -iname "*.tiff" -o -iname "*.png" -o -iname "*.cr2" -o -iname "*.nef" -o -iname "*.dng" \) \
    \( -name "*03-19*" -o -name "*03-20*" -o -name "*03-21*" \
       -o -name "*06-20*" -o -name "*06-21*" -o -name "*06-22*" \
       -o -name "*09-22*" -o -name "*09-23*" -o -name "*09-24*" \
       -o -name "*12-20*" -o -name "*12-21*" -o -name "*12-22*" -o -name "*12-23*" \) \
    ! -name "._*" 2>/dev/null >> "$OUTPUT_FILE"

echo "Removing duplicates..."
sort -u "$OUTPUT_FILE" -o "$OUTPUT_FILE"

echo ""
echo "Done! Output file: $OUTPUT_FILE"
echo "Total photos found: $(wc -l < "$OUTPUT_FILE")"
