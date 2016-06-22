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

class Chat:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("id")
        self.type = data.get("type")
        self.title = data.get("title")
        self.username = data.get("username")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")

    async def message(self, text):
        await self.bot.api_call("sendMessage", text = text, chat_id = self.id)

    def command(self, command):
        def wrap(handler):
            self.bot.cmd_handlers[self.id, command.lower()] = handler
            return handler
        return wrap

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
            self.cmd, self.cmd_target = cmd_regex.match(text[self.offset + 1:self.end]).group("cmd", "username")

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
        entities = data.get("entities")
        if entities is not None:
            for e in entities:
                e = MessageEntity(bot, e, self.text)
                self.entities.append(e)
                if e.type == "bot_command" and e.offset == 0:
                    if e.cmd_target is None or e.cmd_target.lower() == bot.ownuser.username.lower():
                        self.cmd = e.cmd.lower()

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

class Update:
    def __init__(self, bot, data):
        self.bot = bot
        self.id = data.get("update_id")
        self.message = parse_object(bot, data, "message", Message)
        self.edited_message = parse_object(bot, data, "edited_message", Message)
        self.inline_query = data.get("inline_query")
        self.chosen_inline_result = data.get("chosen_inline_result")
        self.callback_query = data.get("callback_query")

    async def handle(self):
        date = int(time.time())
        if date - self.message.date < 300:
            handler = self.bot.cmd_handlers.get(self.message.cmd,
                    self.bot.cmd_handlers.get((self.message.chat.id, self.message.cmd)))
            if handler is not None:
                await handler(self.message)

class Bot:
    def __init__(self, api_token, polling_timeout = 300):
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop = self.loop)
        self.api_token = api_token
        self.polling_timeout = polling_timeout
        self.polling_offset = 0
        self.cmd_handlers = {}
        self.ownuser = User(self, self.api_call_sync("getMe"))

    def command(self, command):
        def wrap(handler):
            self.cmd_handlers[command.lower()] = handler
            return handler
        return wrap

    async def api_call(self, method, **params):
        print(">>", method)
        url = "https://api.telegram.org/bot{}/{}".format(self.api_token, method)
        async with self.session.post(url, data = params) as r:
            d = await r.json()
            print("<<", method, d)
            if d["ok"]:
                return d["result"]
            else:
                return None

    def api_call_sync(self, method, **params):
        return self.loop.run_until_complete(self.api_call(method, **params))

    def get_chat(self, identifier):
        return self.loop.run_until_complete(self.get_chat_aync(identifier))

    async def get_chat_aync(self, identifier):
        return Chat(self, await self.api_call("getChat", chat_id = identifier))

    async def event_loop(self):
        while True:
            updates = await self.api_call("getUpdates",
                    timeout = self.polling_timeout, offset = self.polling_offset)

            for u in updates:
                u = Update(self, u)
                if u.id >= self.polling_offset:
                    self.polling_offset = u.id + 1

                asyncio.ensure_future(u.handle())


    def run(self):
        try:
            self.loop.run_until_complete(self.event_loop())
        finally:
            self.session.close()
