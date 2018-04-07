=============================
SMTP and IMAP roundtrip check
=============================

This packages sends a test email via SMTP, and checks that it was received via
IMAP. Requires Python 3.x, since the stdlib in 2.x is missing too many features
in this area.


Usage
=====

Create a configuration file::

    [default]
    recipient = test@example.com
    smtp_host = smtp.example.com:25
    imap_host = imap.example.com:143
    imap_username = test@example.com
    imap_password = secret

Now run ``mail-check-roundtrip example.conf``. It will send a message with a
random string in the ``X-Mailcheck-Token`` header, and then poll until
``receive_timeout`` to see if a message with that string was rececived (this
message is then deleted). The exit status is 0 if sucessful, 1 on errors (e.g.
connection failed) and 2 if the message could not be found.


Options
=======

The following configuration options are supported and these are their defaults::

    [default]
    recipient = # REQUIRED
    from = # defaults to recipient
    headers = # default empty
        Subject: This is a test
        X-Custom-Header: one

    smtp_host = localhost:25
    smtp_ssl = starttls  # or `ssl` or `none` (not recommended)
    smtp_username =
    smtp_password =

    imap_host = localhost:143
    imap_ssl = starttls  # or `ssl` or `none` (not recommended).
    imap_username = # REQUIRED
    imap_password = # REQUIRED
    imap_folder = INBOX

    poll_timeout = 60
    poll_interval = 10
    poll_delete = true  # Delete the message after it was found
    loglevel = WARNING  # This means no output for a successful run.
