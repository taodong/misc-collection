import io
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_sender.cli import (
    Config,
    EmailSenderError,
    extract_template_variables,
    find_template,
    load_config,
    main,
    render_template,
    resolve_server_endpoint,
)


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class EmailSenderCliTests(unittest.TestCase):
    def test_load_config_requires_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(
                EmailSenderError, "Missing config.json in the current directory."
            ):
                load_config(Path(tmpdir))

    def test_find_template_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_dir = Path(tmpdir) / "templates"
            templates_dir.mkdir()
            template_path = templates_dir / "Hello.txt"
            template_path.write_text("Hello {{name}}", encoding="utf-8")

            resolved = find_template(Path(tmpdir), "hello")

            self.assertEqual(resolved, template_path)

    def test_template_rendering_reuses_values(self):
        template = "Hello {{name}}, your user is {{name}}."

        variables = extract_template_variables(template)
        rendered = render_template(template, {"name": "Alice"})

        self.assertEqual(variables, ["name"])
        self.assertEqual(rendered, "Hello Alice, your user is Alice.")

    def test_server_url_can_include_port(self):
        config = Config(
            server_url="localhost:9587",
            server_port=465,
            auth_user="myuser",
            auth_password="mypassword",
            sender_email="noreply@example.com",
        )

        self.assertEqual(resolve_server_endpoint(config), ("localhost", 9587))

    def test_main_sends_email_with_rendered_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "templates").mkdir()
            (base_dir / "templates" / "Welcome.txt").write_text(
                "Hello {{name}},\nYour code is {{code}}.\n",
                encoding="utf-8",
            )
            (base_dir / "config.json").write_text(
                json.dumps(
                    {
                        "server_url": "localhost:465",
                        "server_port": 9999,
                        "auth_user": "myuser",
                        "auth_password": "mypassword",
                        "sender_email": "noreply@example.com",
                    }
                ),
                encoding="utf-8",
            )

            smtp_client = MagicMock()
            smtp_context = MagicMock()
            smtp_context.__enter__.return_value = smtp_client

            with working_directory(base_dir), patch(
                "builtins.input",
                side_effect=[
                    "test@example.com",
                    "test@example.com",
                    "Greetings",
                    "welcome",
                    "Alice",
                    "123456",
                    "y",
                ],
            ), patch(
                "email_sender.cli.smtplib.SMTP",
                return_value=smtp_context,
            ) as smtp_client_factory, patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout, patch(
                "sys.stderr", new_callable=io.StringIO
            ) as stderr:
                exit_code = main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("Email sent successfully.", stdout.getvalue())
            smtp_client_factory.assert_called_once_with("localhost", 465)
            smtp_client.ehlo.assert_called()
            smtp_client.starttls.assert_called_once()
            smtp_client.login.assert_called_once_with("myuser", "mypassword")
            smtp_client.send_message.assert_called_once()

            message = smtp_client.send_message.call_args.args[0]
            self.assertEqual(message["From"], "noreply@example.com")
            self.assertEqual(message["To"], "test@example.com")
            self.assertEqual(message["Subject"], "Greetings")
            self.assertIn("Hello Alice,", message.get_content())
            self.assertIn("Your code is 123456.", message.get_content())


if __name__ == "__main__":
    unittest.main()
