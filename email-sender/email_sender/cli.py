from __future__ import annotations

import json
import re
import smtplib
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

CONFIG_FILENAME = "config.json"
TEMPLATES_DIRNAME = "templates"
REQUIRED_CONFIG_FIELDS = (
    "server_url",
    "server_port",
    "auth_user",
    "auth_password",
    "sender_email",
)
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class EmailSenderError(Exception):
    """Raised when the email sender cannot complete an operation."""


@dataclass(frozen=True)
class Config:
    server_url: str
    server_port: int
    auth_user: str
    auth_password: str
    sender_email: str


def resolve_server_endpoint(config: Config) -> tuple[str, int]:
    server_url = config.server_url.strip()

    if server_url.startswith("["):
        closing_bracket = server_url.find("]")
        if closing_bracket == -1:
            raise EmailSenderError("Invalid server_url format.")
        host = server_url[1:closing_bracket]
        remainder = server_url[closing_bracket + 1 :]
        if not remainder:
            return host, config.server_port
        if not remainder.startswith(":"):
            raise EmailSenderError("Invalid server_url format.")
        try:
            return host, int(remainder[1:])
        except ValueError as exc:
            raise EmailSenderError("Invalid server_url port.") from exc

    if server_url.count(":") == 1:
        host, raw_port = server_url.split(":", 1)
        if raw_port:
            try:
                return host, int(raw_port)
            except ValueError as exc:
                raise EmailSenderError("Invalid server_url port.") from exc

    return server_url, config.server_port


def load_config(base_dir: Path) -> Config:
    config_path = base_dir / CONFIG_FILENAME
    if not config_path.is_file():
        raise EmailSenderError("Missing config.json in the current directory.")

    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EmailSenderError(f"Invalid config.json: {exc.msg}.") from exc

    if not isinstance(raw_config, dict):
        raise EmailSenderError("config.json must contain a JSON object.")

    missing_fields = [
        field
        for field in REQUIRED_CONFIG_FIELDS
        if field not in raw_config or raw_config[field] in ("", None)
    ]
    if missing_fields:
        missing_list = ", ".join(missing_fields)
        raise EmailSenderError(f"Missing required config field(s): {missing_list}.")

    try:
        server_port = int(raw_config["server_port"])
    except (TypeError, ValueError) as exc:
        raise EmailSenderError("server_port must be an integer.") from exc

    if server_port <= 0:
        raise EmailSenderError("server_port must be greater than zero.")

    return Config(
        server_url=str(raw_config["server_url"]),
        server_port=server_port,
        auth_user=str(raw_config["auth_user"]),
        auth_password=str(raw_config["auth_password"]),
        sender_email=str(raw_config["sender_email"]),
    )


def find_template(base_dir: Path, template_name: str) -> Path:
    templates_dir = base_dir / TEMPLATES_DIRNAME
    if not templates_dir.is_dir():
        raise EmailSenderError("Missing templates directory.")

    matches = [
        path
        for path in templates_dir.glob("*.txt")
        if path.stem.lower() == template_name.lower()
    ]
    if not matches:
        raise EmailSenderError(f'Template "{template_name}" was not found.')
    if len(matches) > 1:
        raise EmailSenderError(
            f'Multiple templates match "{template_name}" case-insensitively.'
        )

    return matches[0]


def extract_template_variables(template_text: str) -> list[str]:
    variables: list[str] = []
    seen: set[str] = set()

    for match in PLACEHOLDER_PATTERN.finditer(template_text):
        variable_name = match.group(1)
        if variable_name not in seen:
            seen.add(variable_name)
            variables.append(variable_name)

    return variables


def render_template(template_text: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        variable_name = match.group(1)
        if variable_name not in variables:
            raise EmailSenderError(
                f'Missing value for template variable "{variable_name}".'
            )
        return variables[variable_name]

    return PLACEHOLDER_PATTERN.sub(replace, template_text)


def prompt_non_empty(label: str) -> str:
    while True:
        value = input(label).strip()
        if value:
            return value
        print("Value is required.")


def prompt_recipient_email() -> str:
    while True:
        recipient = prompt_non_empty("Recipient email: ")
        confirmation = prompt_non_empty("Confirm recipient email: ")
        if recipient == confirmation:
            return recipient
        print("Recipient email addresses do not match. Please try again.")


def prompt_template_values(variable_names: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for variable_name in variable_names:
        values[variable_name] = input(f"{variable_name}: ")
    return values


def display_review(
    *,
    sender_email: str,
    recipient_email: str,
    subject: str,
    template_name: str,
    body: str,
) -> None:
    print("\n=== Review Email ===")
    print(f"From: {sender_email}")
    print(f"To: {recipient_email}")
    print(f"Subject: {subject}")
    print(f"Template: {template_name}")
    print("Body:")
    print(body)
    print("====================\n")


def confirm_send() -> None:
    decision = input("Send email? [y/N]: ").strip().lower()
    if decision not in {"y", "yes"}:
        raise EmailSenderError("Email sending cancelled.")


def send_email(config: Config, recipient_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = config.sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        server_host, server_port = resolve_server_endpoint(config)
        with smtplib.SMTP(server_host, server_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.auth_user, config.auth_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailSenderError(f"Failed to send email: {exc}") from exc


def run(base_dir: Path) -> None:
    config = load_config(base_dir)
    recipient_email = prompt_recipient_email()
    subject = prompt_non_empty("Subject: ")
    template_name = prompt_non_empty("Template name: ")
    template_path = find_template(base_dir, template_name)

    template_text = template_path.read_text(encoding="utf-8")
    variable_names = extract_template_variables(template_text)
    variable_values = prompt_template_values(variable_names)
    body = render_template(template_text, variable_values)

    display_review(
        sender_email=config.sender_email,
        recipient_email=recipient_email,
        subject=subject,
        template_name=template_path.stem,
        body=body,
    )
    confirm_send()
    send_email(config, recipient_email, subject, body)


def main() -> int:
    try:
        run(Path.cwd())
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except EmailSenderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Email sent successfully.")
    return 0
