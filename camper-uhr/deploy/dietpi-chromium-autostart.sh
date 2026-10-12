#!/bin/dash
# DietPi kiosk launcher for the 1480x320 Camper Uhr display.

RES_X=$(sed -n '/^[[:blank:]]*SOFTWARE_CHROMIUM_RES_X=/{s/^[^=]*=//p;q}' /boot/dietpi.txt)
RES_Y=$(sed -n '/^[[:blank:]]*SOFTWARE_CHROMIUM_RES_Y=/{s/^[^=]*=//p;q}' /boot/dietpi.txt)
URL=$(sed -n '/^[[:blank:]]*SOFTWARE_CHROMIUM_AUTOSTART_URL=/{s/^[^=]*=//p;q}' /boot/dietpi.txt)
URL=${URL:-http://localhost:8080}
case "$URL" in
  *\?*) URL="${URL}&kiosk_build=0.6.3" ;;
  *) URL="${URL}?kiosk_build=0.6.3" ;;
esac

# MapLibre requires WebGL; test graphics and rotation on the target device.
CHROMIUM_OPTS="--kiosk --enable-webgl --disable-features=Translate,TranslateUI --no-first-run --disable-translate --lang=de-DE --overscroll-history-navigation=0 --window-size=${RES_X:-1480},${RES_Y:-320} --window-position=0,0"

# Avoid Chromium's connection-error page when the Pi boots faster than the app.
until curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1; do
  sleep 1
done

STARTX='xinit'
[ "$USER" = 'root' ] || STARTX='startx'

exec "$STARTX" /bin/sh -c "xrandr --output HDMI-1 --rotate left; exec /usr/bin/chromium $CHROMIUM_OPTS '$URL'"
