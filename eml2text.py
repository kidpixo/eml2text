#!/usr/bin/env python3
# Copyright 2023 Erik Ben Heckman <erik@heckman.ca>
# https://git.heckman.ca/eml2text   SPDX-License-Identifier: MIT


"""eml2text - Extract plain text from an EML email file.

Standalone single-file version. Run directly:

    python eml2text.py email_file.eml
    python eml2text.py --progress emails/
    python eml2text.py --markdown --output out.md email.eml
"""

import re
import mailbox
import tempfile
import glob
import os
from html.parser import HTMLParser
from email import policy, message_from_file, message_from_string
import getopt
from sys import argv, exit, stderr, stdout


class _HtmlToText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []
        self._list_depth = 0
        self._skip_depth = 0
        self._in_pre = False
        self._in_b = False
        self._in_i = False
        self._last_block = False
        self._just_li = False

    def handle_starttag(self, tag, attrs):
        if self._skip_depth > 0:
            return
        if tag == 'pre':
            self._in_pre = True
        if tag in ('p', 'div'):
            if self._parts and not self._parts[-1].endswith('\n'):
                if not self._just_li:
                    self._parts.append('\n\n')
            elif not self._just_li:
                self._parts.append('\n')
            self._last_block = True
        if tag == 'br':
            if self._parts and not self._parts[-1].endswith('\n'):
                self._parts.append('\n')
            self._last_block = True
        if tag == 'hr':
            self._parts.append('\n---\n\n')
            self._last_block = True
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._parts.append('\n\n')
            self._last_block = True
        if tag == 'blockquote':
            self._parts.append('> ')
            self._last_block = False
        if tag == 'li':
            indent = max(0, self._list_depth - 1)
            self._parts.append('  ' * indent + '* ')
            self._last_block = False
            self._just_li = True
        if tag in ('ul', 'ol'):
            if self._parts and not self._parts[-1].endswith('\n'):
                self._parts.append('\n')
            self._list_depth += 1
        if tag == 'table':
            self._skip_depth += 1
        if tag == 'b' or tag == 'strong':
            self._in_b = True
        if tag == 'i' or tag == 'em':
            self._in_i = True

    def handle_endtag(self, tag):
        if self._skip_depth > 0:
            if tag == 'table':
                self._skip_depth -= 1
            return
        if tag == 'pre':
            self._in_pre = False
        if tag == 'blockquote':
            self._parts.append('\n\n')
            self._last_block = True
        if tag in ('ul', 'ol'):
            self._list_depth = max(0, self._list_depth - 1)
            if not self._parts[-1].endswith('\n'):
                self._parts.append('\n')
        if tag == 'li':
            self._parts.append('\n')
            self._last_block = True
            self._just_li = False
        if tag in ('p', 'div') and not self._last_block:
            self._parts.append('\n')
            self._last_block = True
        if tag == 'b' or tag == 'strong':
            self._in_b = False
        if tag == 'i' or tag == 'em':
            self._in_i = False

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_pre:
            self._parts.append(data)
            self._last_block = False
            return
        if not data or not data.strip():
            return
        text = data
        if self._in_b and self._parts and not self._parts[-1].endswith((' ', '\n')):
            self._parts.append(' ')
        if self._in_i and self._parts and not self._parts[-1].endswith((' ', '\n')):
            self._parts.append(' ')
        self._parts.append(text)
        self._last_block = False

    def result(self):
        text = ''.join(self._parts)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def _html_to_text(html):
    parser = _HtmlToText()
    parser.feed(html)
    parser.close()
    return parser.result()


_HTML_TAG_RE = re.compile(r'<[^>]+>')


def _strip_html(text):
    return _HTML_TAG_RE.sub('', text)


def _get_body(message):
    html = message.get_body(preferencelist=('html',))
    if html:
        return _html_to_text(html.get_content())
    plain = message.get_body(preferencelist=('plain',))
    if plain:
        return plain.get_content()
    return ""


def _get_header(message, name):
    value = message.get(name)
    if value:
        return value
    for part in message.walk():
        if part is message:
            continue
        value = part.get(name)
        if value:
            return value
    return "N/A"


def _format_output(message, markdown, html):
    date_hdr = _get_header(message, "Date")
    from_hdr = _get_header(message, "From")
    to_hdr = _get_header(message, "To")
    subject_hdr = _get_header(message, "Subject")
    body = _get_body(message)

    if html:
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{subject_hdr}</title></head>
<body>
<pre><strong>Date:</strong> {date_hdr}
<strong>From:</strong> {from_hdr}
<strong>To:</strong> {to_hdr}
<strong>Subject:</strong> {subject_hdr}

{body}</pre>
</body>
</html>"""
    elif markdown:
        return f"""**Date:** {date_hdr}
**From:** {from_hdr}
**To:** {to_hdr}
**Subject:** {subject_hdr}

{body}"""
    else:
        return f"""Date: {date_hdr}
From: {from_hdr}
To: {to_hdr}
Subject: {subject_hdr}

{body}"""


def _output_ext(html, markdown):
    if html:
        return ".html"
    if markdown:
        return ".md"
    return ".txt"


def _print_progress(current, total, path):
    name = os.path.basename(path)
    if len(name) > 40:
        name = name[:37] + "..."
    print(f"\rProcessing {current}/{total}: {name}", end="", file=stderr)


def main():
    output_file = None
    markdown = False
    html = False
    progress = False

    try:
        opts, args = getopt.getopt(argv[1:], "hpmo:", ["help", "progress", "markdown", "html", "output="])
    except getopt.GetoptError:
        print(F"Usage: python eml2text.py [--progress] [--markdown] [--html] [--output FILE|DIR] <EML_FILE|DIR>", file=stderr)
        exit(1)

    for opt, arg in opts:
        if opt in ("--help",):
            print(F"""Usage: python eml2text.py [--progress] [--markdown] [--html] [--output FILE|DIR] <EML_FILE|DIR>

Options:
  -p, --progress    Show a progress bar when processing multiple files.
  -m, --markdown    Format output as markdown (bold headers).
  -h, --html        Format output as HTML.
  -o FILE, --output FILE|DIR   Write output to FILE (single mode) or
                    DIR (folder mode, auto-named with .txt/.md/.html).
  --help            Show this help message and exit.

Examples:
  python eml2text.py email.eml
  python eml2text.py --markdown email.eml
  python eml2text.py --html email.eml
  python eml2text.py -m -o out.md email.eml
  python eml2text.py --output out/ emails/
  python eml2text.py --progress emails/""")
            exit(0)
        elif opt in ("-p", "--progress"):
            progress = True
        elif opt in ("-m", "--markdown"):
            markdown = True
        elif opt in ("-h", "--html"):
            html = True
        elif opt in ("-o", "--output"):
            output_file = arg

    if not args:
        print(F"Usage: python eml2text.py [--progress] [--markdown] [--html] [--output FILE|DIR] <EML_FILE|DIR>", file=stderr)
        exit(1)

    def _open_message(path):
        with open(path) as fp:
            first = fp.readline()
        if first.startswith(">From "):
            with open(path) as fp:
                content = fp.read()
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mbox', delete=False) as tmp:
                tmp.write(content.replace(">From ", "From ", 1))
                tmp.flush()
                mbox = mailbox.mbox(tmp.name)
                msgs = list(mbox)
                mbox.close()
            if not msgs:
                print("No messages found in mbox file", file=stderr)
                exit(1)
            raw = msgs[0].as_string()
            return message_from_string(raw, policy=policy.default)
        with open(path) as fp:
            return message_from_file(fp, policy=policy.default)

    input_path = args[0]

    def _process_one(path):
        message = _open_message(path)
        return _format_output(message, markdown, html)

    if os.path.isdir(input_path):
        eml_files = sorted(glob.glob(os.path.join(input_path, '*.eml')))
        if not eml_files:
            print("No .eml files found in directory", file=stderr)
            exit(1)
        out_dir = output_file if output_file else input_path
        if not os.path.isdir(out_dir):
            print(f"Output directory '{out_dir}' does not exist, creating it.", file=stderr)
            os.makedirs(out_dir, exist_ok=True)
        ext = _output_ext(html, markdown)
        total = len(eml_files)
        for i, eml_path in enumerate(eml_files, 1):
            if progress:
                _print_progress(i, total, eml_path)
            out = _process_one(eml_path)
            base = os.path.splitext(os.path.basename(eml_path))[0]
            out_path = os.path.join(out_dir, base + ext)
            with open(out_path, 'w') as f:
                f.write(out)
        if progress:
            print("", file=stderr)
    else:
        try:
            out = _process_one(input_path)
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(out)
            else:
                print(out, file=stdout)
        except OSError as e:
            print(f"Unable to open {input_path}", file=stderr)
            exit(1)


if __name__ == '__main__':
    main()
