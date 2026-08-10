"""Config flow for vPro / AMT."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .amt import AMTClient, AMTError
from .const import CONF_USE_TLS, DEFAULT_PORT_PLAIN, DOMAIN


class VproConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for vPro."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            client = AMTClient(
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                port=user_input[CONF_PORT],
                use_tls=user_input[CONF_USE_TLS],
            )
            try:
                await self.hass.async_add_executor_job(client.test)
            except AMTError as err:
                errors["base"] = (
                    "invalid_auth" if "auth" in str(err).lower() else "cannot_connect"
                )
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or user_input[CONF_HOST],
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_NAME): str,
                vol.Required(CONF_USERNAME, default="admin"): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT_PLAIN): int,
                vol.Required(CONF_USE_TLS, default=False): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
