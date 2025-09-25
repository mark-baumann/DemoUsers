import asyncio
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .temp_mail_apis import SERVICE_REGISTRY


app = FastAPI(title="FakeAccounts Mail API")


class CreateAddressRequest(BaseModel):
    service: str
    domain: Optional[str] = None


class CreateAddressResponse(BaseModel):
    email: str
    token: str
    service: str


class Message(BaseModel):
    mail_id: str | int
    subject: str
    mail_from: str
    mail_date: Optional[str] = None
    receive_time: Optional[float] = None


class FetchMessageResponse(BaseModel):
    mail_body: str
    mail_from: str
    subject: str
    mail_date: Optional[str] = None
    mail_size: Optional[int] = None
    receive_time: Optional[float] = None


def _get_api(service_key: str):
    api_class = SERVICE_REGISTRY.get(service_key)
    if not api_class:
        raise HTTPException(status_code=404, detail=f"Unknown service '{service_key}'")
    return api_class()


@app.get("/services", response_model=List[str])
async def list_services():
    return list(SERVICE_REGISTRY.keys())


@app.get("/domains", response_model=List[str])
async def list_domains(service: str = Query(..., description="Service key")):
    api = _get_api(service)
    try:
        domains = getattr(api, "domains", [])
        if callable(domains):
            domains = domains()
        return domains or []
    except Exception:
        return []


@app.post("/address", response_model=CreateAddressResponse)
async def create_address(req: CreateAddressRequest):
    api = _get_api(req.service)
    result = await api.create_address(req.domain)
    email = result.get("email")
    token = result.get("token")
    if not email or not token:
        raise HTTPException(status_code=502, detail="Service did not return email/token")
    return CreateAddressResponse(email=email, token=token, service=req.service)


@app.get("/messages", response_model=List[Message])
async def get_messages(service: str, token: str):
    api = _get_api(service)
    msgs = await api.get_messages(token)
    return msgs


@app.get("/messages/{message_id}")
async def fetch_message(message_id: str, service: str, token: str):
    api = _get_api(service)
    data = await api.fetch_message(token, message_id)
    # Normalize types to satisfy response model
    if data is None:
        raise HTTPException(status_code=502, detail="Empty response from service")
    # Coerce mail_body to string
    body = data.get("mail_body", "")
    if not isinstance(body, str):
        try:
            body = "\n".join(map(str, body)) if isinstance(body, list) else str(body)
        except Exception:
            body = ""
    data["mail_body"] = body
    # Final guard: drop mail_date entirely (optional field)
    data.pop("mail_date", None)
    # Coerce mail_from and subject to string
    for k in ("mail_from", "subject"):
        if k in data and not isinstance(data[k], str):
            try:
                data[k] = str(data[k])
            except Exception:
                data[k] = ""
    # Coerce mail_size to int if possible
    if "mail_size" in data and not isinstance(data["mail_size"], int):
        try:
            data["mail_size"] = int(data["mail_size"]) if data["mail_size"] is not None else None
        except Exception:
            data["mail_size"] = None
    return data


@app.get("/")
async def root():
    return {"name": "FakeAccounts Mail API", "services": list(SERVICE_REGISTRY.keys())}


