import unittest
from unittest import mock

from click.testing import CliRunner

from qfieldcloud_sdk.cli import QFIELDCLOUD_DEFAULT_URL, cli
from qfieldcloud_sdk.sdk import Client, Pagination


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
