#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf '%s\n' \
    'Usage: ./push-swr-images.sh [--dry-run]' \
    '' \
    'Tag the locally built latest images with a release version and push them:' \
    '  - backend image from DOCKER_IMAGE_BACKEND:SOURCE_TAG' \
    '  - frontend image from DOCKER_IMAGE_FRONTEND:SOURCE_TAG' \
    '  - task runner image from llm4ad-task-runner:SOURCE_TAG' \
    '' \
    'Public images in compose.yml, such as postgres, redis, nginx, adminer,' \
    'mailcatcher and rustfs, are intentionally not retagged or pushed.' \
    '' \
    'Environment variables:' \
    '  ENV_FILE                 Compose env file, default: .env' \
    '  SWR_REGISTRY             Default: registry.cn-hangzhou.aliyuncs.com/noah2012' \
    '  SWR_IMAGE_BACKEND        Default: basename of DOCKER_IMAGE_BACKEND' \
    '  SWR_IMAGE_FRONTEND       Default: basename of DOCKER_IMAGE_FRONTEND' \
    '  SWR_IMAGE_TASK_RUNNER    Default: llm4ad-task-runner' \
    '  SOURCE_TAG               Local image tag to release, default: latest' \
    '  TASK_RUNNER_LOCAL_IMAGE  Default: llm4ad-task-runner:${SOURCE_TAG}' \
    '  TAG                      Release tag to push, default: latest'
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR="${BASH_SOURCE[0]}"
if [[ "$SCRIPT_DIR" == */* ]]; then
  SCRIPT_DIR="${SCRIPT_DIR%/*}"
else
  SCRIPT_DIR="."
fi
cd "$SCRIPT_DIR"

ENV_FILE="${ENV_FILE:-.env}"

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  REPLY="$value"
}

read_env_value() {
  local key="$1"
  local line value

  [[ -f "$ENV_FILE" ]] || return 1
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    trim "$line"
    line="$REPLY"
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
    line="${line#export }"
    [[ "$line" == "$key="* || "$line" == "$key ="* ]] || continue

    value="${line#*=}"
    trim "$value"
    value="$REPLY"
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    REPLY="$value"
    return 0
  done < "$ENV_FILE"
  return 1
}

load_env_default() {
  local key="$1"
  if [[ -z "${!key+x}" ]] && read_env_value "$key"; then
    printf -v "$key" '%s' "$REPLY"
  fi
}

load_env_default TAG
load_env_default DOCKER_IMAGE_BACKEND
load_env_default DOCKER_IMAGE_FRONTEND
load_env_default SWR_REGISTRY
load_env_default SWR_IMAGE_BACKEND
load_env_default SWR_IMAGE_FRONTEND
load_env_default SWR_IMAGE_TASK_RUNNER
load_env_default SOURCE_TAG
load_env_default TASK_RUNNER_LOCAL_IMAGE

TAG="${TAG:-latest}"
SOURCE_TAG="${SOURCE_TAG:-latest}"
SWR_REGISTRY="${SWR_REGISTRY:-registry.cn-hangzhou.aliyuncs.com/noah2012}"
DOCKER_IMAGE_BACKEND="${DOCKER_IMAGE_BACKEND:-backend}"
DOCKER_IMAGE_FRONTEND="${DOCKER_IMAGE_FRONTEND:-frontend}"
TASK_RUNNER_LOCAL_IMAGE="${TASK_RUNNER_LOCAL_IMAGE:-llm4ad-task-runner:${SOURCE_TAG}}"

image_repo_name() {
  local image="$1"
  image="${image%@*}"
  local last="${image##*/}"
  if [[ "$last" == *:* ]]; then
    last="${last%%:*}"
  fi
  REPLY="$last"
}

if [[ -z "${SWR_IMAGE_BACKEND:-}" ]]; then
  image_repo_name "$DOCKER_IMAGE_BACKEND"
  SWR_IMAGE_BACKEND="$REPLY"
fi
if [[ -z "${SWR_IMAGE_FRONTEND:-}" ]]; then
  image_repo_name "$DOCKER_IMAGE_FRONTEND"
  SWR_IMAGE_FRONTEND="$REPLY"
fi
SWR_IMAGE_TASK_RUNNER="${SWR_IMAGE_TASK_RUNNER:-llm4ad-task-runner}"

LOCAL_BACKEND="${DOCKER_IMAGE_BACKEND}:${SOURCE_TAG}"
LOCAL_FRONTEND="${DOCKER_IMAGE_FRONTEND}:${SOURCE_TAG}"
TARGET_BACKEND="${SWR_REGISTRY%/}/${SWR_IMAGE_BACKEND}:${TAG}"
TARGET_FRONTEND="${SWR_REGISTRY%/}/${SWR_IMAGE_FRONTEND}:${TAG}"
TARGET_TASK_RUNNER="${SWR_REGISTRY%/}/${SWR_IMAGE_TASK_RUNNER}:${TAG}"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

push_image() {
  local local_image="$1"
  local target_image="$2"

  if [[ "$DRY_RUN" -eq 0 ]] && ! docker image inspect "$local_image" >/dev/null 2>&1; then
    printf 'Local image not found: %s\n' "$local_image" >&2
    printf 'Build the latest image first from this directory, for example:\n' >&2
    printf '  docker compose -f compose.yml -f compose.deploy.debug.yml --profile debug up -d --build\n' >&2
    exit 1
  fi

  echo "Tagging $local_image -> $target_image"
  run docker tag "$local_image" "$target_image"
  echo "Pushing $target_image"
  run docker push "$target_image"
}

printf 'Image registry: %s\n' "$SWR_REGISTRY"
printf 'Source tag:     %s\n' "$SOURCE_TAG"
printf 'Release tag:    %s\n' "$TAG"
printf '\nImages to push:\n'
printf '  %s -> %s\n' "$LOCAL_BACKEND" "$TARGET_BACKEND"
printf '  %s -> %s\n' "$LOCAL_FRONTEND" "$TARGET_FRONTEND"
printf '  %s -> %s\n' "$TASK_RUNNER_LOCAL_IMAGE" "$TARGET_TASK_RUNNER"

push_image "$LOCAL_BACKEND" "$TARGET_BACKEND"
push_image "$LOCAL_FRONTEND" "$TARGET_FRONTEND"
push_image "$TASK_RUNNER_LOCAL_IMAGE" "$TARGET_TASK_RUNNER"

printf '\nDone.\n'
printf 'Start after pulling images:\n'
printf '  TAG=%q ./start.sh\n' "$TAG"
