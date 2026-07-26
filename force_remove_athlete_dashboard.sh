#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="athlete-dashboard"
# SERVICE_NAME="sports-mongo"

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ docker is not installed or not in PATH"
  exit 1
fi

container_id="$(docker ps -a --filter "name=^/${SERVICE_NAME}$" --format '{{.ID}}' | head -n 1)"

if [[ -z "${container_id}" ]]; then
  echo "ℹ️ No container found with name '${SERVICE_NAME}'."
  echo "ℹ️ Running compose cleanup anyway..."
  docker-compose down --remove-orphans || true
  exit 0
fi

echo "🔎 Found container: ${container_id} (${SERVICE_NAME})"

state="$(docker inspect --format '{{.State.Status}}' "${container_id}")"
echo "📦 Current state: ${state}"

if [[ "${state}" == "running" ]]; then
  echo "🛠️ Disabling restart policy..."
  docker update --restart=no "${SERVICE_NAME}" >/dev/null

  echo "🛠️ Trying in-container shutdown (kill PID 1)..."
  docker exec "${SERVICE_NAME}" sh -lc 'kill 1' >/dev/null 2>&1 || true

  sleep 1

  new_state="$(docker inspect --format '{{.State.Status}}' "${container_id}" 2>/dev/null || echo "missing")"
  echo "📦 State after internal kill: ${new_state}"

  if [[ "${new_state}" == "running" ]]; then
    echo "⚠️ Container still running. Trying docker rm -f..."
    docker rm -f "${container_id}" >/dev/null 2>&1 || true
  fi
else
  echo "🧹 Container not running, removing directly..."
  docker rm "${container_id}" >/dev/null 2>&1 || true
fi

if docker ps -a --filter "id=${container_id}" --format '{{.ID}}' | grep -q .; then
  echo "⚠️ Container still exists. Manual fallback:"
  echo "  docker inspect --format '{{.State.Pid}}' ${container_id}"
  echo "  sudo kill -9 <pid>"
  echo "  docker rm -f ${container_id}"
else
  echo "✅ Container removed: ${container_id}"
fi

echo "🧼 Running compose cleanup..."
docker-compose down --remove-orphans || true

echo "✅ Cleanup completed."
