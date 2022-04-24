from logging import getLogger

import voluptuous as vol
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST

from . import DOMAIN
from .ecoflow.local import PRODUCTS, receive, send
from .ecoflow.local.client import EcoFlowLocalClient

_LOGGER = getLogger(__name__)


class EcoflowConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    host = None

    async def _get_sn_main(self, host: str):
        client = EcoFlowLocalClient(self.host, _LOGGER)
        client.run()
        try:
            info = receive.sn(await client.request(send.get_sn_main()))
        finally:
            await client.close()
        await self.async_set_unique_id(info["serial"])
        self._abort_if_unique_id_configured(updates={
            CONF_HOST: host,
        })
        return info

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo):
        await self._get_sn_main(discovery_info.ip)
        self.host = discovery_info.ip
        return self.async_show_form(step_id="user")

    async def async_step_user(self, user_input: dict = None):
        if user_input:
            self.host = user_input.get(CONF_HOST)

        errors = {}
        if self.host:
            try:
                info = await self._get_sn_main(self.host)
            except TimeoutError:
                errors["base"] = "timeout"
            else:
                pn = PRODUCTS.get(info["product"], "")
                if pn != "":
                    pn += " "
                return self.async_create_entry(
                    title=f'{pn}{info["serial"][-6:]}',
                    data={
                        CONF_HOST: self.host,
                        "product": info["product"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=self.host): str,
            }),
            last_step=True,
        )
