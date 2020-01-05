import asyncio
import datetime
import glob
import inspect
import logging
import pprint
import re
import sys
import traceback

import aiohttp
import discord
from discord.http import HTTPClient, Route

from .plot import plot_all
from .utils import load_json, write_json, run_period

from .settings import Settings

rootLogger = logging.getLogger(__name__)
rootLogger.setLevel(logging.DEBUG)

sh = logging.StreamHandler(stream=sys.stdout)
sh.setFormatter(logging.Formatter(
    fmt="[%(levelname)s]: %(message)s"
))

sh.setLevel(logging.DEBUG)

rootLogger.addHandler(sh)


class Response:
    def __init__(self, content, reply=False, delete_after=0, send_message=False):
        self.content = content
        self.send_message = send_message
        self.reply = reply
        self.delete_after = delete_after


class StatsBot(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(fetch_offline_members=False)
        self.already_ready = False
        self.settings = Settings(**kwargs)
        self.prefix = self.settings.prefix

        self.running_tasks = set()

        rootLogger.critical("Bot Initalized...\n")

    async def close(self):
        for task in self.running_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                rootLogger.debug(f"Canceled task {task}")
        await super().close()

    def run(self):
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.start(self.settings.token, bot=self.settings.bot))
        except Exception:
            traceback.print_exc()
            loop.run_until_complete(self.close())
        finally:
            loop.close()

    async def on_ready(self):
        if not self.already_ready:
            rootLogger.info("Connected To API!")
            rootLogger.info("~\n")

            self.running_tasks.add(
                asyncio.ensure_future(
                    run_period(
                        self.settings.fetch_period,
                        self.collect_write_data,
                        start=datetime.datetime.now() + datetime.timedelta(seconds=self.settings.delay_first_fetch)
                    )
                )
            )
            if self.settings.plot_period:
                self.running_tasks.add(
                    asyncio.ensure_future(run_period(self.settings.plot_period, self.plot_graphs))
                )
            self.already_ready = True
        else:
            rootLogger.info("Reconnected To API!")

    async def collect_write_data(self):
        discoverable_guilds = await self.collect_discoverable_guilds()
        merged_guilds = await self.collect_undiscoverable_guilds(discoverable_guilds)

        rootLogger.info(
            f"Collected {len(merged_guilds)} discoverable guilds! Outting to file..."
        )

        current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M")

        write_json(f"collected_data/guild_list_{current_time}.json", merged_guilds)
        write_json(f"guild_list.json", merged_guilds)
        rootLogger.info(f'See "collected_data/guild_list_{current_time}.json" for data of this time!')
        rootLogger.info('See "guild_list.json" for latest data!')

    def plot_graphs(self):
        # @TheerapakG: should we store this so that we don't need to load again?
        # or shold we populate graph as loaded?
        load_data = list()

        for filename in glob.iglob('./collected_data/guild_list_*.json'):
            date = re.search(r'guild_list_(.+).json', filename).group(1)
            
            this_data = list()
            raw = load_json(filename)
            for guild in raw.values():
                this_data.append(
                    {
                        'name': guild['name'],
                        'online': guild['approximate_presence_count'],
                        'member': guild['approximate_member_count']
                    }
                )

            load_data.append({'date': datetime.datetime.strptime(date, "%Y%m%d-%H%M"), 'guilds': this_data})

        fname = plot_all(load_data, 'date', 'member', 'name', 'guilds', x_date=True, n=10, title = 'top 10 members over time')
        rootLogger.info(f'See "{fname}" for member graph!')


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

        guild_dict = dict()

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

        guild_dict.update(discoverable_guilds)
        return guild_dict

    async def collect_discoverable_guilds(self):
        if self.user.bot:
            rootLogger.info("Not collecting discoverables via API due to being a bot")
            return dict()

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
