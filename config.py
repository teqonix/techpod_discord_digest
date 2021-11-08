import secret_store.app_secrets
discord_token = secret_store.app_secrets.discord_token
log_level = 'INFO'

# Bot settings not controlled via conversation (yet):
default_query_days = 9

# Discord Server config:
bot_admin_channel = "bot_log_channel"
excluded_channels = [
    "another_bot_test_channel"
]
bot_admin_role_names = [
    'Bot Admin'
]
# Some people may want to opt out of having their reactions tracked:
tracking_opt_out_roles = [
    'Bot Invisibility'
]

# GCP Config:
gcp_project_id = 'techpod-discord-digest'

# Firestore config:
firestore_admin_collection = 'dev_techpod_discord_digest_bot_admin' # TODO: Add to terraform
monitored_emoji_doc_name = 'MONITORED_EMOJI'
monitored_channels_doc_name = 'MONITORED_CHANNELS'

firestore_storage_collection = 'dev_techpod_discord_digest_bot_storage' # TODO: Add to terraform
message_store_doc_name = 'messages'
message_store_reaction_collection_name = 'reacted_to'

message_created_at_field = u'created_at_datetime'