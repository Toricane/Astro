import interactions
import src.const
import aiohttp
from io import BytesIO


class Message(interactions.Extension):
    """An extension dedicated to message context menus."""

    def __init__(self, bot: interactions.Client, **kwargs: dict | None):
        self.bot: interactions.Client = bot
        self.targets: dict | None = {}

    @interactions.extension_message_command(
        name="Create help thread", scope=src.const.METADATA["guild"]
    )
    async def create_help_thread(self, ctx: interactions.CommandContext):
        self.targets[int(ctx.author.id)] = ctx.target

        modal = interactions.Modal(
            custom_id="help_thread_creation",
            title="Create help thread",
            components=[
                interactions.TextInput(
                    style=interactions.TextStyleType.SHORT,
                    custom_id="help_thread_name",
                    label="What should the thread be named?",
                    value=f"[AUTO] Help thread for {ctx.target.author.username}.",
                    required=True,
                    min_length=1,
                    max_length=100,
                ),
                interactions.TextInput(
                    style=interactions.TextStyleType.PARAGRAPH,
                    custom_id="edit_content",
                    label="What should the question be?",
                    value=ctx.target.content,
                    required=True,
                    min_length=1,
                    max_length=4000,
                ),
                interactions.TextInput(
                    style=interactions.TextStyleType.PARAGRAPH,
                    custom_id="extra_content",
                    label="Any additional information",
                    required=False,
                    min_length=1,
                    max_length=1024,
                ),
            ],
        )
        await ctx.popup(modal)

    @interactions.extension_component("TAG_SELECTION")
    async def _help_thread_select(
        self, ctx: interactions.ComponentContext, _selected: list[str]
    ):
        if (
            src.const.METADATA["roles"]["Helper"] not in ctx.author.roles
            and src.const.METADATA["roles"]["Moderator"] not in ctx.author.roles
        ):
            return await ctx.send("missing permissions!", ephemeral=True)
        await self.bot._http.modify_channel(
            channel_id=int(ctx.channel_id), payload={"applied_tags": _selected}
        )
        await ctx.send("Done", ephemeral=True)

    @interactions.extension_modal("help_thread_creation")
    async def _help_thread_modal(
        self,
        ctx: interactions.CommandContext,
        thread_name: str,
        content: str,
        extra_content: str | None = None,
    ):

        target: interactions.Message = self.targets.pop(int(ctx.author.id))

        target._json["content"] = content
        files: list[interactions.File] = []
        if target._json["attachments"]:
            del target._json["attachments"]

            async with aiohttp.ClientSession() as session:
                for attachment in target.attachments:
                    async with session.get(attachment.url) as request:
                        _bytes: bytes = await request.content.read()
                        files.append(interactions.File(attachment.filename, fp=BytesIO(_bytes)))

            target._json["attachments"] = [file._json_payload(_id) for _id, file in enumerate(files)]

        if not "AUTO" in thread_name:
            thread_name = f"[AUTO] {thread_name}"

        _thread: dict = await self.bot._http.create_forum_thread(
            self=self.bot._http,
            auto_archive_duration=1440,
            name=thread_name,
            channel_id=src.const.METADATA["channels"]["help"],
            applied_tags=["996215708595794071"],
            message_payload=target._json,
            files=files,
            reason="Auto help thread creation",
        )

        ch = await interactions.get(
            self.bot,
            interactions.Channel,
            object_id=src.const.METADATA["channels"]["help"],
        )
        _tags = ch._extras["available_tags"]
        _options: list[interactions.SelectOption] = [
            interactions.SelectOption(
                label=tag["name"],
                value=tag["id"],
                emoji=interactions.Emoji(
                    name=tag["emoji_name"],
                )
                if tag["emoji_name"]
                else None,
            )
            for tag in _tags
        ]

        select = interactions.SelectMenu(
            custom_id="TAG_SELECTION",
            placeholder="Select the tags you want",
            options=_options,
            min_values=0,
            max_values=len(_options),
        )

        thread = interactions.Channel(**_thread, _client=self.bot._http)

        await thread.add_member(int(ctx.author.id))
        await thread.add_member(int(target.author.id))

        embed = None

        if extra_content:
            embed = interactions.Embed(
                title="Additional Information:",
                color=0xFEE75C,
                timestamp=target.timestamp,
                description=extra_content,
            )
            embed.set_footer(text="Please create a thread in #help to ask questions!")

        button = interactions.Button(
            style=interactions.ButtonStyle.LINK,
            label="Original message",
            url=target.url,
        )
        close_button = interactions.Button(
            style=interactions.ButtonStyle.DANGER,
            label="Close this thread",
            custom_id="close thread",
        )

        _ars = [
            interactions.ActionRow.new(button),
            interactions.ActionRow.new(select),
            interactions.ActionRow.new(close_button),
        ]

        msg = await thread.send(
            "This help thread was automatically generated. Read the message above for more information.",
            embeds=embed,
            components=_ars,
        )
        await msg.pin()

        await ctx.send(
            f"Hey, {target.author.mention}! At this time, we only help with support-related questions in our help "
            f"channel. Please redirect to {thread.mention} in order to receive help."
        )
        await ctx.send(":white_check_mark: Thread created.", ephemeral=True)

    @interactions.extension_listener
    async def on_thread_create(self, thread: interactions.Thread):

        if (
            thread._extras.get("applied_tags")
            and thread.parent_id == 996211499364262039
            and thread._extras.get("newly_created")
            and "AUTO" not in thread.name
        ):
            msg = await thread.send(
                "Hey! Once your issue is solved, press the button below to close this thread!",
                components=[
                    interactions.Button(
                        style=interactions.ButtonStyle.DANGER,
                        label="Close this thread",
                        custom_id="close thread",
                    )
                ],
            )
            await msg.pin()

    @interactions.extension_component("close thread")
    async def _close_thread(self, ctx: interactions.ComponentContext):
        await ctx.get_channel()
        await ctx.send("Closing! Thank you for using our help system!")
        await ctx.channel.modify(archived=True, locked=True)


def setup(bot, **kwargs):
    Message(bot, **kwargs)
