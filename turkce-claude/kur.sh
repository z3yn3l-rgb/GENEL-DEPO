#!/usr/bin/env bash
# Claude Code'u Türkçe konuşacak şekilde ayarlar (macOS / Linux).
# Kullanım: bash kur.sh            -> Türkçe'yi açar
#           bash kur.sh kaldir     -> Türkçe ayarını kaldırır
set -euo pipefail

AYAR_DIZINI="$HOME/.claude"
AYAR_DOSYASI="$AYAR_DIZINI/settings.json"
mkdir -p "$AYAR_DIZINI"
[ -f "$AYAR_DOSYASI" ] || echo '{}' > "$AYAR_DOSYASI"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Hata: python3 gerekli." >&2
  exit 1
fi

cp "$AYAR_DOSYASI" "$AYAR_DOSYASI.yedek"

python3 - "$AYAR_DOSYASI" "${1:-kur}" <<'PY'
import json, sys
yol, islem = sys.argv[1], sys.argv[2]
with open(yol, encoding="utf-8") as f:
    ayar = json.load(f)
if islem == "kaldir":
    ayar.pop("language", None)
    print("Türkçe ayarı kaldırıldı.")
else:
    ayar["language"] = "turkish"
    print("Türkçe ayarı eklendi.")
with open(yol, "w", encoding="utf-8") as f:
    json.dump(ayar, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY

echo "Ayar dosyası: $AYAR_DOSYASI (yedek: settings.json.yedek)"
echo "Claude Code'u yeniden başlatın."
