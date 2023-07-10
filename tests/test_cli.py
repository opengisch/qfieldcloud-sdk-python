import unittest

from click.testing import CliRunner

from qfieldcloud_sdk.cli import cli


class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = CliRunner()

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
