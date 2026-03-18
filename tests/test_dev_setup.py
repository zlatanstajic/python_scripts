import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, call, patch  # noqa: E402

import pyperclip  # noqa: E402
import pytest  # noqa: E402

from scripts.dev_setup import (  # noqa: E402
    checkout_source_branch,
    create_and_checkout_new_branch,
    create_message_description,
    create_message_name,
    delete_new_branch_and_checkout_to_source_branch,
    do_you_wish_to_proceed,
    get_current_directory,
    get_git_branches,
    get_target_branch,
    handle_copy_to_clipboard,
    is_git_repository,
    issue_name_for_branch,
    parse_arguments,
    push_to_target_branch,
    read_environment_variables,
    select_branch,
    user_input,
)


class TestIssueNameForBranch:
    def test_issue_name_for_branch_valid(self):
        assert issue_name_for_branch("Fix login bug") == "fix_login_bug"

    def test_issue_name_for_branch_with_special_chars(self):
        assert (
            issue_name_for_branch("Fix & test | bug.dot/")
            == "fix__and__test__-__bug_dot_dot_forward-slash_"
        )

    @patch("scripts.dev_setup.finish_script")
    def test_issue_name_for_branch_with_numbers(self, mock_finish):
        issue_name_for_branch("Fix bug 123")
        mock_finish.assert_called_once_with(True, "Issue name cannot contain numbers.")


class TestIsGitRepository:
    @patch("os.path.isdir", return_value=True)
    def test_is_git_repository_exists(self, mock_isdir):
        is_git_repository()  # Should not raise

    @patch("os.path.isdir", return_value=False)
    def test_is_git_repository_not_exists(self, mock_isdir):
        with pytest.raises(
            Exception, match="This script must be run in a git repository directory"
        ):
            is_git_repository()


class TestGetCurrentDirectory:
    @patch("os.getcwd", return_value="/path/to/dir")
    @patch("os.path.basename", return_value="dir")
    @patch("scripts.dev_setup.logger")
    def test_get_current_directory(self, mock_logger, mock_basename, mock_getcwd):
        get_current_directory()
        mock_logger.info.assert_called_once_with("Located in directory: dir\n")


class TestUserInput:
    @patch("builtins.input", return_value="test input")
    def test_user_input(self, mock_input):
        assert user_input("Enter something") == "test input"


class TestDoYouWishToProceed:
    @patch("builtins.input", return_value="y")
    def test_do_you_wish_to_proceed_yes(self, mock_input):
        assert do_you_wish_to_proceed() is True

    @patch("builtins.input", return_value="n")
    def test_do_you_wish_to_proceed_no(self, mock_input):
        assert do_you_wish_to_proceed() is False

    @patch("builtins.input", side_effect=["invalid", "yes"])
    @patch("builtins.print")
    def test_do_you_wish_to_proceed_invalid_then_yes(self, mock_print, mock_input):
        assert do_you_wish_to_proceed() is True


class TestGetGitBranches:
    @patch("subprocess.run")
    def test_get_git_branches_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  main\n* develop\n  feature\n"
        mock_run.return_value = mock_result
        branches = get_git_branches()
        assert branches == ["main", "develop", "feature"]

    @patch("subprocess.run")
    @patch("scripts.dev_setup.finish_script")
    def test_get_git_branches_failure(self, mock_finish, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        get_git_branches()
        mock_finish.assert_called_once_with(True, "Unable to list git branches.")


class TestSelectBranch:
    @patch("scripts.dev_setup.user_input", return_value="1")
    @patch("scripts.dev_setup.logger")
    def test_select_branch(self, mock_logger, mock_input):
        branches = ["main", "develop"]
        assert select_branch(branches) == "main"


class TestGetTargetBranch:
    def test_get_target_branch(self):
        assert get_target_branch("issues", 123, "Fix bug") == "issues/123_fix_bug"


class TestReadEnvironmentVariables:
    @patch.dict(
        os.environ,
        {
            "BRANCH_PREFIX": "feat",
            "REQUEST_PREFIX": "closes:",
            "ISSUE_BASE_PATH": "https://github.com/user",
        },
    )
    def test_read_environment_variables_custom(self):
        assert read_environment_variables() == (
            "feat",
            "closes:",
            "https://github.com/user",
        )

    def test_read_environment_variables_default(self):
        assert read_environment_variables() == ("issues", "refs:", "")


class TestCheckoutSourceBranch:
    @patch("subprocess.run")
    def test_checkout_source_branch_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        checkout_source_branch("main")

    @patch("subprocess.run")
    @patch("scripts.dev_setup.finish_script")
    def test_checkout_source_branch_failure(self, mock_finish, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        checkout_source_branch("main")
        mock_finish.assert_called_once_with(True, "Not able to checkout to the main")


class TestPushToTargetBranch:
    @patch("subprocess.run")
    def test_push_to_target_branch(self, mock_run):
        push_to_target_branch("issues/123_fix")
        mock_run.assert_called_once_with(
            ["git", "push", "-u", "origin", "issues/123_fix"]
        )


class TestCreateAndCheckoutNewBranch:
    @patch("subprocess.run")
    def test_create_and_checkout_new_branch(self, mock_run):
        create_and_checkout_new_branch("issues/123_fix")
        assert mock_run.call_count == 3
        mock_run.assert_has_calls(
            [
                call(["git", "pull"]),
                call(["git", "branch", "issues/123_fix"]),
                call(["git", "checkout", "issues/123_fix"]),
            ]
        )


class TestDeleteNewBranchAndCheckoutToSourceBranch:
    @patch("subprocess.run")
    def test_delete_new_branch_and_checkout_to_source_branch(self, mock_run):
        delete_new_branch_and_checkout_to_source_branch("main", "issues/123_fix")
        assert mock_run.call_count == 2
        mock_run.assert_has_calls(
            [
                call(["git", "checkout", "main"]),
                call(["git", "branch", "-D", "issues/123_fix"]),
            ]
        )


class TestCreateMessageName:
    def test_create_message_name(self):
        assert create_message_name("refs:", 123, "Fix bug") == "refs: #123 Fix bug\n"


class TestCreateMessageDescription:
    @patch("os.path.basename", return_value="repo")
    def test_create_message_description_with_github(self, mock_basename):
        desc = create_message_description("https://github.com/user", "issues", 123)
        assert desc == "Based on issues [#123](https://github.com/user/repo/issues/123)"

    def test_create_message_description_without_base(self):
        assert create_message_description("", "issues", 123) == ""


class TestHandleCopyToClipboard:
    @patch("scripts.dev_setup.pyperclip.copy")
    @patch("scripts.dev_setup.logger")
    def test_handle_copy_to_clipboard_with_desc(self, mock_logger, mock_copy):
        handle_copy_to_clipboard("name", "desc")
        mock_copy.assert_has_calls([call("desc"), call("name")])
        mock_logger.info.assert_has_calls(
            [
                call("\nCopied message description to the clipboard:\n\ndesc"),
                call("\nCopied message name info to the clipboard:\n\nname"),
            ]
        )

    @patch("scripts.dev_setup.pyperclip.copy", side_effect=pyperclip.PyperclipException)
    @patch("scripts.dev_setup.logger")
    def test_handle_copy_to_clipboard_error(self, mock_logger, mock_copy):
        handle_copy_to_clipboard("name", "desc")
        mock_logger.warning.assert_called_with(
            "Warning: Could not copy to clipboard. Please install xclip/xsel on Linux."
        )


class TestParseArguments:
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments_valid(self, mock_parse):
        mock_args = MagicMock()
        mock_args.number = 123
        mock_args.name = "Fix bug"
        mock_parse.return_value = mock_args
        args = parse_arguments()
        assert args.number == 123
        assert args.name == "Fix bug"

    @patch("scripts.dev_setup.missing_required_arguments")
    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments_missing(self, mock_parse, mock_missing):
        mock_args = MagicMock()
        mock_args.number = None
        mock_args.name = "Fix bug"
        mock_parse.return_value = mock_args
        parse_arguments()
        mock_missing.assert_called_once()


# Main is complex, perhaps skip or mock heavily
# For brevity, I'll skip main test for now
