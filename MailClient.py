import os
import time
import json
import requests

API_BASE = "http://127.0.0.1:8000"


def create_address(service: str, domain: str | None = None):
    payload = {"service": service}
    if domain:
        payload["domain"] = domain
    r = requests.post(f"{API_BASE}/address", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def list_messages(service: str, token: str):
    r = requests.get(
        f"{API_BASE}/messages",
        params={"service": service, "token": token},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def fetch_message(service: str, token: str, message_id: str):
    r = requests.get(
        f"{API_BASE}/messages/{message_id}",
        params={"service": service, "token": token},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def save_mail(base_dir: str, email: str, message_id: str | int, meta: dict, body: str):
    email_dir = os.path.join(base_dir, email)
    ensure_dir(email_dir)
    # Save HTML if it looks like HTML, otherwise .txt
    ext = "html" if isinstance(body, str) and "<" in body and ">" in body else "txt"
    body_path = os.path.join(email_dir, f"{message_id}.{ext}")
    meta_path = os.path.join(email_dir, f"{message_id}.json")
    try:
        with open(body_path, "w", encoding="utf-8") as f:
            f.write(body or "")
    except Exception:
        # Fallback to txt
        body_path = os.path.join(email_dir, f"{message_id}.txt")
        with open(body_path, "w", encoding="utf-8") as f:
            f.write(str(body) if body is not None else "")
    # include body in the JSON too
    meta_with_body = dict(meta)
    meta_with_body["body"] = body
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_with_body, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    base_mail_dir = os.path.join(os.getcwd(), "mails")
    ensure_dir(base_mail_dir)

    # Choose service from API
    try:
        services = requests.get(f"{API_BASE}/services", timeout=10).json()
    except Exception:
        services = ["guerrillamail", "mailgw", "mailtm", "dropmail", "tempmaillol"]
    print("\n========================")
    print("  Choose mail service  ")
    print("========================")
    for i, s in enumerate(services, 1):
        print(f"[{i}] {s}")
    choice = input(f"Select [1-{len(services)}] (default 1): ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(services):
        service = services[0]
    else:
        service = services[int(choice) - 1]

    info = create_address(service)
    email = info["email"]
    token = info["token"]
    service = info["service"]
    print("\n========================")
    print("        ACTIVE         ")
    print("========================")
    print(f"Service : {service}")
    print(f"Address : {email}")
    print("Polling… Press Ctrl+C to stop.\n")

    seen_ids: set[str] = set()
    interval_seconds = 5

    try:
        while True:
            try:
                msgs = list_messages(service, token) or []
                new_msgs = []
                for m in msgs:
                    mid = str(m.get("mail_id"))
                    if mid not in seen_ids:
                        new_msgs.append(m)
                        seen_ids.add(mid)
                for m in new_msgs:
                    mid = str(m.get("mail_id"))
                    try:
                        full = fetch_message(service, token, mid)
                    except requests.HTTPError as e:
                        print(f"Fetch failed for {mid}: {e}")
                        continue
                    body = full.get("mail_body", "")
                    meta = {
                        "subject": full.get("subject"),
                        "from": full.get("mail_from"),
                        "service": service,
                        "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    save_mail(base_mail_dir, email, mid, meta, body)
                    print("------------------------")
                    print(f"From   : {meta['from']}")
                    print(f"Subject: {meta['subject']}")
                    print("Body:")
                    print(body if isinstance(body, str) else str(body))
                    print("\n")
            except Exception as ex:
                print(f"Poll error: {ex}")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("Stopped.")
