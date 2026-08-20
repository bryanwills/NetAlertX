#!/usr/bin/env python

import json
import os
import re
import sys
import requests
from base64 import b64encode

# Register NetAlertX directories
INSTALL_PATH = os.getenv('NETALERTX_APP', '/app')
sys.path.extend([f"{INSTALL_PATH}/server/plugins", f"{INSTALL_PATH}/server"])

import conf  # noqa: E402 [flake8 lint suppression]
from const import confFileName, logPath  # noqa: E402 [flake8 lint suppression]
from plugin_helper import Plugin_Objects, handleEmpty  # noqa: E402 [flake8 lint suppression]
from utils.datetime_utils import timeNowUTC  # noqa: E402 [flake8 lint suppression]
from logger import mylog, Logger  # noqa: E402 [flake8 lint suppression]
from helper import get_setting_value  # noqa: E402 [flake8 lint suppression]
from models.notification_instance import NotificationInstance  # noqa: E402 [flake8 lint suppression]
from database import DB  # noqa: E402 [flake8 lint suppression]
from pytz import timezone  # noqa: E402 [flake8 lint suppression]

# Make sure the TIMEZONE for logging is correct
conf.tz = timezone(get_setting_value('TIMEZONE'))

# Make sure log level is initialized correctly
Logger(get_setting_value('LOG_LEVEL'))

pluginName = 'NTFY'

LOG_PATH = logPath + '/plugins'
RESULT_FILE = os.path.join(LOG_PATH, f'last_result.{pluginName}.log')


def main():

    mylog('verbose', [f'[{pluginName}](publisher) In script'])

    # Check if basic config settings supplied
    if check_config() is False:
        mylog('none', [f'[{pluginName}] ⚠ ERROR: Publisher notification gateway not set up correctly. Check your {confFileName} {pluginName}_* variables.'])
        return

    # Create a database connection
    db = DB()  # instance of class DB
    db.open()

    # Initialize the Plugin obj output file
    plugin_objects = Plugin_Objects(RESULT_FILE)

    # Create a NotificationInstance instance
    notifications = NotificationInstance(db)

    # Retrieve new notifications
    new_notifications = notifications.getNew()

    # Process the new notifications (see the Notifications DB table for structure or check the /php/server/query_json.php?file=table_notifications.json endpoint)
    for notification in new_notifications:

        # Send notification
        response_text, response_status_code = send(notification["HTML"], notification["Text"])

        # Log result
        plugin_objects.add_object(
            primaryId   = pluginName,
            secondaryId = timeNowUTC(),
            watched1    = notification["GUID"],
            watched2    = handleEmpty(response_text),
            watched3    = response_status_code,
            watched4    = 'null',
            extra       = 'null',
            foreignKey  = notification["GUID"]
        )

    plugin_objects.write_result_file()


# -------------------------------------------------------------------------------
def check_config():
    if get_setting_value('NTFY_HOST') == '' or get_setting_value('NTFY_TOPIC') == '':
        return False
    else:
        return True


# -------------------------------------------------------------------------------
def build_custom_headers(entries, reserved_headers):
    """Turn "Name: Value" setting entries into a header dict.

    Entries are skipped when malformed, when the name would clobber a header the
    plugin already set (so ntfy auth stays intact), and when a name repeats.
    Values are never logged, they are usually secrets.
    """

    taken = {name.lower() for name in reserved_headers}
    custom_headers = {}

    for position, entry in enumerate(entries, start=1):
        name, separator, value = entry.partition(':')
        name, value = name.strip(), value.strip()

        if separator == '' or name == '' or value == '':
            mylog('none', [f'[{pluginName}] ⚠ Ignoring custom header #{position}, expected the format "Name: Value".'])
        elif name.lower() in taken:
            mylog('none', [f'[{pluginName}] ⚠ Custom header "{name}" collides with a header that is already set; skipping it.'])
        else:
            taken.add(name.lower())
            custom_headers[name] = value

    return custom_headers


# -------------------------------------------------------------------------------
def send(html, text):

    response_text = ''
    response_status_code = ''

    # settings
    token = get_setting_value('NTFY_TOKEN')
    user = get_setting_value('NTFY_USER')
    pwd = get_setting_value('NTFY_PASSWORD')
    verify_ssl = get_setting_value('NTFY_VERIFY_SSL')
    custom_header_entries = get_setting_value('NTFY_CUSTOM_HEADERS') or []
    # Strip a leading '?' so both "p_token=..." and "?p_token=..." work; requests
    # adds the '?' itself, and a leading one would produce a broken "??" in the URL.
    url_query_string = get_setting_value('NTFY_URL_QUERY_STRING').lstrip('?')

    # prepare request headers
    headers = {
        "Title": "NetAlertX Notification",
        "Actions": "view, Open Dashboard, " + get_setting_value('REPORT_DASHBOARD_URL'),
        "Priority": get_setting_value('NTFY_PRIORITY'),
        "Tags": "warning"
    }

    # if token or username and password are set generate hash and update header
    if token != '':
        headers["Authorization"] = "Bearer {}".format(token)
    elif user != "" and pwd != "":
        # Generate hash for basic auth
        basichash = b64encode(bytes(user + ':' + pwd, "utf-8")).decode("ascii")
        # add authorization header with hash
        headers["Authorization"] = "Basic {}".format(basichash)

    # Optional custom headers, e.g. to authenticate through a reverse proxy / tunnel
    # sitting in front of the ntfy instance. Pangolin needs two of them, which is why
    # this is a list rather than a single name/value pair.
    custom_headers = build_custom_headers(custom_header_entries, headers)
    headers.update(custom_headers)

    # call NTFY service
    try:
        response = requests.post("{}/{}".format(
            get_setting_value('NTFY_HOST'),
            get_setting_value('NTFY_TOPIC')),
            data    = text,
            headers = headers,
            params  = url_query_string if url_query_string != '' else None,
            verify  = verify_ssl,
            timeout = get_setting_value('NTFY_RUN_TIMEOUT')
        )

        response_status_code = response.status_code

        # Check if the request was successful (status code 200)
        if response_status_code == 200:
            response_text = response.text  # This captures the response body/message
        else:
            response_text = json.dumps(response.text)

    except requests.exceptions.InvalidHeader:
        # requests echoes the offending header value in this exception's message,
        # so the message itself is never logged - it would leak the configured
        # custom header value. Report the problem without quoting the value.
        if custom_headers:
            names = ', '.join(f'"{name}"' for name in custom_headers)
            error_text = (f'Invalid custom header - one of {names} has a name or value containing characters '
                          f'that are not allowed in an HTTP header (e.g. a newline, a leading space, or a '
                          f'non-ASCII character). Check for trailing whitespace on the value.')
        else:
            error_text = ('A request header contains characters that are not allowed in an HTTP header. Check the '
                          'NTFY_* settings for stray newlines or non-ASCII characters.')

        mylog('none', [f'[{pluginName}] ⚠ ERROR: ', error_text])

        response_text = error_text

        return response_text, response_status_code

    except requests.exceptions.RequestException as e:
        # The exception message embeds the request URL, which may include a secret
        # query string (e.g. a proxy token). Redact the query part before it is
        # logged and persisted to the plugin result file / shown in the UI.
        error_text = str(e)
        if url_query_string != '':
            error_text = re.sub(r'(\?)\S+', r'\1<redacted>', error_text)

        mylog('none', [f'[{pluginName}] ⚠ ERROR: ', error_text])

        response_text = error_text

        return response_text, response_status_code

    return response_text, response_status_code


if __name__ == '__main__':
    sys.exit(main())
