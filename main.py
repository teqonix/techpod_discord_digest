import discord
import json
import logging
from datetime import datetime

import firestore_client
import config

DISCORD_CLIENT = discord.Client()
LOGGER = logging.getLogger()

CHANNEL_LIST = list()
ADMIN_CHANNEL = None
DB_CLIENT = None

@DISCORD_CLIENT.event
async def on_ready():
    logging.info(f'We have logged in as {DISCORD_CLIENT.user}')
    all_channels_generator = DISCORD_CLIENT.get_all_channels()

    raw_all_channels = list()
    for c in all_channels_generator:
        raw_all_channels.append(c)
    
    DB_CLIENT = firestore_client.DigestBotFirestoreClient(gcp_credentials_env_var='GOOGLE_APPLICATION_CREDENTIALS')

    for channel in raw_all_channels:
        if channel.name not in config.excluded_channels and channel.type.name == 'text':
            CHANNEL_LIST.append(channel)
            if channel.name == config.bot_admin_channel:
                ADMIN_CHANNEL = channel

    local_server_emoji_metadata = list()
    for emoji in DB_CLIENT.monitored_emoji['emoji_list']:
        # This bot is currently hard-coded to only connect to one Discord Server, hence the [0]:
        for server_emojii in DISCORD_CLIENT.guilds[0].emojis:
            if emoji['name'] == server_emojii.name:
                already_added = 1
                local_server_emoji_metadata.append({'name': emoji['name'], 'id': str(server_emojii.id), 'category': emoji['category']})
        # Unicode emoji will not exist in the DISCORD_CLIENT listing of emojis, so if we didn't add the emoji being processed then add it now: 
        if already_added == 1:
            already_added = 0
            continue
        else:
            already_added = 0
            local_server_emoji_metadata.append({'name': emoji['name'], 'id': '', 'category': emoji['category']})              
    
    new_line = "\n"
    channel_string = '**Channels Being Monitored:**'
    for channel in DB_CLIENT.monitored_channels['channels']:
        channel_string = channel_string + " \n • #" + channel

    emoji_string = f'{new_line}{new_line}**Emoji Being Monitored:**'
    for emoji in local_server_emoji_metadata:
        if emoji['id'] != '': emoji_string = emoji_string + ' \n • <:' + emoji['name'] + ':' + emoji['id'] + '> (Category: ' + emoji['category'] + ')' 
        if emoji['id'] == '': emoji_string = emoji_string + " \n • " + emoji['name'] + ' (Category: ' + emoji['category'] + ')' 

    await ADMIN_CHANNEL.send(f'Techpod Discord Digest bot is ready as of '\
        f'{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC ' \
        f'{new_line}{new_line} {channel_string}'\
        f'{emoji_string}'
    )

    print('Bot Ready.')

@DISCORD_CLIENT.event
async def on_message(message):
    if message.author == DISCORD_CLIENT.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
    
    if message.content.startswith('!test'):
        logging.info('debugging!')
        logging.info('no really I would like to debug')

@DISCORD_CLIENT.event
async def on_raw_reaction_add(payload):
    logging.debug(f"saw a reaction added: {payload}")
    if payload.channel_id in [c.id for c in CHANNEL_LIST]:
        logging.info(f"Reaction {payload.emoji.name} was used on message {payload.message_id} in channel {payload.channel_id} by member {payload.member.name}.")

if __name__ == "__main__":
    logging.basicConfig(level=config.log_level)
    DISCORD_CLIENT.run(config.discord_token)