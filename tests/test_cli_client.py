import os
import unittest
from unittest import mock

from click.testing import CliRunner

from qfieldcloud_sdk.cli import QFIELDCLOUD_DEFAULT_URL, cli
from qfieldcloud_sdk.sdk import Client, Pagination, QfcException


class TestSDK(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = Client(QFIELDCLOUD_DEFAULT_URL)

    def test_paginated_list_projects(self):
        results = self.client.list_projects(limit=20)
        self.assertTrue(0 < len(results) and len(results) <= 20)

    def test_paginated_list_projects_include_public(self):
        results = self.client.list_projects(
            include_public=True, pagination=Pagination(limit=200)
        )
        self.assertTrue(0 < len(results) and len(results) <= 50)

    def test_parse_content_disposition_filename(self):
        filename = Client._get_filename_from_content_disposition(
            'attachment; filename="seed.xlsx"'
        )
        self.assertEqual(filename, "seed.xlsx")

        encoded_filename = Client._get_filename_from_content_disposition(
            "attachment; filename*=UTF-8''my%20seed.xlsx"
        )
        self.assertEqual(encoded_filename, "my seed.xlsx")

    def test_timeout_defaults_when_unset(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("QFC_SDK_CONNECT_TIMEOUT_S", None)
            os.environ.pop("QFC_SDK_READ_TIMEOUT_S", None)
            client = Client(QFIELDCLOUD_DEFAULT_URL)

        self.assertEqual(client.connect_timeout, 10.0)
        self.assertEqual(client.read_timeout, 300.0)

    def test_timeout_explicit_args_win_over_env(self):
        with mock.patch.dict(
            os.environ,
            {
                "QFC_SDK_CONNECT_TIMEOUT_S": "1",
                "QFC_SDK_READ_TIMEOUT_S": "2",
            },
        ):
            client = Client(QFIELDCLOUD_DEFAULT_URL, connect_timeout=5, read_timeout=6)

        self.assertEqual(client.connect_timeout, 5.0)
        self.assertEqual(client.read_timeout, 6.0)

    def test_timeout_resolved_from_env(self):
        with mock.patch.dict(
            os.environ,
            {
                "QFC_SDK_CONNECT_TIMEOUT_S": "7",
                "QFC_SDK_READ_TIMEOUT_S": "8.5",
            },
        ):
            client = Client(QFIELDCLOUD_DEFAULT_URL)

        self.assertEqual(client.connect_timeout, 7.0)
        self.assertEqual(client.read_timeout, 8.5)

    def test_timeout_zero_or_less_disables_timeout(self):
        client = Client(QFIELDCLOUD_DEFAULT_URL, connect_timeout=0, read_timeout=-1)

        self.assertIsNone(client.connect_timeout)
        self.assertIsNone(client.read_timeout)

    def test_timeout_only_disable_connect_timeout(self):
        client = Client(QFIELDCLOUD_DEFAULT_URL, connect_timeout=0, read_timeout=9)

        self.assertIsNone(client.connect_timeout)
        self.assertEqual(client.read_timeout, 9.0)

    def test_timeout_invalid_env_value_raises(self):
        with (
            mock.patch.dict(os.environ, {"QFC_SDK_CONNECT_TIMEOUT_S": "not-a-number"}),
            self.assertRaises(QfcException),
        ):
            Client(QFIELDCLOUD_DEFAULT_URL)

    def test_timeout_invalid_arg_value_raises(self):
        with self.assertRaises(QfcException):
            Client(QFIELDCLOUD_DEFAULT_URL, read_timeout="soon")  # type: ignore


class TestCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = CliRunner()

    def test_list_projects(self):
        result = self.runner.invoke(
            cli,
            [
                "list-projects",
                "--include-public",
                "--offset",
                5,
                "--limit",
                100,
            ],
            catch_exceptions=False,
        )
        self.assertEqual(result.exit_code, 0)

    def test_list_jobs(self):
        result = self.runner.invoke(
            cli,
            ["list-jobs", "my_project_id", "--limit", 10, "--offset", 5],
            catch_exceptions=False,
        )
        self.assertEqual(result.exit_code, 0)

    def test_create_user(self):
        client = mock.Mock()
        client.create_user.return_value = {
            "username": "field_mapper_42",
            "email": "field_mapper_42@example.com",
        }

        with mock.patch("qfieldcloud_sdk.cli.sdk.Client", return_value=client):
            result = self.runner.invoke(
                cli,
                [
                    "--json",
                    "create-user",
                    "field_mapper_42",
                    "s3cr3t",
                    "field_mapper_42@example.com",
                    "--exist-ok",
                ],
                catch_exceptions=False,
            )

        self.assertEqual(result.exit_code, 0)
        client.create_user.assert_called_once_with(
            "field_mapper_42",
            "s3cr3t",
            "field_mapper_42@example.com",
            exist_ok=True,
        )
        self.assertIn('"username": "field_mapper_42"', result.output)

    def test_timeout_options_wire_through_to_client(self):
        client = mock.Mock()
        client.logout.return_value = {"detail": "Logged out."}

        with mock.patch(
            "qfieldcloud_sdk.cli.sdk.Client", return_value=client
        ) as client_cls:
            result = self.runner.invoke(
                cli,
                [
                    "--connect-timeout",
                    "3",
                    "--read-timeout",
                    "4",
                    "logout",
                ],
                catch_exceptions=False,
            )

        self.assertEqual(result.exit_code, 0)
        _, kwargs = client_cls.call_args
        self.assertEqual(kwargs["connect_timeout"], 3.0)
        self.assertEqual(kwargs["read_timeout"], 4.0)

    def test_timeout_defaults_when_unset(self):
        client = mock.Mock()
        client.logout.return_value = {"detail": "Logged out."}

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("QFC_SDK_CONNECT_TIMEOUT_S", None)
            os.environ.pop("QFC_SDK_READ_TIMEOUT_S", None)
            with mock.patch(
                "qfieldcloud_sdk.cli.sdk.Client", return_value=client
            ) as client_cls:
                result = self.runner.invoke(cli, ["logout"], catch_exceptions=False)

        self.assertEqual(result.exit_code, 0)
        _, kwargs = client_cls.call_args
        self.assertIsNone(kwargs["connect_timeout"])
        self.assertIsNone(kwargs["read_timeout"])
