def build_engineer_auth_headers(
    *,
    api_key: str | None = None,
    device_token: str | None = None,
) -> dict[str, str]:
    if device_token:
        return {"x-device-token": device_token}
    if api_key:
        return {"x-api-key": api_key}
    return {}
