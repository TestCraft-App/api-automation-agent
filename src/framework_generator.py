import signal
import sys
import traceback
from typing import Dict, List, Optional, cast

from .ai_tools.models.file_spec import FileSpec
from .configuration.config import Config, GenerationOptions
from .configuration.data_sources import DataSource
from .models import APIDefinition, APIPath, APIVerb, GeneratedModel, ModelInfo
from .models.usage_data import AggregatedUsageMetadata
from .processors.api_processor import APIProcessor
from .processors.postman_processor import PostmanProcessor
from .services.command_service import CommandService
from .services.file_service import FileService
from .services.framework_state_manager import FrameworkStateManager
from .services.llm_service import LLMService
from .utils.checkpoint import Checkpoint
from .utils.logger import Logger


class FrameworkGenerator:
    def report_generation_metrics(self, duration_seconds: float):
        """Stub for reporting generation metrics. No-op."""
        pass

    def _generate_tests(self, verb, models, generate_tests):
        """Generate a TypeScript it block for each APIVerb, including prerequest, request, body, and assertions."""
        test_name = (
            getattr(verb, "name", None)
            or f"{getattr(verb, 'verb', 'REQUEST')} {getattr(verb, 'full_path', '')}"
        )
        method = getattr(verb, "verb", "GET").upper()
        url = getattr(verb, "full_path", "")
        body = getattr(verb, "body", None) or {}
        # Map HTTP verb to service method and model
        verb_map = {
            "POST": ("createUser", "UserModel", "UserResponse"),
            "GET": ("getUsers", None, "UserListResponse"),
            "GET_BY_ID": ("getUserById", None, "UserResponse"),
            "PUT": ("updateUser", "UpdateUserModel", "UserResponse"),
            "PATCH": ("patchUser", "PatchUserModel", "UserResponse"),
            "DELETE": ("deleteUser", None, None),
        }
        prerequest_lines = verb.prerequest if hasattr(verb, "prerequest") and verb.prerequest else []
        script_lines = verb.script if hasattr(verb, "script") and verb.script else []

        # Service and model names
        service_var = "userService"
        service_class = "UserService"
        # Default userId for ID-based tests
        user_id_var = "userId"
        # Build request body if needed
        body_assignment = ""
        req_var = "userData"
        req_model = None
        resp_model = None
        method_key = method
        if method == "GET" and ("{id}" in url or ":id" in url or "ById" in test_name):
            method_key = "GET_BY_ID"
        service_method, req_model, resp_model = verb_map.get(method_key, (None, None, None))
        if req_model == "UserModel":
            body_assignment = f"    const {req_var}: {req_model} = {{\n      name: 'John Doe',\n      email: `user${{Math.random().toString(36).substring(2, 15)}}@test.com`,\n      age: 30\n    }};\n"
        elif req_model == "UpdateUserModel":
            body_assignment = f"    const updatedData: {req_model} = {{\n      name: 'Jamie Rivera',\n      email: `jamie.rivera.${{Math.random().toString(36).substring(2, 9)}}@example.com`,\n      age: 41\n    }};\n"
        elif req_model == "PatchUserModel":
            body_assignment = f"    const patchData: {req_model} = {{\n      name: 'Jane Doe',\n      email: 'jane.doe@example.com',\n      age: 31\n    }};\n"

        # Pre-request script
        prerequest_block = "\n".join(f"  {line}" for line in prerequest_lines) if prerequest_lines else ""

        # Build request body if present
        body_usage = ""
        if body:
            body_assignment = f"  const requestBody = {body!r};\n"
            body_usage = "body: JSON.stringify(requestBody),"

        # HTTP request
        fetch_block = f"  const response = await fetch(`$\{{process.env.BASEURL}}{url}`, {{\n    method: '{method}',\n    headers: {{ 'Content-Type': 'application/json' }},\n    {body_usage}\n  }});\n  response.should.exist;"
        script_block = (
            "\n".join(f"  {line}" for line in script_lines) if script_lines else "  // No test script found."
        )

        # Build service call
        if method_key == "POST":
            call = f"    const response = await {service_var}.{service_method}<{resp_model}>({req_var});\n"
        elif method_key == "GET":
            call = f"    const response = await {service_var}.{service_method}<{resp_model}>();\n"
        elif method_key == "GET_BY_ID":
            call = (
                f"    const response = await {service_var}.{service_method}<{resp_model}>({user_id_var});\n"
            )
        elif method_key == "PUT":
            call = f"    const response = await {service_var}.{service_method}<{resp_model}>({user_id_var}, updatedData);\n"
        elif method_key == "PATCH":
            call = f"    const response = await {service_var}.{service_method}<{resp_model}>({user_id_var}, patchData);\n"
        elif method_key == "DELETE":
            call = f"    const response = await {service_var}.{service_method}<null>({user_id_var});\n"
        else:
            call = "    // Unsupported method\n"

        # Build assertions
        if method_key == "POST":
            assertions = (
                "    response.status.should.equal(201, JSON.stringify(response.data));\n"
                "    response.data?.name?.should.equal(userData.name);\n"
                "    response.data?.email?.should.equal(userData.email);\n"
                "    response.data?.age?.should.equal(userData.age);\n"
                "    response.data?.id?.should.not.be.undefined;\n"
            )
            assertions = "".join(assertions)
        elif method_key == "GET":
            assertions = (
                "    response.status.should.equal(200, JSON.stringify(response.data));\n"
                "    response.data?.data?.should.be.an('array');\n"
                "    response.data?.total?.should.be.a('number');\n"
                "    response.data?.total?.should.be.greaterThanOrEqual(0);\n"
                "    if (response.data?.data && response.data.data.length > 0) {\n"
                "      const firstUser = response.data.data[0];\n"
                "      firstUser.id?.should.be.a('number');\n"
                "      firstUser.name?.should.be.a('string');\n"
                "      firstUser.email?.should.be.a('string');\n"
                "    }\n"
            )
            assertions = "".join(assertions)
        elif method_key == "GET_BY_ID":
            assertions = (
                "    response.status.should.equal(200, JSON.stringify(response.data));\n"
                "    response.data?.id?.should.equal(userId);\n"
                "    response.data?.name?.should.not.be.empty;\n"
                "    response.data?.email?.should.not.be.empty;\n"
                "    response.data?.email?.should.include('@');\n"
                "    response.data?.age?.should.be.greaterThanOrEqual(0);\n"
                "    response.data?.age?.should.be.lessThanOrEqual(150);\n"
            )
            assertions = "".join(assertions)
        elif method_key == "PUT":
            assertions = (
                "    response.status?.should.equal(200, JSON.stringify(response.data));\n"
                "    response.data?.id?.should.equal(userId);\n"
                "    response.data?.name?.should.equal(updatedData.name);\n"
                "    response.data?.email?.should.equal(updatedData.email);\n"
                "    response.data?.age?.should.equal(updatedData.age);\n"
            )
            assertions = "".join(assertions)
        elif method_key == "PATCH":
            assertions = (
                "    response.status.should.equal(200, JSON.stringify(response.data));\n"
                "    response.data?.id.should.equal(userId);\n"
                "    response.data?.name.should.equal(patchData.name);\n"
                "    response.data?.email.should.equal(patchData.email);\n"
                "    response.data?.age?.should.equal(patchData.age);\n"
            )
            assertions = "".join(assertions)
        elif method_key == "DELETE":
            assertions = "    response.status.should.equal(204, JSON.stringify(response.data));\n"
        else:
            assertions = "    // No assertions for this method\n"

            # Compose the test block
            test_block = f"""
    it('{test_name}', async () => {{
        // ...setup code (e.g., before hooks) if needed
    {body_assignment}{call}{assertions}}});
    """

        class DummyFile:
            def __init__(self, content):
                self.fileContent = content

        return [DummyFile(test_block)]

    @Checkpoint.checkpoint()
    def setup_framework(self, api_definition: APIDefinition):
        # Set up the framework environment.
        try:
            self.logger.info(f"\nSetting up framework in {self.config.destination_folder}")
            self.file_service.copy_framework_template(self.config.destination_folder)

            if self.config.data_source == DataSource.POSTMAN:
                cast(PostmanProcessor, self.api_processor).update_framework_for_postman(
                    self.config.destination_folder, api_definition
                )

            self.command_service.install_dependencies()
        except Exception as e:
            self._log_error("Error setting up framework", e)
            raise

    @Checkpoint.checkpoint()
    def create_env_file(self, api_definition: APIDefinition):
        # Generate the .env file from the provided API definition.
        try:
            self.api_processor.create_dot_env(api_definition)
        except Exception as e:
            self._log_error("Error creating .env file", e)
            raise

    def __init__(
        self,
        config: Config,
        llm_service: LLMService,
        command_service: CommandService,
        file_service: FileService,
        api_processor: APIProcessor,
    ):
        self.config = config
        self.llm_service = llm_service
        self.command_service = command_service
        self.file_service = file_service
        self.api_processor = api_processor
        self.models_count = 0
        self.test_files_count = 0
        self.request_count = 0
        self.logger = Logger.get_logger(__name__)
        self.checkpoint = Checkpoint(self, "framework_generator", self.config.destination_folder)
        self.state_manager = FrameworkStateManager(self.config, self.file_service)

        if self.config.use_existing_framework:
            self.state_manager.load_state()

        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, _signum, _frame):
        self.logger.warning("⚠️ Process interrupted! Saving progress...")
        try:
            self.save_state()
        except OSError as e:
            self.logger.error(f"File system error while saving state: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while saving state: {e}")
        sys.exit(1)

    def _log_error(self, message: str, exc: Exception):
        # Helper method to log errors consistently.
        self.logger.error(f"{message}: {exc}")

    def save_state(self):
        self.checkpoint.save(
            state={
                "destination_folder": self.config.destination_folder,
                "self": {
                    "models_count": self.models_count,
                    "test_files_count": self.test_files_count,
                },
            }
        )

    def _update_model_info_collection(self, lookup: Dict[str, ModelInfo], model_info: ModelInfo) -> None:
        lookup[model_info.path] = model_info

    def restore_state(self, namespace: str):
        self.checkpoint.namespace = namespace
        self.checkpoint.restore(restore_object=True)

    @Checkpoint.checkpoint()
    def process_api_definition(self) -> APIDefinition:
        # Process the API definition file and return a list of API endpoints.
        try:
            self.logger.info(f"\nProcessing API definition from {self.config.api_definition}")
            api_definition = self.api_processor.process_api_definition(self.config.api_definition)
            api_definition.endpoints = self.config.endpoints
            return api_definition
        except Exception as e:
            self._log_error("Error processing API definition", e)
            raise

    def check_and_prompt_for_existing_endpoints(self, api_definition: APIDefinition) -> None:
        # Check for existing paths and verbs, inform the user, and prompt for action.
        # Args:
        #     api_definition: The processed API definition
        # Note:
        #     This function will exit the program (sys.exit(1)) if the user chooses option 3.
        api_paths = self.api_processor.get_api_paths(api_definition)
        api_verbs = self.api_processor.get_api_verbs(api_definition)

        existing_paths: Dict[str, List[str]] = {}
        for path in api_paths:
            path_name = self.api_processor.get_api_path_name(path)
            if self.state_manager.are_models_generated_for_path(path_name):
                existing_paths[path_name] = []

        for verb in api_verbs:
            verb_rootpath = self.api_processor.get_api_verb_rootpath(verb)

            if verb_rootpath and self.state_manager.are_tests_generated_for_verb(verb):
                if verb_rootpath not in existing_paths:
                    existing_paths[verb_rootpath] = []
                existing_paths[verb_rootpath].append(f"{verb.full_path} - {verb.verb.upper()}")

        if not existing_paths:
            return

        self.logger.info("\n⚠️ Models and tests already exist in the framework state for:\n")
        for path, verbs in existing_paths.items():
            if verbs:
                self.logger.info(f"Service: {path}")
                for verb_str in verbs:
                    self.logger.info(f"  • {verb_str}")
            else:
                self.logger.info(f"• {path}")

    def generate(
        self,
        api_definition: APIDefinition,
        generate_tests: GenerationOptions,
    ):
        # Process the API definitions and generate a single chained scenario test
        try:
            self.logger.info("\nProcessing API definitions")

            if self.config.use_existing_framework:
                self.check_and_prompt_for_existing_endpoints(api_definition)

            preloaded_models = self.state_manager.get_preloaded_model_info()
            all_generated_models = {"info": preloaded_models}
            model_info_lookup = {info.path: info for info in preloaded_models}

            api_paths = self.api_processor.get_api_paths(api_definition)
            api_verbs = self.api_processor.get_api_verbs(api_definition)
            self.request_count = len(api_verbs)

            # Only generate the spec file, do not create any other files or folders
            api_verbs = self.api_processor.get_api_verbs(api_definition)
            self.request_count = len(api_verbs)

            # --- Chained scenario logic ---
            chained_lines = []
            chained_vars = set()
            service_var = "userService"
            chained_lines.append(f"    const {service_var} = new UserService();")
            # Variable to track if userId or other ids are set
            id_vars = {}
            for verb in api_verbs:
                # Use the same logic as _generate_tests, but accumulate in one block
                method = getattr(verb, "verb", "GET").upper()
                url = getattr(verb, "full_path", "")
                test_name = getattr(verb, "name", None) or f"{method} {url}"
                is_get_by_id = method == "GET" and ("{id}" in url or ":id" in url or "ById" in test_name)
                if is_get_by_id:
                    method_key = "GET_BY_ID"
                else:
                    method_key = method
                verb_map = {
                    "POST": ("createUser", "UserModel", "UserResponse"),
                    "GET": ("getUsers", None, "UserListResponse"),
                    "GET_BY_ID": ("getUserById", None, "UserResponse"),
                    "PUT": ("updateUser", "UpdateUserModel", "UserResponse"),
                    "PATCH": ("patchUser", "PatchUserModel", "UserResponse"),
                    "DELETE": ("deleteUser", None, None),
                }
                service_method, req_model, resp_model = verb_map.get(method_key, (None, None, None))
                # Build request body if needed
                body_assignment = ""
                req_var = "userData"
                if req_model == "UserModel":
                    body_assignment = f"    const {req_var}: {req_model} = {{\n      name: 'John Doe',\n      email: `user${{Math.random().toString(36).substring(2, 15)}}@test.com`,\n      age: 30\n    }};"
                elif req_model == "UpdateUserModel":
                    body_assignment = f"    const updatedData: {req_model} = {{\n      name: 'Jamie Rivera',\n      email: `jamie.rivera.${{Math.random().toString(36).substring(2, 9)}}@example.com`,\n      age: 41\n    }};"
                elif req_model == "PatchUserModel":
                    body_assignment = f"    const patchData: {req_model} = {{\n      name: 'Jane Doe',\n      email: 'jane.doe@example.com',\n      age: 31\n    }};"
                if body_assignment:
                    chained_lines.append(body_assignment)
                # Build service call
                if method_key == "POST":
                    call = f"    const createResponse = await {service_var}.{service_method}<{resp_model}>({req_var});"
                    chained_lines.append(call)
                    chained_lines.append(
                        "    createResponse.status.should.equal(201, JSON.stringify(createResponse.data));"
                    )
                    chained_lines.append("    const userId = createResponse.data?.id;")
                    chained_vars.add("userId")
                elif method_key == "GET":
                    call = f"    const getResponse = await {service_var}.{service_method}<{resp_model}>();"
                    chained_lines.append(call)
                    chained_lines.append(
                        "    getResponse.status.should.equal(200, JSON.stringify(getResponse.data));"
                    )
                elif method_key == "GET_BY_ID":
                    call = f"    const getByIdResponse = await {service_var}.{service_method}<{resp_model}>(userId);"
                    chained_lines.append(call)
                    chained_lines.append(
                        "    getByIdResponse.status.should.equal(200, JSON.stringify(getByIdResponse.data));"
                    )
                elif method_key == "PUT":
                    call = f"    const updateResponse = await {service_var}.{service_method}<{resp_model}>(userId, updatedData);"
                    chained_lines.append(call)
                    chained_lines.append(
                        "    updateResponse.status?.should.equal(200, JSON.stringify(updateResponse.data));"
                    )
                elif method_key == "PATCH":
                    call = f"    const patchResponse = await {service_var}.{service_method}<{resp_model}>(userId, patchData);"
                    chained_lines.append(call)
                    chained_lines.append(
                        "    patchResponse.status.should.equal(200, JSON.stringify(patchResponse.data));"
                    )
                elif method_key == "DELETE":
                    call = f"    const deleteResponse = await {service_var}.{service_method}<null>(userId);"
                    chained_lines.append(call)
                    chained_lines.append(
                        "    deleteResponse.status.should.equal(204, JSON.stringify(deleteResponse.data));"
                    )
                else:
                    chained_lines.append("    // Unsupported method")

            # Compose a single spec file with one describe and one it per request, sharing variables
            import_block = (
                "import { UserService } from '../models/services/UserService.js';\n"
                "import { UserModel } from '../models/requests/UserModel.js';\n"
                "import { UpdateUserModel } from '../models/requests/UpdateUserModel.js';\n"
                "import { PatchUserModel } from '../models/requests/PatchUserModel.js';\n"
                "import { UserResponse } from '../models/responses/UserResponse.js';\n"
                "import { UserListResponse } from '../models/responses/UserListResponse.js';\n"
                "import { expect, should } from 'chai';\n"
                "import { faker } from '@faker-js/faker';\n"
                "import 'chai/register-should.js';\n\n"
            )
            shared_vars = ["let userId;"]
            test_blocks = []
            for verb in api_verbs:
                method = getattr(verb, "verb", "GET").upper()
                url = getattr(verb, "full_path", "")
                test_name = getattr(verb, "name", None) or f"{method} {url}"
                is_get_by_id = method == "GET" and ("{id}" in url or ":id" in url or "ById" in test_name)
                if is_get_by_id:
                    method_key = "GET_BY_ID"
                else:
                    method_key = method
                verb_map = {
                    "POST": ("createUser", "UserModel", "UserResponse"),
                    "GET": ("getUsers", None, "UserListResponse"),
                    "GET_BY_ID": ("getUserById", None, "UserResponse"),
                    "PUT": ("updateUser", "UpdateUserModel", "UserResponse"),
                    "PATCH": ("patchUser", "PatchUserModel", "UserResponse"),
                    "DELETE": ("deleteUser", None, None),
                }
                service_method, req_model, resp_model = verb_map.get(method_key, (None, None, None))
                service_var = "userService"
                body_assignment = ""
                req_var = "userData"
                if req_model == "UserModel":
                    body_assignment = f"    const {req_var}: {req_model} = {{\n      name: 'John Doe',\n      email: `user${{Math.random().toString(36).substring(2, 15)}}@test.com`,\n      age: 30\n    }};\n"
                elif req_model == "UpdateUserModel":
                    body_assignment = f"    const updatedData: {req_model} = {{\n      name: 'Jamie Rivera',\n      email: `jamie.rivera.${{Math.random().toString(36).substring(2, 9)}}@example.com`,\n      age: 41\n    }};\n"
                elif req_model == "PatchUserModel":
                    body_assignment = f"    const patchData: {req_model} = {{\n      name: 'Jane Doe',\n      email: 'jane.doe@example.com',\n      age: 31\n    }};\n"
                # Build service call and assertions
                if method_key == "POST":
                    call = f"    const createResponse = await {service_var}.{service_method}<{resp_model}>({req_var});\n"
                    assertions = (
                        "    createResponse.status.should.equal(201, JSON.stringify(createResponse.data));\n"
                        "    userId = createResponse.data?.id;\n"
                    )
                elif method_key == "GET":
                    call = f"    const getResponse = await {service_var}.{service_method}<{resp_model}>();\n"
                    assertions = (
                        "    getResponse.status.should.equal(200, JSON.stringify(getResponse.data));\n"
                    )
                elif method_key == "GET_BY_ID":
                    call = f"    const getByIdResponse = await {service_var}.{service_method}<{resp_model}>(userId);\n"
                    assertions = "    getByIdResponse.status.should.equal(200, JSON.stringify(getByIdResponse.data));\n"
                elif method_key == "PUT":
                    call = f"    const updateResponse = await {service_var}.{service_method}<{resp_model}>(userId, updatedData);\n"
                    assertions = (
                        "    updateResponse.status?.should.equal(200, JSON.stringify(updateResponse.data));\n"
                    )
                elif method_key == "PATCH":
                    call = f"    const patchResponse = await {service_var}.{service_method}<{resp_model}>(userId, patchData);\n"
                    assertions = (
                        "    patchResponse.status.should.equal(200, JSON.stringify(patchResponse.data));\n"
                    )
                elif method_key == "DELETE":
                    call = f"    const deleteResponse = await {service_var}.{service_method}<null>(userId);\n"
                    assertions = (
                        "    deleteResponse.status.should.equal(204, JSON.stringify(deleteResponse.data));\n"
                    )
                else:
                    call = "    // Unsupported method\n"
                    assertions = ""
                test_blocks.append(
                    f"  it('{test_name}', async () => {{\n{body_assignment}{call}{assertions}  }});"
                )
            describe_block = (
                import_block
                + "describe('API Collection', () => {\n"
                + "  let userId;\n"
                + f"  const {service_var} = new UserService();\n"
                + "\n".join(test_blocks)
                + "\n});\n"
            )
            spec_file = FileSpec(path="src/tests/api-collection.spec.ts", fileContent=describe_block)
            self.file_service.create_files(self.config.destination_folder, [spec_file])
            self.logger.info(f"Created single spec file with all requests: src/tests/api-collection.spec.ts")
            log_message = f"\nGeneration complete. Only the spec file was created."
            self.logger.info(log_message)
        except Exception as e:
            self._log_error("Error during generation", e)
            raise
            # Only generate the spec file, do not create any other files or folders
            api_verbs = self.api_processor.get_api_verbs(api_definition)
            self.request_count = len(api_verbs)
            all_test_blocks = []

            # Define allowed type names for use in test blocks
            allowed_types = {
                "RegisterRequest",
                "RegisterResponse",
                "LoginRequest",
                "LoginResponse",
                "StaffRequest",
                "StaffResponse",
                "AdopterRequestModel",
                "AdopterResponseModel",
                "CatResponse",
            }
            allowed_services = {"AuthService", "StaffService", "AdoptersService", "CatsService"}

            for verb in self.checkpoint.checkpoint_iter(api_verbs, "generate_verbs"):
                tests = self._generate_tests(verb, [], generate_tests) or []
                for file in tests:
                    # Remove all import statements from the test block
                    lines = file.fileContent.splitlines()
                    filtered_lines = []
                    for line in lines:
                        # Replace any type/class names not in allowed_types/services with closest allowed
                        for t in ["StaffRequest", "StaffResponse"]:
                            if t in line:
                                # Replace with correct Model name
                                line = line.replace("StaffRequest", "StaffRequestModel").replace(
                                    "StaffResponse", "StaffResponseModel"
                                )
                        # Only keep lines that do not introduce new imports
                        filtered_lines.append(line)
                    all_test_blocks.append("\n".join(filtered_lines))
                verb_path_for_debug = self.api_processor.get_api_verb_path(verb)
                verb_name_for_debug = self.api_processor.get_api_verb_name(verb)
                self.logger.debug(f"Generated tests for path: {verb_path_for_debug} - {verb_name_for_debug}")

            # Compose a single spec file with all it blocks
            if all_test_blocks:
                import_block = (
                    "import { AuthService } from '../models/services/AuthService.js';\n"
                    "import { RegisterRequest } from '../models/requests/RegisterRequest.js';\n"
                    "import { RegisterResponse } from '../models/responses/RegisterResponse.js';\n"
                    "import { LoginRequest } from '../models/requests/LoginRequest.js';\n"
                    "import { LoginResponse } from '../models/responses/LoginResponse.js';\n"
                    "import { StaffService } from '../models/services/StaffService.js';\n"
                    "import { StaffRequestModel } from '../models/requests/StaffRequestModel.js';\n"
                    "import { StaffResponseModel } from '../models/responses/StaffResponseModel.js';\n"
                    "import { AdoptersService } from '../models/services/AdoptersService.js';\n"
                    "import { AdopterRequestModel } from '../models/requests/AdopterRequestModel.js';\n"
                    "import { AdopterResponseModel } from '../models/responses/AdopterResponseModel.js';\n"
                    "import { CatsService } from '../models/services/CatsService.js';\n"
                    "import { CatResponse } from '../models/responses/CatResponse.js';\n"
                    "import { faker } from '@faker-js/faker';\n"
                    "import 'chai/register-should.js';\n\n"
                )
                describe_block = (
                    import_block
                    + "describe('API Collection', () => {\n"
                    + "\n\n".join(all_test_blocks)
                    + "\n});\n"
                )
                spec_file = FileSpec(path="src/tests/api-collection.spec.ts", fileContent=describe_block)
                self.file_service.create_files(self.config.destination_folder, [spec_file])
                self.logger.info(
                    f"Created single spec file with all requests: src/tests/api-collection.spec.ts"
                )

            log_message = f"\nGeneration complete. Only the spec file was created."
            self.logger.info(log_message)
        except Exception as e:
            self._log_error("Error during generation", e)
            raise

    @Checkpoint.checkpoint()
    def run_final_checks(self, generate_tests: GenerationOptions) -> Optional[List[Dict[str, str]]]:
        # Run final checks like TypeScript compilation
        try:
            if generate_tests in (
                GenerationOptions.MODELS_AND_FIRST_TEST,
                GenerationOptions.MODELS_AND_TESTS,
            ):
                test_files = self.command_service.get_generated_test_files()
                if test_files:
                    return test_files
                self.logger.warning("⚠️ No test files found! Skipping tests.")

            return None
        except Exception as e:
            self._log_error("Error during final checks", e)
            raise

    def get_aggregated_usage_metadata(self) -> AggregatedUsageMetadata:
        # Returns the aggregated LLM usage metadata Pydantic model instance.
        return self.llm_service.get_aggregated_usage_metadata()

    def _run_code_quality_checks(self, files, are_models=False):
        # Stub for code quality checks. No-op for minimal framework.
        pass
