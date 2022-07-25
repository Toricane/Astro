from datetime import datetime, timedelta
import interactions
import logging
import src.cmds.mod
import src.const
import src.model
from src.const import *
from pymongo.database import *

log = logging.getLogger("astro.exts.mod")


class Mod(interactions.Extension):
    """An extension dedicated to /mod and other functionalities."""

    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.db: Database = kwargs.get("db")
        self.actions: Collection = self.db.Moderation
        self._actions = self.actions.find({"id": MOD_ID}).next()["actions"]

    async def get_actions(self) -> None:
        self._actions = self.actions.find({"id": TAGS_ID}).next()["actions"]

    @interactions.extension_command(**src.cmds.mod.cmd)
    async def mod(
        self,
        ctx: interactions.CommandContext,
        sub_command_group: str = "",
        sub_command: str = "",
        user: interactions.User = None,
        reason: str = None,
        id: int = 0,
        channel: interactions.Channel = None,
        length: int = 0,
        amount: int = 0,
        **kwargs
    ):
        log.debug("We've detected /mod, matching...")

        if not self.__check_role(ctx):
            await ctx.send(":x: You are not a moderator.", ephemeral=True)
        else:
            match sub_command_group:
                case "member":
                    match sub_command:
                        case "ban":
                            await self._ban_member(ctx, user, reason)
                        case "unban":
                            await self._unban_member(ctx, id, reason)
                        case "kick":
                            await self._kick_member(ctx, user, reason)
                        case "warn":
                            await self._warn_member(ctx, user, reason)
                        case "timeout":
                            await self._timeout_member(ctx, user, reason, **kwargs)
                        case "untimeout":
                            await self._untimeout_member(ctx, user, reason)
                case "channel":
                    match sub_command:
                        case "slowmode":
                            await self._slowmode_channel(ctx, length, channel)  # TODO do this
                        case "purge":
                            await self._purge_channel(ctx, amount, channel)
                        case "lock":
                            await self._lock_channel(ctx, channel)
                        case "unlock":
                            await self._unlock_channel(ctx, channel)

    async def _ban_member(self, ctx: interactions.CommandContext, member: interactions.Member, reason: str = "N/A"):
        """Bans a member from the server and logs into the database."""
        await ctx.defer(ephemeral=True)
        db = self._actions
        id = len(list(db.items())) + 1
        action = src.model.Action(
            id=id,
            type=src.model.ActionType.BAN,
            moderator=ctx.author,
            user=member.user,
            reason=reason
        )
        db.update({str(id): action._json})
        self.actions.find_one_and_update({"id": MOD_ID}, {"$set": {"actions": db}})
        await self.get_actions()
        embed = interactions.Embed(
            title="User banned",
            color=0xED4245,
            author=interactions.EmbedAuthor(
                name=f"{member.user.username}#{member.user.discriminator}",
                icon_url=member.user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(
                    name="Moderator",
                    value=f"{ctx.author.mention} ({ctx.author.user.username}#{ctx.author.user.discriminator})",
                    inline=True,
                ),
                interactions.EmbedField(
                    name="Timestamps",
                    value="\n".join(
                        [
                            f"Joined: <t:{round(member.joined_at.timestamp())}:R>.",
                            f"Created: <t:{round(member.id.timestamp.timestamp())}:R>.",
                        ]
                    ),
                ),
                interactions.EmbedField(name="Reason", value=reason),
            ]
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["action-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)
        await member.ban(guild_id=src.const.METADATA["guild"], reason=reason)
        await channel.send(embeds=embed)
        await ctx.send(f":heavy_check_mark: {member.mention} has been banned.", ephemeral=True)

    async def _unban_member(self, ctx: interactions.CommandContext, id: int, reason: str = "N/A"):
        """Unbans a user from the server and logs into the database."""
        await ctx.defer(ephemeral=True)
        db = self._actions
        _id = len(list(db.items())) + 1
        _user: dict = await self.bot._http.get_user(id=id)
        user = interactions.User(**_user)
        action = src.model.Action(
            id=_id,
            type=src.model.ActionType.KICK,
            moderator=ctx.author,
            user=user,
            reason=reason
        )
        db.update({str(_id): action._json})
        self.actions.find_one_and_update({"id": MOD_ID}, {"$set": {"actions": db}})
        await self.get_actions()
        embed = interactions.Embed(
            title="User unbanned",
            color=0x57F287,
            author=interactions.EmbedAuthor(
                name=f"{user.username}#{user.discriminator}",
                icon_url=user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(
                    name="Moderator",
                    value=f"{ctx.author.mention} ({ctx.author.user.username}#{ctx.author.user.discriminator})",
                    inline=True,
                ),
                interactions.EmbedField(name="Reason", value=reason),
            ]
        )
        _guild: dict = await self.bot._http.get_guild(src.const.METADATA["guild"])
        guild = interactions.Guild(**_guild, _client=self.bot._http)
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["action-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        await guild.remove_ban(user_id=id, reason=reason)
        await channel.send(embeds=embed)
        await ctx.send(f":heavy_check_mark: {user.mention} has been unbanned.", ephemeral=True)

    async def _kick_member(self, ctx: interactions.CommandContext, member: interactions.Member, reason: str = "N/A"):
        """Bans a member from the server and logs into the database."""
        await ctx.defer(ephemeral=True)
        db = self._actions
        id = len(list(db.items())) + 1
        action = src.model.Action(
            id=id,
            type=src.model.ActionType.KICK,
            moderator=ctx.author,
            user=member.user,
            reason=reason
        )
        db.update({str(id): action._json})
        self.actions.find_one_and_update({"id": MOD_ID}, {"$set": {"actions": db}})
        await self.get_actions()
        embed = interactions.Embed(
            title="User kicked",
            color=0xED4245,
            author=interactions.EmbedAuthor(
                name=f"{member.user.username}#{member.user.discriminator}",
                icon_url=member.user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(
                    name="Moderator",
                    value=f"{ctx.author.mention} ({ctx.author.user.username}#{ctx.author.user.discriminator})",
                    inline=True,
                ),
                interactions.EmbedField(
                    name="Timestamps",
                    value="\n".join(
                        [
                            f"Joined: <t:{round(member.joined_at.timestamp())}:R>.",
                            f"Created: <t:{round(member.id.timestamp.timestamp())}:R>.",
                        ]
                    ),
                ),
                interactions.EmbedField(name="Reason", value=reason),
            ]
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["action-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        await member.kick(guild_id=src.const.METADATA["guild"], reason=reason)
        await channel.send(embeds=embed)
        await ctx.send(f":heavy_check_mark: {member.mention} has been kicked.", ephemeral=True)

    async def _warn_member(self, ctx: interactions.CommandContext, member: interactions.Member, reason: str = "N/A"):
        """Warns a member in the server and logs into the database."""
        await ctx.defer(ephemeral=True)
        db = self._actions
        id = len(list(db.items())) + 1
        action = src.model.Action(
            id=id,
            type=src.model.ActionType.WARN,
            moderator=ctx.author,
            user=member.user,
            reason=reason
        )
        db.update({str(id): action._json})
        self.actions.find_one_and_update({"id": MOD_ID}, {"$set": {"actions": db}})
        await self.get_actions()
        embed = interactions.Embed(
            title="User warned",
            color=0xFEE75C,
            author=interactions.EmbedAuthor(
                name=f"{member.user.username}#{member.user.discriminator}",
                icon_url=member.user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(
                    name="Moderator",
                    value=f"{ctx.author.mention} ({ctx.author.user.username}#{ctx.author.user.discriminator})",
                    inline=True,
                ),
                interactions.EmbedField(
                    name="Timestamps",
                    value="\n".join(
                        [
                            f"Joined: <t:{round(member.joined_at.timestamp())}:R>.",
                            f"Created: <t:{round(member.id.timestamp.timestamp())}:R>.",
                        ]
                    ),
                ),
                interactions.EmbedField(name="Reason", value=reason),
            ]
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["action-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        await channel.send(embeds=embed)
        await ctx.send(f":heavy_check_mark: {member.mention} has been warned.", ephemeral=True)

    async def _timeout_member(self, ctx: interactions.CommandContext, member: interactions.Member, reason: str = "N/A", hours: int = 1, **kwargs):
        """Timeouts a member in the server and logs into the database."""
        await ctx.defer(ephemeral=True)
        db = self._actions
        id = len(list(db.items())) + 1
        action = src.model.Action(
            id=id,
            type=src.model.ActionType.TIMEOUT,
            moderator=ctx.author,
            user=member.user,
            reason=reason
        )
        db.update({str(id): action._json})
        self.actions.find_one_and_update({"id": MOD_ID}, {"$set": {"actions": db}})
        await self.get_actions()
        embed = interactions.Embed(
            title="User timed out",
            color=0xFEE75C,
            author=interactions.EmbedAuthor(
                name=f"{member.user.username}#{member.user.discriminator}",
                icon_url=member.user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(
                    name="Moderator",
                    value=f"{ctx.author.mention} ({ctx.author.user.username}#{ctx.author.user.discriminator})",
                    inline=True,
                ),
                interactions.EmbedField(
                    name="Timestamps",
                    value="\n".join(
                        [
                            f"Joined: <t:{round(member.joined_at.timestamp())}:R>.",
                            f"Created: <t:{round(member.id.timestamp.timestamp())}:R>.",
                        ]
                    ),
                ),
                interactions.EmbedField(name="Reason", value="N/A" if reason is None else reason),
            ]
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["action-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        time = datetime.utcnow()
        time += timedelta(hours=hours, **kwargs)
        await member.modify(guild_id=ctx.guild_id, communication_disabled_until=time.isoformat())
        await channel.send(embeds=embed)
        await ctx.send(f":heavy_check_mark: {member.mention} has been timed out until <t:{round(time.timestamp())}:F> (<t:{round(time.timestamp())}:R>).", ephemeral=True)

    async def _untimeout_member(self, ctx: interactions.CommandContext, member: interactions.Member, reason: str = "N/A"):
        """Untimeouts a member in the server and logs into the database."""
        await ctx.defer(ephemeral=True)
        db = self._actions
        id = len(list(db.items())) + 1
        action = src.model.Action(
            id=id,
            type=src.model.ActionType.TIMEOUT,
            moderator=ctx.author,
            user=member.user,
            reason=reason
        )
        db.update({str(id): action._json})
        self.actions.find_one_and_update({"id": MOD_ID}, {"$set": {"actions": db}})
        await self.get_actions()
        embed = interactions.Embed(
            title="User untimed out",
            color=0xFEE75C,
            author=interactions.EmbedAuthor(
                name=f"{member.user.username}#{member.user.discriminator}",
                icon_url=member.user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(
                    name="Moderator",
                    value=f"{ctx.author.mention} ({ctx.author.user.username}#{ctx.author.user.discriminator})",
                    inline=True,
                ),
                interactions.EmbedField(
                    name="Timestamps",
                    value="\n".join(
                        [
                            f"Joined: <t:{round(member.joined_at.timestamp())}:R>.",
                            f"Created: <t:{round(member.id.timestamp.timestamp())}:R>.",
                        ]
                    ),
                ),
                interactions.EmbedField(name="Reason", value="N/A" if reason is None else reason),
            ]
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["action-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        if member.communication_disabled_until is None:
            return await ctx.send(f":x: {member.mention} is not timed out.", ephemeral=True)

        await member.modify(guild_id=ctx.guild_id, communication_disabled_until=None)
        await channel.send(embeds=embed)
        await ctx.send(f":heavy_check_mark: {member.mention} has been untimed out.", ephemeral=True)

    async def _purge_channel(self, ctx: interactions.CommandContext, amount: int, channel: interactions.Channel = None):
        """Purges an amount of message of a channel."""
        if not channel:
            channel = await ctx.get_channel()
        
        await channel.purge(amount=amount, bulk=True)
        await ctx.send(f":heavy_check_mark: {channel.mention} was purged.", ephemeral=True)

    def __check_role(self, ctx: interactions.CommandContext) -> bool:
        """Checks whether an invoker has the Moderator role or not."""
        # TODO: please get rid of me when perms v2 is out. this is so dumb.
        return bool(str(src.const.METADATA["roles"]["Moderator"]) in [str(role) for role in ctx.author.roles])

    @interactions.extension_listener()
    async def on_message_delete(self, message: interactions.Message):
        embed = interactions.Embed(
            title="Message deleted",
            color=0xED4245,
            author=interactions.EmbedAuthor(
                name=f"{message.author.username}#{message.author.discriminator}",
                icon_url=message.author.avatar_url
            ),
            fields=[
                interactions.EmbedField(name="ID", value=str(message.author.id), inline=True),
                interactions.EmbedField(
                    name="Message",
                    value=message.content if message.content else "**Message could not be retrieved.**"
                ),
            ],
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["mod-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        await channel.send(embeds=embed)

    @interactions.extension_listener()
    async def on_message_update(self, before: interactions.Message, after: interactions.Message):
        embed = interactions.Embed(
            title="Message updated",
            color=0xED4245,
            author=interactions.EmbedAuthor(
                name=f"{before.author.username}#{before.author.discriminator}",
                icon_url=before.author.avatar_url
            ),
            fields=[
                interactions.EmbedField(name="ID", value=str(before.author.id), inline=True),
                interactions.EmbedField(
                    name="Before:",
                    value=before.content if before.content else "**Message could not be retrieved.**"
                ),
                interactions.EmbedField(
                    name="After:",
                    value=after.content if after.content else "**Message could not be retrieved.**"
                )
            ],
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["mod-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        await channel.send(embeds=embed)

    @interactions.extension_listener()
    async def on_guild_member_add(self, member: interactions.GuildMember):
        embed = interactions.Embed(
            title="User joined",
            color=0x57F287,
            author=interactions.EmbedAuthor(
                name=f"{member.user.username}#{member.user.discriminator}",
                icon_url=member.user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(name="ID", value=str(member.user.id)),
                interactions.EmbedField(
                    name="Timestamps",
                    value="\n".join(
                        [
                            f"Joined: <t:{round(member.joined_at.timestamp())}:R>.",
                            f"Created: <t:{round(member.id.timestamp.timestamp())}:R>.",
                        ]
                    ),
                ),
            ]
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["mod-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        await channel.send(embeds=embed)

    @interactions.extension_listener()
    async def on_guild_member_remove(self, member: interactions.GuildMember):
        embed = interactions.Embed(
            title="User left",
            color=0xED4245,
            thumbnail=interactions.EmbedImageStruct(url=member.user.avatar_url, height=256, width=256)._json,
            author=interactions.EmbedAuthor(
                name=f"{member.user.username}#{member.user.discriminator}",
                icon_url=member.user.avatar_url,
            ),
            fields=[
                interactions.EmbedField(name="ID", value=str(member.user.id)),
                interactions.EmbedField(
                    name="Timestamps",
                    value="\n".join(
                        [
                            f"Joined: <t:{round(member.joined_at.timestamp())}:R>.",
                            f"Created: <t:{round(member.id.timestamp.timestamp())}:R>.",
                        ]
                    ),
                ),
            ]
        )
        _channel: dict = await self.bot._http.get_channel(src.const.METADATA["channels"]["mod-logs"])
        channel = interactions.Channel(**_channel, _client=self.bot._http)

        await channel.send(embeds=embed)


def setup(bot, **kwargs):
    Mod(bot, **kwargs)
