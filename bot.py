import aiohttp
import asyncio
import re
import time

def parse_object(bot, data, key, otype):
    d = data.get(key)
    if d is not None:
        d = otype(bot, d)
    return d

class User:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("id")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.username = data.get("username")

class ChatMember:
    def __init__(self, bot, data):
        self.user = parse_object(bot, data, "user", User)
        self.status = data.get("status")
        self.until_date = data.get("until_date")
        self.can_be_edited = data.get("can_be_edited")
        self.can_change_info = data.get("can_change_info")
        self.can_post_messages = data.get("can_post_messages")
        self.can_edit_messages = data.get("can_edit_messages")
        self.can_delete_messages = data.get("can_delete_messages")
        self.can_invite_users = data.get("can_invite_users")
        self.can_restrict_members = data.get("can_restrict_members")
        self.can_pin_messages = data.get("can_pin_messages")
        self.can_promote_members = data.get("can_promote_members")
        self.can_send_messages = data.get("can_send_messages")
        self.can_send_media_messages = data.get("can_send_media_messages")
        self.can_send_other_messages = data.get("can_send_other_messages")
        self.can_add_web_page_previews = data.get("can_add_web_page_previews")

class Chat:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("id")
        self.type = data.get("type")
        self.title = data.get("title")
        self.username = data.get("username")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")

    async def message(self, text, **kwargs):
        await self.bot.api_call("sendMessage", text = text, chat_id = self.id, **kwargs)

    async def administrators(self):
        data = await self.bot.api_call("getChatAdministrators", chat_id = self.id)
        return [ChatMember(self.bot, member) for member in data]

    def command(self, command):
        def wrap(handler):
            self.bot.cmd_handlers[self.id, command.lower()] = handler
            return handler
        return wrap

    def any(self, handler):
        self.bot.any_handlers[self.id] = handler
        return handler

cmd_regex = re.compile(r"^(?P<cmd>\w+)(|@(?P<username>\w+))$")
class MessageEntity:
    def __init__(self, bot, data, text):
        self.type = data.get("type")
        self.offset = data.get("offset")
        self.length = data.get("length")
        self.end = self.offset + self.length
        self.url = data.get("url")
        self.user = parse_object(bot, data, "user", User)
        if self.type == "bot_command":
            match = cmd_regex.match(text[self.offset + 1:self.end])
            if match is not None:
                self.cmd, self.cmd_target = match.group("cmd", "username")

class Message:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("message_id")
        self.from_user = parse_object(bot, data, "from", User)
        self.date = data.get("date")
        self.chat = parse_object(bot, data, "chat", Chat)
        self.forward_from = parse_object(bot, data, "forward_from", User)
        self.forward_from_chat = parse_object(bot, data, "forward_from_chat", Chat)
        self.forward_date = data.get("forward_date")
        self.reply_to_message = parse_object(bot, data, "reply_to_message", Message)
        self.edit_date = data.get("edit_date")
        self.text = data.get("text")

        self.entities = []
        self.cmd = None
        self.args = None
        entities = data.get("entities")
        if entities is not None:
            for e in entities:
                e = MessageEntity(bot, e, self.text)
                self.entities.append(e)
                if e.type == "bot_command" and e.offset == 0:
                    if e.cmd_target is None or e.cmd_target.lower() == bot.ownuser.username.lower():
                        self.cmd = e.cmd.lower()
                        self.args = self.text[e.end + 1:]

        self.audio = data.get("audio")
        self.document = data.get("document")
        self.photo = data.get("photo")
        self.sticker = data.get("sticker")
        self.video = data.get("video")
        self.voice = data.get("voice")
        self.caption = data.get("caption")
        self.contact = data.get("contact")
        self.location = data.get("location")
        self.venue = data.get("venue")
        self.new_chat_member = parse_object(bot, data, "new_chat_member", User)
        self.left_chat_member = parse_object(bot, data, "left_chat_member", User)
        self.new_chat_title = data.get("new_chat_title")
        self.new_chat_photo = data.get("new_chat_photo")
        self.delete_chat_photo = data.get("delete_chat_photo")
        self.group_chat_created = data.get("group_chat_created")
        self.supergroup_chat_created = data.get("supergroup_chat_created")
        self.channel_chat_created = data.get("channel_chat_created")
        self.migrate_to_chat_id = data.get("migrate_to_chat_id")
        self.migrate_from_chat_id = data.get("migrate_from_chat_id")
        self.pinned_message = parse_object(bot, data, "pinned_message", Message)

    async def edit(self, text, **kwargs):
        await self.bot.api_call("editMessageText", message_id = self.id, text = text, chat_id = self.chat.id, **kwargs)

    async def delete(self):
        await self.bot.api_call("deleteMessage", chat_id = self.chat.id, message_id = self.id)

class CallbackQuery:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("id")
        self.from_user = parse_object(bot, data, "from", User)
        self.message = parse_object(bot, data, "message", Message)
        self.chat_instance = data.get("chat_instance")
        self.data = data.get("data")

    async def answer(self, **kwargs):
        await self.bot.api_call("answerCallbackQuery", callback_query_id = self.id, **kwargs)

class InlineQuery:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("id")
        self.from_user = parse_object(bot, data, "from", User)
        self.location = data.get("location")
        self.query = data.get("query")
        self.offset = data.get("offset")

class Update:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("update_id")
        self.message = parse_object(bot, data, "message", Message)
        self.edited_message = parse_object(bot, data, "edited_message", Message)
        self.inline_query = parse_object(bot, data, "inline_query", InlineQuery)
        self.chosen_inline_result = data.get("chosen_inline_result")
        self.callback_query = parse_object(bot, data, "callback_query", CallbackQuery)

    async def handle(self):
        date = int(time.time())
        if self.message is not None:
            if date - self.message.date < 300:
                handler = self.bot.cmd_handlers.get((self.message.chat.id, self.message.cmd),
                        self.bot.cmd_handlers.get(self.message.cmd,
                        self.bot.any_handlers.get(self.message.chat.id,
                        self.bot.any_handlers.get("any"))))
                if handler is not None:
                    await handler(self.message)

        elif self.inline_query is not None:
            await self.bot.inline_query_handler(self.inline_query)

        elif self.callback_query is not None:
            await self.bot.callback_query_handler(self.callback_query)

class Bot:
    def __init__(self, api_token, polling_timeout = 10):
        self.api_token = api_token
        self.polling_timeout = polling_timeout
        self.polling_offset = 0
        self.cmd_handlers = {}
        self.any_handlers = {}
        self.inline_query_handler = None
        self.callback_query_handler = None
        self.ownuser = User(self, self.api_call_sync("getMe"))

    def command(self, command):
        def wrap(handler):
            self.cmd_handlers[command.lower()] = handler
            return handler
        return wrap

    def any(self, handler):
        self.any_handlers["any"] = handler
        return handler

    def inline_query(self, handler):
        self.inline_query_handler = handler
        return handler

    def callback(self, handler):
        self.callback_query_handler = handler
        return handler

    async def api_call(self, method, **params):
        #print(">>", method)
        url = "https://api.telegram.org/bot{}/{}".format(self.api_token, method)
        async with self.session.post(url, data = params) as r:
            d = await r.json()
            #print("<<", method, d)
            if d["ok"]:
                return d["result"]
            else:
                return None

    def api_call_sync(self, method, **params):
        async def inner():
            async with aiohttp.ClientSession() as session:
                self.session = session
                return await self.api_call(method, **params)
        return asyncio.run(inner())

    def get_chat(self, identifier):
        async def inner():
            async with aiohttp.ClientSession() as session:
                self.session = session
                return await self.get_chat_aync(identifier)
        return asyncio.run(inner())

    async def get_chat_aync(self, identifier):
        return Chat(self, await self.api_call("getChat", chat_id = identifier))

    async def event_loop(self):
        max_retry_interval = 600
        backoff_steps = 10
        update_failures = 0
        while True:
            if update_failures > 0:
                update_failures = min(update_failures, backoff_steps)
                await asyncio.sleep(
                    max_retry_interval ** (update_failures / backoff_steps),
                )
            update_failures += 1

            try:
                updates = await self.api_call("getUpdates",
                        timeout = self.polling_timeout, offset = self.polling_offset)
                if updates is None:
                    continue
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue

            update_failures = 0
            for u in updates:
                u = Update(self, u)
                if u.id >= self.polling_offset:
                    self.polling_offset = u.id + 1

                f = asyncio.create_task(u.handle())

    async def run_async(self):
        async with aiohttp.ClientSession() as session:
            self.session = session
            return await self.event_loop()

    def run(self):
        return asyncio.run(self.run_async())
