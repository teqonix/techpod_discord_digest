import secret_store.app_secrets
discord_token = secret_store.app_secrets.discord_token

log_level = 'INFO'

# Discord Server config:
bot_admin_channel = "bot_log_channel"
excluded_channels = [
    "another_bot_test_channel"
]
bot_admin_role_names = [
    'Bot Admin'
]

# GCP Config:
gcp_project_id = 'techpod-discord-digest'

# Firestore config:
firestore_admin_collection = 'techpod_discord_digest_bot_admin' # TODO: Add to terraform
monitored_emoji_doc_name = 'MONITORED_EMOJI'
monitored_channels_doc_name = 'MONITORED_CHANNELS'

firestore_storage_collection = 'techpod_discord_digest_bot_storage' # TODO: Add to terraform
