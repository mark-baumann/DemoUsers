#!/usr/bin/env python3
"""
CLI: Startet Chrome (sichtbar, nicht headless) mit Tor-Proxy und öffnet die angegebene URL.
Beispiel: python browser.py markb.de
"""

import sys
import logging
from urllib.parse import urlparse

# Vermeide Namenskonflikt mit diesem Skript-Namen durch relativen Import
from browser.session import BrowserSession

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    try:
        fh = logging.FileHandler('network.log')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        pass


def normalize_url(arg: str) -> str:
    # Falls kein Schema angegeben, https voranstellen
    parsed = urlparse(arg)
    if not parsed.scheme:
        return f"https://{arg}"
    return arg


def main():
    if len(sys.argv) < 2:
        print("Nutzung: python browser.py <url>")
        sys.exit(1)

    target = normalize_url(sys.argv[1])
    session = BrowserSession()

    if not session.start():
        print("✗ Browser konnte nicht gestartet werden")
        sys.exit(2)

    # Exit-IP direkt über Tor-Controller ermitteln und anzeigen (ohne Internet-Service)
    try:
        from proxy import TorProxy
        tor = session.browser_proxy.tor_proxy if hasattr(session, 'browser_proxy') else TorProxy()
        exit_ip = tor.get_exit_ip()
        if exit_ip:
            print(f"Tor Exit-IP: {exit_ip}")
            logger.info(f"Tor Exit-IP: {exit_ip}")
        else:
            print("Tor Exit-IP unbekannt")
            logger.warning("Tor Exit-IP unbekannt")
    except Exception as e:
        logger.error(f"Konnte Exit-IP nicht ermitteln: {e}")

    if not session.visit(target):
        print(f"✗ Konnte URL nicht laden: {target}")
        session.close()
        sys.exit(3)

    print(f"✓ Geöffnet: {target}")
    # Blockiere, bis der Benutzer das Browserfenster schließt
    session.wait_until_closed()


if __name__ == "__main__":
    main()