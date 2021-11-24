docker buildx build \
  --platform linux/amd64 \
  -t $IMAGE \
  --push \
  $BUILD_CONTEXT