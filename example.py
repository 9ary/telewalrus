#!/usr/bin/env python3

import bot

mybot = bot.Bot("<API token>")

# Global command that works in every chat the bot is in
@mybot.command("hello")
async def kick(message):
    await message.chat.message("Hello world!")

# Chat-specific command
mychat = mybot.get_chat(some_chat_id)
@mychat.command("boop")
async def lose(message):
    await message.chat.message("Boop!")

mybot.run()
