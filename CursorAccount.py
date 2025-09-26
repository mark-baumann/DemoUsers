#!/usr/bin/env python3
import os
import time
import logging
from dataclasses import dataclass
from typing import Optional
import sys
import subprocess

import requests

from faker import Faker
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Browser.browser.session import BrowserSession
from MailClient import create_address


logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    try:
        fh = logging.FileHandler('cursor_account.log')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        pass


SIGNUP_URL = "https://authenticator.cursor.sh/sign-up"
MAIL_SERVICE_DEFAULT = "guerrillamail"


@dataclass
class AccountData:
    first_name: str
    last_name: str
    full_name: str
    email: str
    token: str
    password: str


def generate_identity() -> tuple[str, str, str, str]:
    fake = Faker()
    first_name = fake.first_name()
    last_name = fake.last_name()
    full_name = f"{first_name} {last_name}"
    # Simple strong password generator
    password = fake.password(length=16, special_chars=True, digits=True, upper_case=True, lower_case=True)
    return first_name, last_name, full_name, password


def obtain_temp_email(service: str = MAIL_SERVICE_DEFAULT) -> tuple[str, str, str]:
    info = create_address(service)
    return info["email"], info["token"], info["service"]


def ensure_mail_api_running(host: str = "127.0.0.1", port: int = 8000, timeout: int = 30) -> None:
    base = f"http://{host}:{port}"
    try:
        requests.get(f"{base}/", timeout=2)
        return
    except Exception:
        pass
    # Start uvicorn server
    logger.info("Mail API nicht erreichbar – starte uvicorn…")
    proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "MailService.api_server:app",
        "--host", host, "--port", str(port), "--log-level", "warning"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait until ready
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(f"{base}/", timeout=1)
            logger.info("Mail API bereit.")
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Mail API konnte nicht gestartet werden")


def wait_and_type(driver, by, selector: str, text: str, timeout: int = 30):
    el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
    el.clear()
    el.send_keys(text)
    return el


def click_when_clickable(driver, by, selector: str, timeout: int = 30):
    el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))
    el.click()
    return el


def create_cursor_account(signup_url: str = SIGNUP_URL, mail_service: str = MAIL_SERVICE_DEFAULT) -> Optional[AccountData]:
    # Ensure Mail API is available for temp email
    ensure_mail_api_running()
    first_name, last_name, full_name, password = generate_identity()
    email, token, service = obtain_temp_email(mail_service)
    logger.info(f"Generated user: {full_name}, email: {email} via {service}")

    session = BrowserSession()
    if not session.start():
        logger.error("Browser session failed to start")
        return None

    try:
        if not session.visit(signup_url):
            logger.error("Failed to load sign-up page")
            return None

        driver = session.browser_proxy.driver

        # NOTE: The actual selectors may need adjustment based on live DOM
        # Try common field names and fallbacks
        # Name
        try:
            wait_and_type(driver, By.CSS_SELECTOR, 'input[name="name"], input#name, input[autocomplete="name"]', full_name)
        except Exception:
            try:
                # Split fields
                wait_and_type(driver, By.CSS_SELECTOR, 'input[name="firstName"], input#firstName', first_name)
                wait_and_type(driver, By.CSS_SELECTOR, 'input[name="lastName"], input#lastName', last_name)
            except Exception:
                logger.warning("Could not locate name fields")

        # Email
        wait_and_type(driver, By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input#email', email)

        # Password
        wait_and_type(driver, By.CSS_SELECTOR, 'input[type="password"], input[name="password"], input#password', password)

        # Terms checkbox (best-effort)
        try:
            click_when_clickable(driver, By.CSS_SELECTOR, 'input[type="checkbox"], input[name*="terms"], input#terms')
        except Exception:
            pass

        # Submit button
        try:
            click_when_clickable(driver, By.CSS_SELECTOR, 'button[type="submit"], button[data-testid*="submit"], button:has(span:contains("Sign Up"))')
        except Exception:
            # Fallback to pressing Enter on password field
            try:
                pwd = driver.find_element(By.CSS_SELECTOR, 'input[type="password"], input[name="password"], input#password')
                pwd.submit()
            except Exception:
                logger.error("Could not submit the form")
                return None

        # Wait for next UI state (e.g., email verification step)
        time.sleep(5)

        # At this point, verification email should be incoming. The script focuses on account creation; handling the verification click can be added later.

        return AccountData(
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            email=email,
            token=token,
            password=password,
        )
    finally:
        # Keep the browser open for manual review; comment out to auto-close
        session.wait_until_closed()


if __name__ == "__main__":
    acc = create_cursor_account()
    if acc:
        print("\nAccount created (pending email verification):")
        print(f"Name : {acc.full_name}")
        print(f"Email: {acc.email}")
        print(f"Pass : {acc.password}")
    else:
        print("Failed to create account.")
