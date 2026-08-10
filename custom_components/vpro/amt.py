"""Minimal Intel AMT / vPro WSMAN client (sync, requests + HTTP Digest).

Wrapped by the HA integration via hass.async_add_executor_job.
Hand-rolled WSMAN because no maintained async AMT lib exists; envelopes follow
the same conventions as amttool / MeshCentral (proven against real AMT).
"""
from __future__ import annotations

import re
import uuid

import requests
from requests.auth import HTTPDigestAuth

# CIM power states (RequestPowerStateChange / read PowerState)
POWER_ON = 2
POWER_SLEEP_LIGHT = 3
POWER_SLEEP_DEEP = 4
POWER_CYCLE_SOFT = 5          # off (soft) -> on
POWER_OFF_HARD = 6
POWER_HIBERNATE = 7
POWER_OFF_SOFT = 8
POWER_CYCLE_HARD = 9          # off (hard) -> on
POWER_RESET = 10             # master bus reset

# read PowerState value -> coarse state
ON_STATES = {POWER_ON}
SLEEP_STATES = {POWER_SLEEP_LIGHT, POWER_SLEEP_DEEP, POWER_HIBERNATE}
OFF_STATES = {6, 8, 12, 13, 14, 15}

_NS = (
    'xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
    'xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" '
    'xmlns:wsman="http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd" '
    'xmlns:wsen="http://schemas.xmlsoap.org/ws/2004/09/enumeration"'
)

CIM = "http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2"


class AMTError(Exception):
    """AMT communication / protocol error."""


class AMTClient:
    """Synchronous AMT WSMAN client."""

    def __init__(self, host, username, password, port=16993, use_tls=True, timeout=12):
        self.host = host
        self.timeout = timeout
        scheme = "https" if use_tls else "http"
        self.url = f"{scheme}://{host}:{port}/wsman"
        self._session = requests.Session()
        self._session.auth = HTTPDigestAuth(username, password)
        self._session.verify = False  # AMT uses a self-signed cert
        self._session.headers.update({"Content-Type": "application/soap+xml;charset=UTF-8"})

    # -- low level ---------------------------------------------------------
    def _post(self, body: str) -> str:
        try:
            r = self._session.post(self.url, data=body.encode("utf-8"), timeout=self.timeout)
        except requests.RequestException as err:
            raise AMTError(f"connection failed: {err}") from err
        if r.status_code == 401:
            raise AMTError("authentication failed (401)")
        if r.status_code >= 400:
            raise AMTError(f"HTTP {r.status_code}: {r.text[:200]}")
        return r.text

    def _header(self, action: str, resource: str, selectors: str = "") -> str:
        return (
            f'<wsa:Action s:mustUnderstand="true">{action}</wsa:Action>'
            f'<wsa:To s:mustUnderstand="true">{self.url}</wsa:To>'
            f'<wsman:ResourceURI s:mustUnderstand="true">{resource}</wsman:ResourceURI>'
            f'<wsa:MessageID s:mustUnderstand="true">uuid:{uuid.uuid4()}</wsa:MessageID>'
            '<wsa:ReplyTo><wsa:Address>'
            "http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous"
            "</wsa:Address></wsa:ReplyTo>"
            f"{selectors}"
        )

    def _envelope(self, header: str, body: str) -> str:
        return (
            f"<?xml version='1.0' encoding='UTF-8'?>"
            f"<s:Envelope {_NS}><s:Header>{header}</s:Header>"
            f"<s:Body>{body}</s:Body></s:Envelope>"
        )

    def _enumerate(self, resource: str) -> str:
        """WSMAN Enumerate then Pull (AMT ignores OptimizeEnumeration).

        Returns the Pull response body (items), or "" if nothing.
        """
        en_action = "http://schemas.xmlsoap.org/ws/2004/09/enumeration/Enumerate"
        pull_action = "http://schemas.xmlsoap.org/ws/2004/09/enumeration/Pull"
        resp = self._post(self._envelope(self._header(en_action, resource), "<wsen:Enumerate/>"))
        m = re.search(r"EnumerationContext>([^<]+)<", resp)
        if not m:
            return ""
        ctx = m.group(1)
        body = (
            f"<wsen:Pull><wsen:EnumerationContext>{ctx}</wsen:EnumerationContext>"
            "<wsen:MaxElements>50</wsen:MaxElements></wsen:Pull>"
        )
        return self._post(self._envelope(self._header(pull_action, resource), body))

    # -- operations --------------------------------------------------------
    def get_power_state(self) -> int | None:
        """Return current CIM PowerState (int) or None."""
        resp = self._enumerate(f"{CIM}/CIM_AssociatedPowerManagementService")
        m = re.search(r"<[^>]*PowerState>\s*(\d+)\s*<", resp)
        return int(m.group(1)) if m else None

    def set_power(self, power_state: int) -> bool:
        """Invoke RequestPowerStateChange. Returns True on ReturnValue 0."""
        resource = f"{CIM}/CIM_PowerManagementService"
        action = f"{resource}/RequestPowerStateChange"
        selectors = (
            "<wsman:SelectorSet>"
            '<wsman:Selector Name="Name">Intel(r) AMT Power Management Service</wsman:Selector>'
            '<wsman:Selector Name="SystemName">Intel(r) AMT</wsman:Selector>'
            '<wsman:Selector Name="CreationClassName">CIM_PowerManagementService</wsman:Selector>'
            '<wsman:Selector Name="SystemCreationClassName">CIM_ComputerSystem</wsman:Selector>'
            "</wsman:SelectorSet>"
        )
        body = (
            f'<p:RequestPowerStateChange_INPUT xmlns:p="{resource}">'
            f"<p:PowerState>{power_state}</p:PowerState>"
            "<p:ManagedElement>"
            "<wsa:Address>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:Address>"
            "<wsa:ReferenceParameters>"
            f"<wsman:ResourceURI>{CIM}/CIM_ComputerSystem</wsman:ResourceURI>"
            "<wsman:SelectorSet>"
            '<wsman:Selector Name="Name">ManagedSystem</wsman:Selector>'
            '<wsman:Selector Name="CreationClassName">CIM_ComputerSystem</wsman:Selector>'
            "</wsman:SelectorSet>"
            "</wsa:ReferenceParameters>"
            "</p:ManagedElement>"
            "</p:RequestPowerStateChange_INPUT>"
        )
        resp = self._post(self._envelope(self._header(action, resource, selectors), body))
        m = re.search(r"<[^>]*ReturnValue>\s*(\d+)\s*<", resp)
        return m is not None and m.group(1) == "0"

    def get_versions(self) -> dict[str, str]:
        """Enumerate CIM_SoftwareIdentity -> {InstanceID: VersionString}."""
        resp = self._enumerate(f"{CIM}/CIM_SoftwareIdentity")
        out: dict[str, str] = {}
        for inst in re.findall(r"<[^>]*CIM_SoftwareIdentity>(.*?)</[^>]*CIM_SoftwareIdentity>", resp, re.S):
            iid = re.search(r"<[^>]*InstanceID>(.*?)<", inst)
            ver = re.search(r"<[^>]*VersionString>(.*?)<", inst)
            if iid and ver:
                out[iid.group(1).strip()] = ver.group(1).strip()
        return out

    def boot_to_bios(self) -> bool:
        """Best-effort: set next boot to BIOS setup then reset. EXPERIMENTAL."""
        # 1) AMT_BootSettingData PUT requires read-modify-write of the full object.
        bsd = f"{CIM}/AMT_BootSettingData"
        get_action = "http://schemas.xmlsoap.org/ws/2004/09/transfer/Get"
        cur = self._post(self._envelope(self._header(get_action, bsd), ""))
        body_m = re.search(r"<s:Body>(.*?)</s:Body>", cur, re.S)
        if not body_m:
            raise AMTError("could not read AMT_BootSettingData")
        obj = body_m.group(1)
        obj = re.sub(r"(<[^>]*BIOSSetup>)[^<]*(<)", r"\g<1>true\g<2>", obj)
        if "BIOSSetup" not in obj:
            raise AMTError("BIOSSetup field not found")
        put_action = "http://schemas.xmlsoap.org/ws/2004/09/transfer/Put"
        self._post(self._envelope(self._header(put_action, bsd), obj))
        # 2) reset into setup
        return self.set_power(POWER_RESET)

    def test(self) -> int | None:
        """Auth + connectivity probe used by config flow. Returns power state."""
        return self.get_power_state()
