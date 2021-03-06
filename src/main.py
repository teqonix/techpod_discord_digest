import bot_actions
import discord
import json
import logging
import firestore_client
from datetime import datetime
import asyncio

import config
import conversation

# TODO List:
# - Need to add mocking and unit testing
# - Code review from a real programmer (I am not an Object Oriented developer - this code will make someone barf)
# - Add emojii monitoring logic (add/remove)
# - Add query capability & output message + formatting
# - Add versioning to all data schemas - if this changes over time it would be good to keep for conversion purposes
# - Refactor code to use classes instead of dictionaries everywhere for object properties

DB_CLIENT = firestore_client.DigestBotFirestoreClient(gcp_credentials_env_var='GOOGLE_APPLICATION_CREDENTIALS')
BOT_ADMIN = bot_actions.TechPodBotClient(DB_CLIENT)
DISCORD_CLIENT = BOT_ADMIN.DISCORD_CLIENT
ACTIVE_CONVERSATIONS = dict()
LOGGER = logging.getLogger()

@DISCORD_CLIENT.event
async def on_ready():
    logging.info(f'We have logged in as {DISCORD_CLIENT.user}')
    await BOT_ADMIN.initialize_bot()
    print('Bot Ready.')

@DISCORD_CLIENT.event
async def on_message(message):
    if message.author == DISCORD_CLIENT.user:
        return

    # Ignore messages in channels not being monitored
    if message.channel.id not in [i.id for i in BOT_ADMIN.CHANNEL_LIST]:
        return

    for opt_out_role in config.tracking_opt_out_roles:
        # Ignore messages from users that have opted out:
        if opt_out_role in [i.name for i in message.author.roles]:
            return     

    if message.author in ACTIVE_CONVERSATIONS:
        convo = ACTIVE_CONVERSATIONS[message.author]
        convo.conversation_message_list.append(message)
        # If the user has requested to cancel their operation, delete the conversation:
        if message.content.startswith('$cancel') or message.content.startswith('$clear'):
            if convo.conversation_stage == 'add_categories':
                await message.channel.send(f'You are in the middle of adding a reaction so we cannot cancel right now!')
                return
            else:
                await message.channel.send(f'Cancelling your request to {ACTIVE_CONVERSATIONS[message.author].command}.')
                ACTIVE_CONVERSATIONS[message.author].conversation_stage = 'complete'
                
        if convo.conversation_stage == 'complete':
            del ACTIVE_CONVERSATIONS[message.author]
        elif convo.command == "$add_reactions":
            await convo.add_reaction_handler(message=message)
        elif convo.command == "$remove_reactions":
            await convo.remove_reaction_handler(message=message)
        elif convo.command == "$add_channels":
            await convo.add_channel_handler(message=message)
        elif convo.command == "$remove_channels":
            await convo.remove_channel_handler(message=message)

    if message.content.startswith('$'):
        # TODO? Might be good to turn this into a helper function
        for admin_role in config.bot_admin_role_names:
            # Ignore any messsage that looks like a bot command if the user does not have a bot admin role:
            if admin_role not in [i.name for i in message.author.roles]:
                return       

        if message.content.startswith('$status'):
            current_status = BOT_ADMIN._get_bot_status_text()
            new_line = '\n'
            await message.channel.send(f'Hey {message.author.display_name}, the current Discord Digest Bot status is: {new_line}'\
                f'{new_line}{current_status["channel_status"]}'\
                f'{current_status["emoji_status"]}'
            )

        if message.content.startswith('$add_channels'):
            if message.author in ACTIVE_CONVERSATIONS:
                pass
            else:
                ACTIVE_CONVERSATIONS[message.author] = conversation.Conversation(owner=message.author, command='$add_channels', db_client=DB_CLIENT, bot_admin=BOT_ADMIN)
                await message.channel.send(f'Hey {message.author.display_name}. What channels would you like to start monitoring?')
                logging.info(f'Started a conversation for command for adding channels: {ACTIVE_CONVERSATIONS[message.author]}')

        if message.content.startswith('$remove_channels'):
            if message.author in ACTIVE_CONVERSATIONS:
                pass
            else:
                ACTIVE_CONVERSATIONS[message.author] = conversation.Conversation(owner=message.author, command='$remove_channels', db_client=DB_CLIENT, bot_admin=BOT_ADMIN)
                await message.channel.send(f'Hey {message.author.display_name}. What channels would you like to me to stop monitoring?')
                logging.info(f'Started a conversation for command for removing channels: {ACTIVE_CONVERSATIONS[message.author]}')

        if message.content.startswith('$add_reactions'):
            if message.author in ACTIVE_CONVERSATIONS:
                pass
            else:
                ACTIVE_CONVERSATIONS[message.author] = conversation.Conversation(owner=message.author, command='$add_reactions', db_client=DB_CLIENT, bot_admin=BOT_ADMIN)
                await message.channel.send(f'Hey {message.author.display_name}. What reaction would you like to start tracking?')
                logging.info(f'Started a conversation for command for adding reactions: {ACTIVE_CONVERSATIONS[message.author]}')
            
        if message.content.startswith('$remove_reactions'):
            if message.author in ACTIVE_CONVERSATIONS:
                pass
            else:
                ACTIVE_CONVERSATIONS[message.author] = conversation.Conversation(owner=message.author, command='$remove_reactions', db_client=DB_CLIENT, bot_admin=BOT_ADMIN)
                await message.channel.send(f'Hey {message.author.display_name}. What reactions would you like to stop tracking? Pick from these: { [i["discord_output_str"] for i in DB_CLIENT.monitored_emoji["emoji_list"]] }')
                logging.info(f'Started a conversation for command for removing reactions: {ACTIVE_CONVERSATIONS[message.author]}')
        
        if message.content.startswith('$query'):
            if message.author in ACTIVE_CONVERSATIONS:
                pass
            else:
                ACTIVE_CONVERSATIONS[message.author] = conversation.Conversation(owner=message.author, command='$query', db_client=DB_CLIENT, bot_admin=BOT_ADMIN)
                await message.channel.send(f'Hol up, {message.author.display_name} - I`m fetching reactions to posts within the past {config.default_query_days} days for your community digest report..')
                async with message.channel.typing():
                    await asyncio.sleep(1)
                    await BOT_ADMIN.run_digest_query(message=message)
                ACTIVE_CONVERSATIONS[message.author].conversation_stage = 'complete'

    if message.content.startswith('!test'):
        logging.info('debugging!')
        DB_CLIENT.get_reacted_messages_for_timespan()

@DISCORD_CLIENT.event
async def on_raw_reaction_add(payload):
    logging.debug(f"saw a reaction added: {payload}")
    if payload.channel_id in [c.id for c in BOT_ADMIN.CHANNEL_LIST]:
        if str(payload.emoji) in [i['discord_output_str'] for i in DB_CLIENT.monitored_emoji['emoji_list']]:
            logging.info(f"Reaction {payload.emoji.name} was used on message {payload.message_id} in channel {payload.channel_id} by member {payload.member.name}.")
            try:
                channel_ref = BOT_ADMIN.get_channel_reference(channel_id=payload.channel_id)
                message_ref = await channel_ref.fetch_message(id=payload.message_id)
                # member_reg = channel_ref.guild.
                # If a user has opted out of tracking, do not continue processing their reaction:
                # TODO: Probably turn this into a helper function somewhere else
                for opt_out_role in config.tracking_opt_out_roles:
                    if opt_out_role in [i.name for i in message_ref.author.roles]:
                        return
            except Exception as e:
                logging.error(f'Could not fetch channel reference with id {payload.channel_id} or message reference with id {payload.message_id}')
                raise Exception
            DB_CLIENT.store_raw_message(message_ref)

if __name__ == "__main__":
    logging.basicConfig(level=config.log_level)
    DISCORD_CLIENT.run(config.discord_token)