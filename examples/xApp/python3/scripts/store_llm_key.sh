#!/usr/bin/env bash
# Store an API key for an OpenAI-compatible LLM endpoint in ~/.config/appweaver/<name>.env (mode 600),
# wired for the portal's "vllm" provider. The key is read from stdin (hidden prompt on a terminal),
# never passed on the command line, never echoed.
#
#   scripts/store_llm_key.sh aalto                       # Aalto LLM gateway, GLM-5.3-Flash (defaults)
#   scripts/store_llm_key.sh <name> <base_url> <model>   # any other endpoint
#
# From another machine (e.g. a Mac holding the key), over SSH:
#   ssh -t dang@<linux-host> flexric/examples/xApp/python3/scripts/store_llm_key.sh aalto
# or pipe it without a prompt:
#   printf '%s' "$AALTO_KEY" | ssh dang@<linux-host> flexric/examples/xApp/python3/scripts/store_llm_key.sh aalto
#
# Use it with:  . ~/.config/appweaver/aalto.env && python scripts/check_llm_provider.py
set -euo pipefail
name="${1:?usage: store_llm_key.sh <name> [base_url] [model]}"
case "$name" in *[!A-Za-z0-9_-]*) echo "name must be [A-Za-z0-9_-]" >&2; exit 2;; esac
if [[ "$name" == "aalto" ]]; then
  base="${2:-https://llm-gateway.k8s.aalto.fi/api/v1}"
  model="${3:-zai-org/GLM-5.3-Flash}"
else
  base="${2:?base_url required}"; model="${3:?model required}"
fi
if [[ -t 0 ]]; then
  read -rs -p "API key for ${name} (${base}): " key; echo >&2
else
  IFS= read -r key || true
fi
key="${key//[$'\r\n\t ']/}"
[[ -n "$key" ]] || { echo "empty key, nothing written" >&2; exit 1; }
case "$key" in *\'*|*\\*|*\"*|*\$*|*\`*) echo "key has quote or shell characters, nothing written" >&2; exit 1;; esac
dir="$HOME/.config/appweaver"; out="$dir/${name}.env"
umask 077; mkdir -p "$dir"; chmod 700 "$dir"
tmp="$(mktemp "$dir/.${name}.XXXXXX")"
var="$(printf '%s' "$name" | tr 'a-z-' 'A-Z_')_API_KEY"
{
  echo "# ${name}: ${base} (written $(date -Iseconds) by store_llm_key.sh)"
  echo "export ${var}='${key}'"
  echo "# Portal/harness wiring (provider \"vllm\" = any OpenAI-compatible server)"
  echo "export LLM_PROVIDER=vllm"
  echo "export VLLM_BASE_URL='${base}'"
  echo "export VLLM_MODEL='${model}'"
  echo "export VLLM_API_KEY=\"\$${var}\""
} > "$tmp"
chmod 600 "$tmp"; mv -f "$tmp" "$out"
echo "wrote $out (mode 600, key length ${#key}, model ${model})" >&2
