import os
import base64
from flask import jsonify, request
from logger import mylog, Logger
from helper import get_setting_value
from utils.datetime_utils import timeNowUTC
from messaging.in_app import write_notification

INSTALL_PATH = os.getenv("NETALERTX_APP", "/app")

# Make sure log level is initialized correctly
lggr = Logger(get_setting_value('LOG_LEVEL'))


def handle_sync_get():
    """Handle GET requests for SYNC (NODE → HUB)."""

    # get all dwevices from the api endpoint
    api_path = os.environ.get('NETALERTX_API', '/tmp/api')

    file_path = f"/{api_path}/table_devices.json"

    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
    except FileNotFoundError:
        msg = f"[Plugin: SYNC] Data file not found: {file_path}"
        write_notification(msg, "alert", timeNowUTC())
        mylog("verbose", [msg])
        return jsonify({"error": msg}), 500

    response_data = base64.b64encode(raw_data).decode("utf-8")

    message = "[Plugin: SYNC] Data sent"
    mylog('verbose', [message])
    if lggr.isAbove('verbose'):
        write_notification(message, 'info', timeNowUTC())

    return jsonify({
        "node_name": get_setting_value("SYNC_node_name"),
        "status": 200,
        "message": "OK",
        "data_base64": response_data,
        "timestamp": timeNowUTC()
    }), 200


def handle_sync_post():
    """Handle POST requests for SYNC (HUB receiving from NODE)."""

    mylog("verbose", [
        "[SYNC API] ENTER handle_sync_post",
        f"method={request.method}",
        f"content_type={request.content_type}",
        f"content_length={request.content_length}",
        f"remote_addr={request.remote_addr}"
    ])

    # ---- RAW BODY (critical for debugging encoding / encryption issues)
    try:
        raw = request.get_data(cache=False)
        mylog("verbose", [
            f"[SYNC API] raw_bytes_len={len(raw)}",
            f"[SYNC API] raw_preview={raw[:200]}"
        ])
    except Exception as e:
        mylog("none", [f"[SYNC API] FAILED reading raw body: {e}"])
        return jsonify({"error": "failed reading body"}), 400

    # ---- JSON PARSE (this is a very common failure point)
    try:
        body = request.get_json(force=False, silent=False)
        mylog("verbose", [f"[SYNC API] parsed_json={body}"])
    except Exception as e:
        mylog("none", [f"[SYNC API] JSON_PARSE_FAILED={e}"])
        return jsonify({"error": "invalid json"}), 400

    # ---- EXTRACT FIELDS
    data = body.get("data", "")
    node_name = body.get("node_name", "")
    plugin = body.get("plugin", "")

    mylog("verbose", [
        f"[SYNC API] node_name={repr(node_name)}",
        f"[SYNC API] plugin={repr(plugin)}",
        f"[SYNC API] data_type={type(data).__name__}",
        f"[SYNC API] data_len={len(data) if isinstance(data, str) else 'non-string'}"
    ])

    storage_path = INSTALL_PATH + "/log/plugins"

    try:
        os.makedirs(storage_path, exist_ok=True)
        mylog("verbose", [f"[SYNC API] storage_path_ready={storage_path}"])
    except Exception as e:
        mylog("none", [f"[SYNC API] MKDIR_FAILED={e}"])
        return jsonify({"error": "storage path error"}), 500

    # ---- FILE COUNT LOGIC
    try:
        encoded_files = [
            f for f in os.listdir(storage_path)
            if f.startswith(f"last_result.{plugin}.encoded.{node_name}")
        ]
        decoded_files = [
            f for f in os.listdir(storage_path)
            if f.startswith(f"last_result.{plugin}.decoded.{node_name}")
        ]
        file_count = len(encoded_files + decoded_files) + 1

        mylog("verbose", [
            f"[SYNC API] encoded_files={len(encoded_files)}",
            f"[SYNC API] decoded_files={len(decoded_files)}",
            f"[SYNC API] file_count={file_count}"
        ])
    except Exception as e:
        mylog("none", [f"[SYNC API] LISTDIR_FAILED={e}"])
        return jsonify({"error": "listdir failed"}), 500

    # ---- FILE PATH
    file_path_new = os.path.join(
        storage_path,
        f"last_result.{plugin}.encoded.{node_name}.{file_count}.log"
    )

    mylog("verbose", [f"[SYNC API] file_path_new={file_path_new}"])

    # ---- WRITE FILE (final critical point)
    try:
        if not isinstance(data, str):
            data = str(data)

        with open(file_path_new, "w") as f:
            f.write(data)

    except Exception as e:
        import traceback
        mylog("none", [
            f"[SYNC API] WRITE_FAILED={e}",
            traceback.format_exc()
        ])
        return jsonify({"error": str(e)}), 500

    msg = f"[Plugin: SYNC] Data received ({file_path_new})"
    write_notification(msg, "info", timeNowUTC())
    mylog("verbose", [msg])

    return jsonify({"message": "Data received and stored successfully"}), 200
