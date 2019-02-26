from configparser import ConfigParser
from datetime import datetime
import argparse
import email.message
import email.parser
import imaplib
import logging
import re
import smtplib
import ssl
import sys
import time
import uuid


log = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname)-5.5s %(message)s'

HEADER = re.compile(': *')
SSL_CONTEXT = ssl.create_default_context()
EMAIL_PARSER = email.parser.BytesParser()

CONFIG = {}


def main():
    global CONFIG
    parser = argparse.ArgumentParser()
    parser.add_argument('configfile', help='path to config file')
    options = parser.parse_args()
    config = ConfigParser()
    config.read(options.configfile)
    CONFIG = config['default']
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT,
                        level=CONFIG.get('loglevel', 'WARNING'))

    msg = create_message()
    try:
        send(msg)
    except Exception:
        log.warning('SMTP error, aborting', exc_info=True)
        return 1

    waited = 0
    interval = int(CONFIG.get('poll_interval', 10))
    timeout = int(CONFIG.get('poll_timeout', 60))
    while waited < timeout:
        time.sleep(interval)
        waited += interval
        try:
            if check_received(msg['X-Mailcheck-Token']):
                return 0
        except Exception:
            log.warning('IMAP error, aborting', exc_info=True)
            return 1
        log.info('IMAP not found, retrying in %s', interval)
    log.info('IMAP not found after %s, giving up', timeout)
    return 2


def create_message():
    msg = email.message.Message()
    msg['To'] = CONFIG['recipient']
    msg['From'] = CONFIG.get('from', CONFIG['recipient'])
    msg['Date'] = datetime.now().strftime(
        '%a, %d %b %Y %H:%M:%S +0000')
    msg['X-Mailcheck-Token'] = str(uuid.uuid4())
    msg.set_payload(
        'Sent by mail-check-roundtrip with token: %s\n\n'
        'See <https://pypi.python.org/pypi/ws.mailcheck>' %
        msg['X-Mailcheck-Token'])
    for line in CONFIG.get('headers', '').split('\n'):
        line = line.strip()
        try:
            key, value = HEADER.split(line)
        except Exception:
            continue
        msg[key] = value
    return msg


def send(msg):
    host, port = CONFIG.get('smtp_host', 'localhost:25').split(':')
    use_ssl = CONFIG.get('smtp_ssl', 'starttls')
    if use_ssl == 'ssl':
        log.debug('SMTP connect to %s:%s with SSL', host, port)
        smtp = smtplib.SMTP_SSL(host, port, context=SSL_CONTEXT)
    else:
        smtp = smtplib.SMTP(host, port)
        if use_ssl == 'starttls':
            log.debug('SMTP connect to %s:%s with STARTTLS', host, port)
            smtp.starttls(context=SSL_CONTEXT)
        else:
            log.debug('SMTP connect to %s:%s', host, port)

    if CONFIG.get('smtp_username'):
        log.debug('SMTP login as %s', CONFIG['smtp_username'])
        smtp.login(CONFIG['smtp_username'], CONFIG['smtp_password'])
    log.info('SMTP send email from %s to %s (token %s)',
             msg['From'], msg['To'], msg['X-Mailcheck-Token'])
    smtp.sendmail(msg['To'], [msg['To']], msg.as_string())
    smtp.quit()


def check_received(token):
    host, port = CONFIG.get('imap_host', 'localhost:143').split(':')
    use_ssl = CONFIG.get('imap_ssl', 'starttls')
    if use_ssl == 'ssl':
        log.debug('IMAP connect to %s:%s with SSL', host, port)
        imap = imaplib.IMAP4_SSL(host, port, context=SSL_CONTEXT)
    else:
        imap = imaplib.IMAP4(host, port)
        if use_ssl == 'starttls':
            imap.starttls(ssl_context=SSL_CONTEXT)
            log.debug('IMAP connect to %s:%s with STARTTLS', host, port)
        else:
            log.debug('IMAP connect to %s:%s', host, port)

    log.debug('IMAP login as %s', CONFIG['imap_username'])
    imap.login(CONFIG['imap_username'], CONFIG['imap_password'])
    folder = CONFIG.get('imap_folder', 'INBOX')
    log.debug('IMAP select folder %s', folder)
    ok, count = imap.select(folder)
    if ok != 'OK' or not count:
        return False
    ok, data = imap.search(None, 'TO', CONFIG['recipient'])
    if ok != 'OK':
        return False

    found = False
    message_numbers = data[0].split()
    for num in message_numbers:
        ok, data = imap.fetch(num, '(RFC822)')
        if ok != 'OK':
            continue
        msg = EMAIL_PARSER.parsebytes(data[0][1], headersonly=True)
        log.debug('IMAP looking at %s from %s to %s',
                  msg['Message-ID'], msg['From'], msg['To'])

        if msg['X-Mailcheck-Token'] == token:
            found = True
            if CONFIG.get('poll_delete', 'true') == 'true':
                log.info('IMAP found token %s, deleting message', token)
                imap.store(num, '+FLAGS', r'\Deleted')
                imap.expunge()
            else:
                log.info('IMAP found token %s', token)
            break

    imap.logout()
    return found


if __name__ == '__main__':
    main()
