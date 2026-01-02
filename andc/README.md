# ANDC

ANDC (All Night Dance Celebration) was a quarterly all-night dance party hosted by the Divine Rhythm Society in San Francisco. The events were held on the solstices and equinoxes.

I did video and projection installations for the group for several years.

## Tools

### tag-solstice-equinox.sh

A script to find photos taken during solstice and equinox date ranges (2005-2024):

- Spring Equinox: March 19-21
- Summer Solstice: June 20-22
- Fall Equinox: September 22-24
- Winter Solstice: December 20-23

**Usage:**
```bash
./tag-solstice-equinox.sh
```

**Output:** `solstice-equinox-photos.txt` - a list of photo paths, one per line.

**Requirements:** [exiftool](https://exiftool.org/) (`brew install exiftool`)
