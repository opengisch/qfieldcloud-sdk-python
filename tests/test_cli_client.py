import unittest

from click.testing import CliRunner

from qfieldcloud_sdk.cli import QFIELDCLOUD_DEFAULT_URL, cli
from qfieldcloud_sdk.sdk import Client
from qfieldcloud_sdk.utils import get_numeric_params


class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = CliRunner()

    def test_parse_params(self):
        url = "https//my_service.org/api/?limit=10&offset=5"
        limit, offset = get_numeric_params(url, ("limit", "offset"))
        self.assertEqual(limit, 10)
        self.assertEqual(offset, 5)

    def test_list_project(self):
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

    def test_job_trigger(self):
        result = self.runner.invoke(
            cli,
            ["job-trigger", "absbsj-122-1212-1asas", "process_projectfile"],
            catch_exceptions=False,
        )
        self.assertEqual(result.exit_code, 0)


class TestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = Client(QFIELDCLOUD_DEFAULT_URL)

    def test_cache_results(self):
        results = self.client.list_projects(include_public=True)
        self.assertTrue(results)
