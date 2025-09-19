from src.framework_generator import FrameworkGenerator
from unittest.mock import MagicMock, patch, call


def test_code_quality_checks_for_models():
    config = MagicMock()
    llm_service = MagicMock()
    command_service = MagicMock()
    file_service = MagicMock()
    api_processor = MagicMock()

    framework_generator = FrameworkGenerator(
        config=config,
        llm_service=llm_service,
        command_service=command_service,
        file_service=file_service,
        api_processor=api_processor,
    )

    input_files = [MagicMock(), MagicMock()]
    fixed_files = [MagicMock(), MagicMock()]

    with (
        patch.object(command_service, "run_command_with_fix", return_value=fixed_files) as mock_run_fix,
        patch.object(command_service, "format_files") as mock_format,
        patch.object(command_service, "run_linter") as mock_lint,
    ):
        result = framework_generator._run_code_quality_checks(input_files, are_models=True)

        mock_run_fix.assert_called_once_with(
            command_func=command_service.run_typescript_compiler_for_files,
            fix_func=framework_generator._typescript_fix_wrapper,
            files=input_files,
            are_models=True,
        )
        mock_format.assert_called_once()
        mock_lint.assert_called_once()

        assert result is fixed_files
        assert result == fixed_files


def test_code_quality_checks_for_tests():
    config = MagicMock()
    llm_service = MagicMock()
    command_service = MagicMock()
    file_service = MagicMock()
    api_processor = MagicMock()

    framework_generator = FrameworkGenerator(
        config=config,
        llm_service=llm_service,
        command_service=command_service,
        file_service=file_service,
        api_processor=api_processor,
    )

    input_files = [MagicMock(), MagicMock()]
    fixed_files = [MagicMock(), MagicMock()]

    with (
        patch.object(command_service, "run_command_with_fix", return_value=fixed_files) as mock_run_fix,
        patch.object(command_service, "format_files") as mock_format,
        patch.object(command_service, "run_linter") as mock_lint,
    ):
        result = framework_generator._run_code_quality_checks(input_files)
        assert mock_run_fix.call_count == 2

        first_call = mock_run_fix.call_args_list[0]
        assert first_call == call(
            command_func=command_service.run_typescript_compiler_for_files,
            fix_func=framework_generator._typescript_fix_wrapper,
            files=input_files,
            are_models=False,
        )

        second_call = mock_run_fix.call_args_list[1]
        assert second_call == call(
            command_func=command_service.run_test,
            fix_func=framework_generator._test_fix_wrapper,
            files=fixed_files,
            max_retries=config.max_test_fixes,
        )

        mock_format.assert_called_once()
        mock_lint.assert_called_once()

        assert result is fixed_files
        assert result == fixed_files


def test_execution_fix_wrapper_stop():
    config = MagicMock()
    llm_service = MagicMock()
    command_service = MagicMock()
    file_service = MagicMock()
    api_processor = MagicMock()

    framework_generator = FrameworkGenerator(
        config=config,
        llm_service=llm_service,
        command_service=command_service,
        file_service=file_service,
        api_processor=api_processor,
    )

    input_files = [MagicMock(), MagicMock()]
    messages = "Reporter output/HTTP Activity"
    fix_history = []
    fixed_files = [MagicMock(), MagicMock()]
    changes = MagicMock()
    stop = MagicMock()
    fix_return = (fixed_files, changes, stop)

    with (patch.object(llm_service, "fix_test_execution", return_value=fix_return) as mock_run_fix,):
        result_files, result_changes, result_stop = framework_generator._test_fix_wrapper(
            input_files, messages, fix_history, are_models=False
        )
        mock_run_fix.assert_called_once_with(input_files, messages, fix_history)
        assert result_files is fixed_files
        assert result_changes is changes
        assert result_stop == True


def test_execution_fix_wrapper_continue():
    config = MagicMock()
    llm_service = MagicMock()
    command_service = MagicMock()
    file_service = MagicMock()
    api_processor = MagicMock()

    framework_generator = FrameworkGenerator(
        config=config,
        llm_service=llm_service,
        command_service=command_service,
        file_service=file_service,
        api_processor=api_processor,
    )

    input_files = [MagicMock(), MagicMock()]
    messages = "Reporter output/HTTP Activity"
    fix_history = []
    fixed_files = [MagicMock(), MagicMock()]
    changes = MagicMock()
    stop = None
    fix_return = (fixed_files, changes, stop)

    with (patch.object(llm_service, "fix_test_execution", return_value=fix_return) as mock_run_fix,):
        result_files, result_changes, result_stop = framework_generator._test_fix_wrapper(
            input_files, messages, fix_history, are_models=False
        )
        mock_run_fix.assert_called_once_with(input_files, messages, fix_history)
        assert result_files is fixed_files
        assert result_changes is changes
        assert result_stop == False


def test_typescript_fix_wrapper_on_models():
    config = MagicMock()
    llm_service = MagicMock()
    command_service = MagicMock()
    file_service = MagicMock()
    api_processor = MagicMock()

    framework_generator = FrameworkGenerator(
        config=config,
        llm_service=llm_service,
        command_service=command_service,
        file_service=file_service,
        api_processor=api_processor,
    )

    input_files = [MagicMock(), MagicMock()]
    messages = "Reporter output/HTTP Activity"
    fixed_files = [MagicMock(), MagicMock()]
    are_models = True

    with patch.object(llm_service, "fix_typescript", return_value=fixed_files) as mock_ts_fix:
        result_files, result_changes, result_stop = framework_generator._typescript_fix_wrapper(
            input_files,
            messages,
            [],
            are_models,
        )
        mock_ts_fix.assert_called_once_with(input_files, messages, are_models)
        assert result_files is fixed_files
        assert result_changes == None
        assert result_stop == False


def test_typescript_fix_wrapper_on_tests():
    config = MagicMock()
    llm_service = MagicMock()
    command_service = MagicMock()
    file_service = MagicMock()
    api_processor = MagicMock()

    framework_generator = FrameworkGenerator(
        config=config,
        llm_service=llm_service,
        command_service=command_service,
        file_service=file_service,
        api_processor=api_processor,
    )

    input_files = [MagicMock(), MagicMock()]
    messages = "Reporter output/HTTP Activity"
    fixed_files = [MagicMock(), MagicMock()]
    are_models = False

    with patch.object(llm_service, "fix_typescript", return_value=fixed_files) as mock_ts_fix:
        result_files, result_changes, result_stop = framework_generator._typescript_fix_wrapper(
            input_files,
            messages,
            [],
            are_models,
        )
        mock_ts_fix.assert_called_once_with(input_files, messages, are_models)
        assert result_files is fixed_files
        assert result_changes == None
        assert result_stop == False
