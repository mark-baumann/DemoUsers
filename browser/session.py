#!/usr/bin/env python3
"""
Browser Proxy Session Manager
Verwendet die proxy/tor_proxy.py für Tor-Verbindungen und stellt Browser-Sessions bereit.
"""

import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from proxy import TorProxy

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


class BrowserProxy:
    def __init__(self):
        self.tor_proxy = TorProxy()
        self.driver = None
        self.session = None

    def setup_chrome_proxy(self) -> ChromeOptions:
        options = ChromeOptions()

        socks_proxy = self.tor_proxy.get_proxy_settings()['socks_proxy']
        options.add_argument(f'--proxy-server=socks5://{socks_proxy}')

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--ignore-certificate-errors')

        # Nicht headless: Standard-Mode, Fenster sichtbar
        options.add_argument('--window-size=1200,800')

        return options

    def start_browser(self) -> bool:
        try:
            logger.info("Starte Tor...")
            if not self.tor_proxy.start_tor():
                logger.error("Tor konnte nicht gestartet werden")
                return False

            self.session = self.tor_proxy.create_session()
            if not self.session:
                logger.error("Proxy-Session konnte nicht erstellt werden")
                return False

            logger.info("Starte Chrome Browser...")
            options = self.setup_chrome_proxy()
            self.driver = webdriver.Chrome(options=options)
            logger.info("Chrome gestartet")
            return True
        except WebDriverException as e:
            logger.error(f"Fehler beim Starten des Browsers: {e}")
            return False
        except Exception as e:
            logger.error(f"Unerwarteter Fehler: {e}")
            return False

    def navigate_to(self, url: str, timeout: int = 30) -> bool:
        if not self.driver:
            logger.error("Browser nicht gestartet")
            return False
        try:
            logger.info(f"Navigiere zu: {url}")
            self.driver.get(url)
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.info("✓ Seite geladen")
            return True
        except TimeoutException:
            logger.error(f"Timeout beim Laden von {url}")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Navigieren zu {url}: {e}")
            return False

    def keep_open_until_closed(self):
        if not self.driver:
            return
        try:
            # Blockiere, bis Fenster geschlossen wurde
            while True:
                if len(self.driver.window_handles) == 0:
                    break
                time.sleep(0.5)
        finally:
            self.close()

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser geschlossen")
            except Exception:
                pass
            finally:
                self.driver = None
        self.tor_proxy.stop_tor()
        logger.info("Tor gestoppt")


class BrowserSession:
    def __init__(self):
        self.browser_proxy = BrowserProxy()

    def start(self) -> bool:
        return self.browser_proxy.start_browser()

    def visit(self, url: str) -> bool:
        return self.browser_proxy.navigate_to(url)

    def wait_until_closed(self):
        self.browser_proxy.keep_open_until_closed()

    def close(self):
        self.browser_proxy.close()


