#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf '%s\n' \
    'Usage: TAG=v1.0.0 ./start.sh [start|stop|remove|upgrade] [--debug] [--dry-run]' \
    '' \
    'Manage the image-based deployment.' \
    '' \
    'Commands:' \
    '  start    Pull required images, then start services. Default command.' \
    '  stop     Stop compose services and backend runtime containers.' \
    '  remove   Remove compose services and backend runtime containers.' \
    '  upgrade  Pull required images, stop runtime containers, then recreate services.' \
    '' \
    'Options:' \
    '  --debug    Include compose.deploy.debug.yml and the debug profile.' \
    '  --dry-run  Print commands without running them.' \
    '  -h, --help Show this help.' \
    '' \
    'Environment variables:' \
    '  TAG                           Image tag to deploy, default: latest' \
    '  EXTRA_BACKEND_RUNTIME_IMAGES  Extra whitespace-separated images to pull'
}

COMMAND="start"
DEBUG=0
DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    start|stop|remove|upgrade)
      COMMAND="$1"
      shift
      ;;
    --debug)
      DEBUG=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
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

COMPOSE_ARGS=(-f compose.yml -f compose.swr.yml)
if [[ "$DEBUG" -eq 1 ]]; then
  COMPOSE_ARGS+=(-f compose.deploy.debug.yml --profile debug)
fi

RUNTIME_IMAGES=()
DYNAMIC_CONTAINER_PREFIXES=()

add_runtime_image() {
  local image="$1"
  local existing

  [[ -n "$image" ]] || return 0
  for existing in "${RUNTIME_IMAGES[@]}"; do
    [[ "$existing" == "$image" ]] && return 0
  done
  RUNTIME_IMAGES+=("$image")
}

add_dynamic_container_prefix() {
  local prefix="$1"
  local existing

  [[ -n "$prefix" ]] || return 0
  for existing in "${DYNAMIC_CONTAINER_PREFIXES[@]}"; do
    [[ "$existing" == "$prefix" ]] && return 0
  done
  DYNAMIC_CONTAINER_PREFIXES+=("$prefix")
}

discover_backend_runtime_images() {
  local constants_file="../src/backend/app/core/constants.py"
  local line image prefix

  [[ -f "$constants_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^[[:space:]]*[A-Z0-9_]*IMAGE[[:space:]]*=[[:space:]]*\"([^\"]+)\" ]]; then
      image="${BASH_REMATCH[1]}"
      add_runtime_image "$image"
    elif [[ "$line" =~ ^[[:space:]]*[A-Z0-9_]*IMAGE[[:space:]]*=[[:space:]]*\'([^\']+)\' ]]; then
      image="${BASH_REMATCH[1]}"
      add_runtime_image "$image"
    elif [[ "$line" =~ ^[[:space:]]*[A-Z0-9_]*CONTAINER_NAME_PREFIX[[:space:]]*=[[:space:]]*\"([^\"]+)\" ]]; then
      prefix="${BASH_REMATCH[1]}"
      add_dynamic_container_prefix "$prefix"
    elif [[ "$line" =~ ^[[:space:]]*[A-Z0-9_]*CONTAINER_NAME_PREFIX[[:space:]]*=[[:space:]]*\'([^\']+)\' ]]; then
      prefix="${BASH_REMATCH[1]}"
      add_dynamic_container_prefix "$prefix"
    fi
  done < "$constants_file"
  add_dynamic_container_prefix "code_user-"
}

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

pull_required_images() {
  printf 'Image tag: %s\n' "${TAG:-latest}"
  printf 'Compose service images used by this deployment:\n'
  run docker compose "${COMPOSE_ARGS[@]}" config --images

  printf '\nPulling compose service images...\n'
  run docker compose "${COMPOSE_ARGS[@]}" pull

  if [[ "${#RUNTIME_IMAGES[@]}" -gt 0 ]]; then
    printf '\nPulling backend runtime images...\n'
    for image in "${RUNTIME_IMAGES[@]}"; do
      run docker pull "$image"
    done
  fi
}

dynamic_container_ids() {
  local prefix="$1"
  docker ps -aq --filter "name=^/${prefix}"
}

running_dynamic_container_ids() {
  local prefix="$1"
  docker ps -q --filter "name=^/${prefix}"
}

stop_dynamic_containers() {
  local prefix ids=()

  if [[ "${#DYNAMIC_CONTAINER_PREFIXES[@]}" -eq 0 ]]; then
    return 0
  fi

  printf '\nStopping backend runtime containers...\n'
  for prefix in "${DYNAMIC_CONTAINER_PREFIXES[@]}"; do
    if [[ "$DRY_RUN" -eq 1 ]]; then
      run docker stop "\$(docker ps -q --filter name=^/${prefix})"
      continue
    fi

    mapfile -t ids < <(running_dynamic_container_ids "$prefix")
    if [[ "${#ids[@]}" -gt 0 ]]; then
      run docker stop "${ids[@]}"
    fi
  done
}

remove_dynamic_containers() {
  local prefix ids=()

  if [[ "${#DYNAMIC_CONTAINER_PREFIXES[@]}" -eq 0 ]]; then
    return 0
  fi

  printf '\nRemoving backend runtime containers...\n'
  for prefix in "${DYNAMIC_CONTAINER_PREFIXES[@]}"; do
    if [[ "$DRY_RUN" -eq 1 ]]; then
      run docker rm -f "\$(docker ps -aq --filter name=^/${prefix})"
      continue
    fi

    mapfile -t ids < <(dynamic_container_ids "$prefix")
    if [[ "${#ids[@]}" -gt 0 ]]; then
      run docker rm -f "${ids[@]}"
    fi
  done
}

start_services() {
  pull_required_images
  printf '\nStarting services...\n'
  run docker compose "${COMPOSE_ARGS[@]}" up -d
}

stop_services() {
  printf '\nStopping compose services...\n'
  run docker compose "${COMPOSE_ARGS[@]}" stop
  stop_dynamic_containers
}

remove_services() {
  printf '\nRemoving compose services...\n'
  run docker compose "${COMPOSE_ARGS[@]}" down --remove-orphans
  remove_dynamic_containers
}

upgrade_services() {
  pull_required_images
  printf '\nStopping compose services...\n'
  run docker compose "${COMPOSE_ARGS[@]}" stop
  stop_dynamic_containers
  printf '\nRecreating services...\n'
  run docker compose "${COMPOSE_ARGS[@]}" up -d --remove-orphans
}

discover_backend_runtime_images
if [[ -n "${EXTRA_BACKEND_RUNTIME_IMAGES:-}" ]]; then
  for image in ${EXTRA_BACKEND_RUNTIME_IMAGES}; do
    add_runtime_image "$image"
  done
fi

case "$COMMAND" in
  start)
    start_services
    ;;
  stop)
    stop_services
    ;;
  remove)
    remove_services
    ;;
  upgrade)
    upgrade_services
    ;;
esac
