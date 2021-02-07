# plainMail2HTML - Convert a text/plain Email to plain+HTML Email.
#
# Copyright (C) 2016 Amit Ramon <amit.ramon@riseup.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""MessageProcessor - an Email message processing class

A class for Email processing: HTML component creation, attaching
components to a single Email object.

"""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from plain2html.core.message_utils import convert_text_to_alternative, clone_header


class MessageTypeError(Exception):
    """Specific exception class"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class MessageProcessor(object):
    """Class for processing Email objects"""

    def __init__(self, html_parser=None, allow_8bit=False):
        """Initialize the instance.
        """
        self.preferred_charset = 'utf-8'
        self.html_parser = html_parser
        self.allow_8bit = allow_8bit

    def generate_html_msg_from_file(self, fp):
        """Load Email from file and add to it HTML component"""

        msg = email.message_from_file(fp)
        if msg.is_multipart():
            html_msg = self._add_html_to_multipart(msg)
        else:
            html_msg = self._add_html_to_plain(msg)

        return html_msg

    def _create_plain_message(self, msg):
        """Create a text/plain new message"""
        # Create a new text/plain message and copy to it the content
        # of the original message 'as is'
        text_msg = MIMEText("")
        text_msg.set_payload(msg.get_payload())
        clone_header('Content-Type', msg, text_msg)
        clone_header('Content-Transfer-Encoding', msg, text_msg)

        return text_msg

    def _create_html_message(self, msg):
        """Parse and convert text to HTML"""

        charset = msg.get_content_charset()
        text = msg.get_payload()

        html_str = self.html_parser(text)

        if self.allow_8bit:
            # this is probably a hack, but no sure how 8bit encoded
            # messages should be created
            html_msg = MIMEText("", 'html')
            html_msg.set_payload(html_str)
            html_msg.set_charset(charset)
            if charset != "us-ascii":
                html_msg.replace_header('Content-Transfer-Encoding', '8bit')
        else:
            # payload will probably be base64 encoded
            html_msg = MIMEText(html_str, 'html', charset)

        return html_msg

    def _add_html_to_plain(self, msg):
        """Add HTML component to a text/plain Email"""

        # sanity check
        if msg.is_multipart() or msg.get_content_type() != 'text/plain':
            raise MessageTypeError('Expected text/plain, but got %s.' %
                                   msg.get_content_type())

        # create a new multipart/alternative message that will contain
        # the plain and HTML components
        new_msg = convert_text_to_alternative(msg)

        text_part = self._create_plain_message(msg)
        html_part = self._create_html_message(msg)

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message,
        # in this case the HTML message, is best and preferred.
        new_msg.attach(text_part)
        new_msg.attach(html_part)

        return new_msg

    # It is assumed that msg is generated by Mutt, with a known
    # structure: it is multipart/mixed, and the first component is a
    # text/plain message. The first component is replaced by a
    # multipart/alternative message that contains the original first
    # component (text) and a HTML version of it.

    def _add_html_to_multipart(self, msg):
        """Add HTML component to a multipart/alternative Email"""

        # sanity check
        if not msg.is_multipart():
            raise MessageTypeError('Expected multipart/alternative, but got %s.' %
                                   msg.get_content_type())

        # TODO: assert msg is multipart-mix, first part is text-plain
        text_part = msg.get_payload()[0]  # text msg is first in list
        if text_part.get_content_type() != 'text/plain':
            raise MessageTypeError('Expected component 1 to be '
                                   'text/plain, but got %s.' %
                                   msg.get_content_type())

        # extract the text body
        # content_charset = text_part.get_content_charset()
        # text = text_part.get_payload(decode=True).decode(content_charset)
        html_part = self._create_html_message(text_part)

        alt_msg = MIMEMultipart('alternative')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message,
        # in this case the HTML message, is best and preferred.
        alt_msg.attach(text_part)
        alt_msg.attach(html_part)
        msg.get_payload()[0] = alt_msg

        return msg
