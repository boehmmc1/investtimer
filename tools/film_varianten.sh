#!/bin/sh
# Erzeugt aus public/media/invest-timer.mp4 die AV1-Fassung und das Poster (erstes Bild) fuer die Film-Buehne.
# Braucht ffmpeg (Ubuntu-Paket). Ergebnis: AV1 ca. 0,93 MB statt 2,79 MB, SSIM 0,991.
set -eu
M=$(dirname "$0")/../public/media
ffmpeg -v error -y -i "$M/invest-timer.mp4" -frames:v 1 -q:v 3 "$M/invest-timer-start.jpg"
ffmpeg -v error -y -i "$M/invest-timer.mp4" -an -c:v libaom-av1 -crf 40 -b:v 0 -cpu-used 6 -row-mt 1 -tiles 2x2 -g 240 -pix_fmt yuv420p "$M/invest-timer.webm"
ls -la "$M"/invest-timer.*
