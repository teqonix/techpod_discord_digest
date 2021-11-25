docker buildx build \
  --platform linux/amd64 \
  -t $IMAGE \
  --build-arg application_credentials=/usr/local/digest_bot/secret_store/techpod-discord-digest-0d66139b52b6.json \
  --push \
  $BUILD_CONTEXT