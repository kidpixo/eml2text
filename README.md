# eml2text

A command-line tool for extracting plain text from an EML email file. Reads the body of an `.eml` file and prints it as plain text, markdown, or HTML.

## Requirements

Python 3.10+.

## Installation

This project has zero external dependencies — only Python standard library. Any of these methods works:

### pipx (recommended)

Installs in an isolated environment and exposes the `eml2text` command:

```
pipx install .
```

### pip

Equivalent here since there are no dependencies to isolate:

```
pip install .
```

Then use `eml2text` from the command line.

### Standalone file

Download [`eml2text.py`](eml2text.py) — a single self-contained Python file. Run it directly:

```
python eml2text.py email_file.eml
```

## Usage

### Single file

```
eml2text email_file.eml
```

Outputs the message headers (Date, From, To, Subject) and body to stdout.

### Folder mode

Pass a directory to process all `.eml` files inside:

```
eml2text emails/
```

By default, `.txt` files are written to the same directory. Use `-o` to write to a different output folder:

```
eml2text -o converted/ emails/
```

### Options

- `-p, --progress` — show a progress bar when processing multiple files in folder mode
- `-m, --markdown` — format output as markdown (bold headers)
- `-h, --html` — format output as HTML
- `-o FILE, --output FILE|DIR` — write output to a file (single mode) or directory (folder mode). In folder mode the extension is set automatically (`.txt`, `.md`, or `.html`)
- `--help` — show help message and exit

### Examples

```
eml2text email.eml
eml2text --progress emails/
eml2text --markdown email.eml
eml2text --html email.eml
eml2text -m -o out.md email.eml
eml2text --output out/ emails/
eml2text --progress -o out/ emails/
```

## Features

- **Thunderbird/mbox support**: Thunderbird's "Save As" exports mbox-format files (starting with `>From `). eml2text detects this and extracts the first message automatically.
- **HTML body conversion**: When the email contains an HTML part, it is converted to formatted plain text with proper list indentation, paragraph breaks, and bold/italic styling.
- **Nested lists**: Lists and sub-lists are rendered with `* ` markers at the correct indentation level.

### License

**eml2text** is licensed under the MIT license, copyright 2024 Erik Ben Heckman <erik@heckman.ca>.

The testing fixtures are taken from a repository belonging to Mikel Lindsaar at <https://github.com/mikel/mail>. It is copyright 2009-2016 Mikel Lindsaar and is also shared under the MIT license.

Note: for this repo I'm trying out licensing tools from [REUSE](https://reuse.software/).
