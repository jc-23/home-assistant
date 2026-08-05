#!/usr/bin/env bash
set -Eeuo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m'

readonly OWNER="jc-23"
readonly REPO="home-assistant"
readonly BRANCH="main"
readonly ICON_DIRECTORY="icons"

FIRMWARE="auto"
CATEGORY=""
DEVICE_ADDRESS=""
DEVICE_URL=""
USERNAME=""
PASSWORD="${AWTRIX_PASSWORD:-}"
TEMP_DIRECTORY=""
CURL_AUTH=()

usage() {
    cat <<'EOF'
Upload this repository's warning icons to AWTRIX 3 or AWTRIX NG.

Usage:
  upload_icon.sh [options] [HOST_OR_URL]

Options:
  --firmware auto|awtrix3|ng  Firmware generation (default: auto)
  --category NAME            Icon directory to upload without prompting
  --user USERNAME            HTTP Basic Auth username (AWTRIX NG)
  -h, --help                 Show this help

The password is read from AWTRIX_PASSWORD or requested without echo when
--user is present. HOST_OR_URL may be an IP address, hostname, or full URL.
EOF
}

die() {
    printf '%bError:%b %s\n' "$RED" "$NC" "$*" >&2
    exit 1
}

notice() {
    printf '%b%s%b\n' "$GREEN" "$*" "$NC"
}

warn() {
    printf '%b%s%b\n' "$YELLOW" "$*" "$NC" >&2
}

cleanup() {
    if [[ -n "$TEMP_DIRECTORY" && -d "$TEMP_DIRECTORY" ]]; then
        rm -rf -- "$TEMP_DIRECTORY"
    fi
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "'$1' is required."
}

parse_arguments() {
    while (($#)); do
        case "$1" in
            --firmware)
                (($# >= 2)) || die "--firmware requires a value."
                FIRMWARE="$2"
                shift 2
                ;;
            --category)
                (($# >= 2)) || die "--category requires a value."
                CATEGORY="$2"
                shift 2
                ;;
            --user)
                (($# >= 2)) || die "--user requires a value."
                USERNAME="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --)
                shift
                ;;
            -*)
                die "Unknown option: $1"
                ;;
            *)
                [[ -z "$DEVICE_ADDRESS" ]] || die "Only one device address is allowed."
                DEVICE_ADDRESS="$1"
                shift
                ;;
        esac
    done

    case "$FIRMWARE" in
        auto|awtrix3|ng) ;;
        *) die "Firmware must be auto, awtrix3, or ng." ;;
    esac
}

configure_device() {
    if [[ -z "$DEVICE_ADDRESS" ]]; then
        read -rp "AWTRIX host, IP address, or URL: " DEVICE_ADDRESS
    fi
    [[ -n "$DEVICE_ADDRESS" ]] || die "A device address is required."

    case "$DEVICE_ADDRESS" in
        http://*|https://*) DEVICE_URL="${DEVICE_ADDRESS%/}" ;;
        *) DEVICE_URL="http://${DEVICE_ADDRESS%/}" ;;
    esac

    if [[ -n "$USERNAME" ]]; then
        if [[ -z "$PASSWORD" ]]; then
            read -rsp "AWTRIX password: " PASSWORD
            printf '\n'
        fi
        CURL_AUTH=(--user "$USERNAME:$PASSWORD")
    fi
}

github_api() {
    curl --fail --silent --show-error --location \
        --connect-timeout 10 \
        "https://api.github.com/repos/$OWNER/$REPO/contents/$1?ref=$BRANCH"
}

list_icon_directories() {
    github_api "$ICON_DIRECTORY" |
        jq -er '.[] | select(.type == "dir") | .name'
}

list_icons() {
    github_api "$ICON_DIRECTORY/$1" |
        jq -er '.[] | select(.type == "file" and (.name | test("\\.gif$"; "i"))) | .download_url'
}

select_category() {
    local directories=()
    mapfile -t directories < <(list_icon_directories)
    ((${#directories[@]} > 0)) || die "No icon directories were found."

    if [[ -n "$CATEGORY" ]]; then
        local directory
        for directory in "${directories[@]}"; do
            [[ "$directory" == "$CATEGORY" ]] && return
        done
        die "Unknown icon category '$CATEGORY'. Available: ${directories[*]}"
    fi

    notice "Available icon directories:"
    PS3="Select a directory: "
    select CATEGORY in "${directories[@]}"; do
        [[ -n "$CATEGORY" ]] && return
        warn "Invalid selection. Please try again."
    done
}

detect_firmware() {
    [[ "$FIRMWARE" == "auto" ]] || return

    local response_file="$TEMP_DIRECTORY/capabilities.json"
    local http_status
    http_status=$(curl --silent --show-error --location \
        --connect-timeout 5 --max-time 10 \
        "${CURL_AUTH[@]}" \
        --output "$response_file" --write-out '%{http_code}' \
        "$DEVICE_URL/api/v1/capabilities") ||
        die "Cannot reach $DEVICE_URL. Use --firmware if automatic detection is unavailable."

    case "$http_status" in
        200)
            if jq -e 'type == "object" and has("effects")' "$response_file" >/dev/null 2>&1; then
                FIRMWARE="ng"
            else
                FIRMWARE="awtrix3"
            fi
            ;;
        401|403)
            die "AWTRIX rejected authentication. Provide --user and a valid password."
            ;;
        *)
            FIRMWARE="awtrix3"
            ;;
    esac

    notice "Detected firmware: $FIRMWARE"
}

verify_gif() {
    local file_name="$1"
    [[ "$(file -b --mime-type "$file_name")" == "image/gif" ]] ||
        die "Downloaded file '$file_name' is not a GIF."
}

upload_icon() {
    local icon_url="$1"
    local file_name
    local temporary_file
    file_name=$(basename "$icon_url")
    temporary_file="$TEMP_DIRECTORY/$file_name"

    curl --fail --silent --show-error --location \
        --connect-timeout 10 \
        --output "$temporary_file" "$icon_url"
    verify_gif "$temporary_file"

    case "$FIRMWARE" in
        ng)
            curl --fail --silent --show-error \
                "${CURL_AUTH[@]}" \
                --form "file=@$temporary_file;filename=$file_name" \
                "$DEVICE_URL/api/v1/files?dir=/ICONS" >/dev/null
            ;;
        awtrix3)
            curl --fail --silent --show-error \
                --form "file=@$temporary_file;filename=/ICONS/$file_name" \
                "$DEVICE_URL/edit" >/dev/null
            ;;
    esac

    notice "Uploaded icon: $file_name"
}

main() {
    parse_arguments "$@"
    require_command curl
    require_command file
    require_command jq

    TEMP_DIRECTORY=$(mktemp -d)
    trap cleanup EXIT INT TERM

    configure_device
    detect_firmware
    select_category

    local icons=()
    mapfile -t icons < <(list_icons "$CATEGORY")
    ((${#icons[@]} > 0)) || die "No GIF icons found in '$CATEGORY'."

    notice "Uploading ${#icons[@]} icon(s) from '$CATEGORY'..."
    local icon_url
    for icon_url in "${icons[@]}"; do
        upload_icon "$icon_url"
    done
}

main "$@"
