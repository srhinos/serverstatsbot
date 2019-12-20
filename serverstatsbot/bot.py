import asyncio
import inspect
import logging
import pprint
import re
import traceback

import aiohttp
import discord
from discord.http import HTTPClient, Route

from .constants import prefix
from .utils import load_json, write_json

rootLogger = logging.getLogger(__name__)
rootLogger.setLevel(logging.DEBUG)


class Response:
    def __init__(self, content, reply=False, delete_after=0, send_message=False):
        self.content = content
        self.send_message = send_message
        self.reply = reply
        self.delete_after = delete_after


class StatsBot(discord.Client):
    def __init__(self):
        super().__init__(fetch_offline_members=False)
        self.prefix = prefix
        self.token = "PUT TOKEN HERE"

        rootLogger.critical("Bot Initalized...\n")

    def run(self):
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.start(self.token))
            loop.run_until_complete(self.connect())
        except Exception:
            traceback.print_exc()
            loop.run_until_complete(self.close())
        finally:
            loop.close()

    async def on_ready(self):
        rootLogger.info("Connected To API!")
        rootLogger.info("~\n")

        discoverable_guilds = await self.collect_discoverable_guilds()
        merged_guilds = await self.collect_undiscoverable_guilds(discoverable_guilds)

        rootLogger.info(
            f"Collected {len(merged_guilds)} discoverable guilds! Outting to file..."
        )
        write_json("guild_list.json", merged_guilds)
        rootLogger.info('See "guild_list.json" for data!')

    async def _wait_delete_msg(self, message, after):
        await asyncio.sleep(after)
        await self.safe_delete_message(message)

    async def safe_send_message(
        self,
        dest,
        *,
        content=None,
        tts=False,
        embed=None,
        file=None,
        files=None,
        expire_in=None,
        nonce=None,
        quiet=None,
    ):
        msg = None
        try:
            msg = await dest.send(
                content=content, tts=tts, embed=embed, file=file, files=files
            )
            # if embed:
            # print(f'Embed send time: "{time_after - time_before}"')
            if msg and expire_in:
                asyncio.ensure_future(self._wait_delete_msg(msg, expire_in))

        except discord.Forbidden:
            if not quiet:
                print("Error: Cannot send message to %s, no permission" % dest.name)
        except discord.NotFound:
            if not quiet:
                print(
                    "Warning: Cannot send message to %s, invalid channel?" % dest.name
                )
        finally:
            if msg:
                return msg

    async def safe_delete_message(self, message, *, quiet=False):
        try:
            return await message.delete()

        except discord.Forbidden:
            if not quiet:
                print(
                    'Error: Cannot delete message "%s", no permission'
                    % message.clean_content
                )
        except discord.NotFound:
            if not quiet:
                print(
                    'Warning: Cannot delete message "%s", message not found'
                    % message.clean_content
                )

    async def safe_edit_message(
        self,
        message,
        *,
        new_content=None,
        expire_in=0,
        send_if_fail=False,
        quiet=False,
        embed=None,
    ):
        msg = None
        try:
            if not embed:
                await message.edit(content=new_content)
                msg = message
            else:
                await message.edit(content=new_content, embed=embed)
                msg = message

            if msg and expire_in:
                asyncio.ensure_future(self._wait_delete_msg(msg, expire_in))

        except discord.NotFound:
            if not quiet:
                print(
                    'Warning: Cannot edit message "%s", message not found'
                    % message.clean_content
                )
            if send_if_fail:
                if not quiet:
                    print("Sending instead")
                msg = await self.safe_send_message(message.channel, content=new_content)
        finally:
            if msg:
                return msg

    async def collect_undiscoverable_guilds(self, discoverable_guilds):
        invite_code_list = load_json("guilds_not_discoverable.json")

        guild_dict = {}

        for invite_code in invite_code_list:
            try:
                partial_invite = await self.fetch_invite(invite_code, with_counts=True)
                if partial_invite.guild.id in discoverable_guilds:
                    continue

                guild_dict[partial_invite.guild.id] = {
                    "id": partial_invite.guild.id,
                    "name": partial_invite.guild.name,
                    "description": partial_invite.guild.description,
                    "features": partial_invite.guild.features,
                    "icon": partial_invite.guild.icon,
                    "splash": partial_invite.guild.splash,
                    "banner": partial_invite.guild.banner,
                    "approximate_presence_count": partial_invite.approximate_presence_count,
                    "approximate_member_count": partial_invite.approximate_member_count,
                }
            except Exception:
                continue

        return guild_dict.update(discoverable_guilds)

    async def collect_discoverable_guilds(self):
        limit = 48
        offset = 0
        params = {"offset": offset, "limit": limit}

        request = await self.http.request(
            Route("GET", f"/discoverable-guilds"), params=params
        )

        guild_dict = {guild["id"]: guild for guild in request["guilds"]}

        while request["total"] > 0:

            await asyncio.sleep(0.5)

            offset += limit

            params = {"offset": offset, "limit": limit}

            request = await self.http.request(
                Route("GET", f"/discoverable-guilds"), params=params
            )

            temp_dict = {guild["id"]: guild for guild in request["guilds"]}
            guild_dict.update(temp_dict)

        return guild_dict


if __name__ == "__main__":
    bot = StatsBot()
    bot.run()
