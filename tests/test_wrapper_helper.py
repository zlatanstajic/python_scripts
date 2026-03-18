"""Tests for src/helpers/wrapper_helper.py."""

from unittest.mock import patch

from src.helpers.wrapper_helper import WrapperHelper, finish_script, run_script


class TestFinishScript:
    """Tests for the finish_script function."""

    @patch("sys.exit")
    @patch("src.helpers.wrapper_helper.logger")
    def test_finish_ok_no_details(self, mock_logger, mock_exit):
        """Verify OK status with no details."""
        finish_script()
        mock_logger.info.assert_called_once_with("\n\nScript finishing OK")
        mock_exit.assert_called_once_with(0)

    @patch("sys.exit")
    @patch("src.helpers.wrapper_helper.logger")
    def test_finish_ok_with_details(self, mock_logger, mock_exit):
        """Verify OK status includes details suffix."""
        finish_script(False, "all done")
        mock_logger.info.assert_called_once_with("\n\nScript finishing OK - all done")
        mock_exit.assert_called_once_with(0)

    @patch("sys.exit")
    @patch("src.helpers.wrapper_helper.logger")
    def test_finish_error_no_details(self, mock_logger, mock_exit):
        """Verify ERROR status with no details."""
        finish_script(True)
        mock_logger.info.assert_called_once_with("\n\nScript finishing ERROR")
        mock_exit.assert_called_once_with(1)

    @patch("sys.exit")
    @patch("src.helpers.wrapper_helper.logger")
    def test_finish_error_with_details(self, mock_logger, mock_exit):
        """Verify ERROR status includes details suffix."""
        finish_script(True, "something broke")
        mock_logger.info.assert_called_once_with(
            "\n\nScript finishing ERROR - something broke"
        )
        mock_exit.assert_called_once_with(1)


class TestRunScript:
    """Tests for the run_script function."""

    @patch("src.helpers.wrapper_helper.finish_script")
    def test_runs_function_successfully(self, mock_finish):
        """Verify that a normal function runs without calling finish_script."""
        called = []
        run_script(lambda: called.append(True))
        assert called == [True]
        mock_finish.assert_not_called()

    @patch("src.helpers.wrapper_helper.finish_script")
    def test_handles_eof_error(self, mock_finish):
        """Verify EOFError is caught and finish_script called with False."""
        run_script(lambda: (_ for _ in ()).throw(EOFError()))
        mock_finish.assert_called_once()
        args = mock_finish.call_args[0]
        assert args[0] is False

    @patch("src.helpers.wrapper_helper.finish_script")
    def test_handles_keyboard_interrupt(self, mock_finish):
        """Verify KeyboardInterrupt is caught and finish_script called with False."""
        run_script(lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
        mock_finish.assert_called_once()
        args = mock_finish.call_args[0]
        assert args[0] is False

    @patch("src.helpers.wrapper_helper.finish_script")
    def test_handles_generic_exception(self, mock_finish):
        """Verify generic Exception is caught and finish_script called with True."""
        run_script(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        mock_finish.assert_called_once()
        args = mock_finish.call_args[0]
        assert args[0] is True
        assert "boom" in args[1]


class TestWrapperHelper:
    """Tests for the WrapperHelper class."""

    @patch("src.helpers.wrapper_helper.finish_script")
    def test_end_defaults(self, mock_finish):
        """Verify WrapperHelper.end forwards default arguments."""
        WrapperHelper.end()
        mock_finish.assert_called_once_with(False, "")

    @patch("src.helpers.wrapper_helper.finish_script")
    def test_end_with_error(self, mock_finish):
        """Verify WrapperHelper.end forwards error flag and details."""
        WrapperHelper.end(True, "fatal")
        mock_finish.assert_called_once_with(True, "fatal")

    @patch("src.helpers.wrapper_helper.run_script")
    def test_main_delegates_to_run_script(self, mock_run):
        """Verify WrapperHelper.main delegates to run_script."""

        def dummy_fn():
            pass

        WrapperHelper.main(dummy_fn)
        mock_run.assert_called_once_with(dummy_fn)
