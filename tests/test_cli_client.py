import unittest

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
