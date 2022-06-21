#!/bin/bash
for i in */LC_MESSAGES/*.po; do
  msgfmt -o "${i%\.*}.mo" $i
done
