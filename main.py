import discord
import json
import logging
from datetime import datetime
import config

CLIENT = discord.Client()
LOGGER = logging.getLogger()

CHANNEL_LIST = list()
ADMIN_CHANNEL = None

@CLIENT.event
async def on_ready():
    logging.info(f'We have logged in as {CLIENT.user}')
    all_channels_generator = CLIENT.get_all_channels()

    raw_all_channels = list()
    for c in all_channels_generator:
        raw_all_channels.append(c)
    
    for channel in raw_all_channels:
        if channel.name not in config.excluded_channels and channel.type.name == 'text':
            CHANNEL_LIST.append(channel)
            if channel.name == config.bot_admin_channel:
                ADMIN_CHANNEL = channel

    await ADMIN_CHANNEL.send(f'Techpod Discord Digest bot is ready as of {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC and monitoring text channels {[c.name for c in CHANNEL_LIST]}.')

    print('Bot Ready.')

@CLIENT.event
async def on_message(message):
    if message.author == CLIENT.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
    
    if message.content.startswith('!test'):
        logging.info('debugging!')
        logging.info('no really I would like to debug')

@CLIENT.event
async def on_raw_reaction_add(payload):
    logging.debug(f"saw a reaction added: {payload}")
    if payload.channel_id in [c.id for c in CHANNEL_LIST]:
        logging.info(f"Reaction {payload.emoji.name} was used on message {payload.message_id} in channel {payload.channel_id} by member {payload.member.name}.")

if __name__ == "__main__":
    logging.basicConfig(level=config.log_level)
    CLIENT.run(config.discord_token)