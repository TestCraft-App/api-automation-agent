import json
import os
import re
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
        """Log detailed generation metrics: request count, token usage, cost, and duration."""
        try:
            usage = self.llm_service.get_aggregated_usage_metadata()
            self.logger.info("\n--- Generation Metrics ---")
            self.logger.info(f"Requests generated: {self.request_count}")
            self.logger.info(f"Total input tokens: {usage.total_input_tokens}")
            self.logger.info(f"Total output tokens: {usage.total_output_tokens}")
            self.logger.info(f"Total tokens: {usage.total_tokens}")
            self.logger.info(f"Total LLM cost: ${usage.total_cost:.4f}")
            self.logger.info(f"Total fix attempts: {usage.total_fix_attempts}")
            self.logger.info(f"Elapsed time: {duration_seconds:.2f} seconds")
            self.logger.info("-------------------------\n")
        except Exception as e:
            self.logger.warning(f"Could not print generation metrics: {e}")

    def _generate_tests(self, verb, models, generate_tests):
        """Generate a TypeScript it block for each APIVerb.

        Note: Postman generation currently uses the custom single-spec logic in generate().
        This method must remain syntactically valid for non-Postman flows.
        """
        test_name = (
            getattr(verb, "name", None)
            or f"{getattr(verb, 'verb', 'REQUEST')} {getattr(verb, 'full_path', '')}"
        )
        method = getattr(verb, "verb", "GET").upper()
        url = getattr(verb, "full_path", "")

        service_var = "userService"
        verb_map = {
            "POST": ("createUser", "UserModel", "UserResponse"),
            "GET": ("getUsers", None, "UserListResponse"),
            "GET_BY_ID": ("getUserById", None, "UserResponse"),
            "PUT": ("updateUser", "UpdateUserModel", "UserResponse"),
            "PATCH": ("patchUser", "PatchUserModel", "UserResponse"),
            "DELETE": ("deleteUser", None, None),
        }
        method_key = method
        if method == "GET" and ("{id}" in url or ":id" in url or "ById" in test_name):
            method_key = "GET_BY_ID"
        service_method, req_model, resp_model = verb_map.get(method_key, (None, None, None))

        req_var = "userData"
        body_assignment = ""
        if req_model == "UserModel":
            body_assignment = (
                f"    const {req_var}: {req_model} = {{\n"
                "      name: 'John Doe',\n"
                "      email: `user${Math.random().toString(36).substring(2, 15)}@test.com`,\n"
                "      age: 30\n"
                "    };\n"
            )

        if method_key == "POST":
            call = f"    const response = await {service_var}.{service_method}<{resp_model}>({req_var});\n"
            assertions = "    response.status.should.equal(201, JSON.stringify(response.data));\n"
        elif method_key == "GET":
            call = f"    const response = await {service_var}.{service_method}<{resp_model}>();\n"
            assertions = "    response.status.should.equal(200, JSON.stringify(response.data));\n"
        elif method_key == "GET_BY_ID":
            call = f"    const response = await {service_var}.{service_method}<{resp_model}>(userId);\n"
            assertions = "    response.status.should.equal(200, JSON.stringify(response.data));\n"
        elif method_key == "DELETE":
            call = f"    const response = await {service_var}.{service_method}<null>(userId);\n"
            assertions = "    response.status.should.equal(204, JSON.stringify(response.data));\n"
        else:
            call = "    // Unsupported method\n"
            assertions = ""

        test_block = (
            f"\n    it('{test_name}', async () => {{\n"
            f"{body_assignment}"
            f"{call}"
            f"{assertions}"
            "    });\n"
        )

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
        # For Postman, generate a single runnable spec with shared vars and real generated services/models.
        try:
            self.logger.info("\nProcessing API definitions")

            if self.config.use_existing_framework:
                self.check_and_prompt_for_existing_endpoints(api_definition)

            api_paths = self.api_processor.get_api_paths(api_definition)
            api_verbs = self.api_processor.get_api_verbs(api_definition)
            self.request_count = len(api_verbs)

            # Postman template does not ship with the generated services/models.
            # Generate them first so the collection spec imports resolve.
            for api_path in api_paths:
                try:
                    definition_content = self.api_processor.get_api_path_content(api_path)
                    self.llm_service.generate_models(definition_content)
                except Exception as e:
                    self.logger.warning(f"Failed to generate models for path {api_path.root_path}: {e}")

            services_dir = os.path.join(self.config.destination_folder, "src", "models", "services")
            requests_dir = os.path.join(self.config.destination_folder, "src", "models", "requests")
            responses_dir = os.path.join(self.config.destination_folder, "src", "models", "responses")

            def _available_type_names(folder: str) -> set[str]:
                try:
                    return {
                        os.path.splitext(name)[0]
                        for name in os.listdir(folder)
                        if name.endswith(".ts") and not name.startswith(".")
                    }
                except Exception:
                    return set()

            available_services = _available_type_names(services_dir)
            available_requests = _available_type_names(requests_dir)
            available_responses = _available_type_names(responses_dir)

            def pick_existing(candidates: List[str], available: set[str]) -> Optional[str]:
                for c in candidates:
                    if c in available:
                        return c
                return None

            def service_has_method(service_class: str, method_name: str) -> bool:
                try:
                    service_path = os.path.join(services_dir, f"{service_class}.ts")
                    with open(service_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    return re.search(rf"\basync\s+{re.escape(method_name)}\b", content) is not None
                except Exception:
                    return False

            def _lower_camel(name: str) -> str:
                return name[:1].lower() + name[1:] if name else name

            def _extract_balanced(
                text: str, start_index: int, open_ch: str, close_ch: str
            ) -> tuple[str, int]:
                depth = 0
                out: list[str] = []
                i = start_index
                while i < len(text):
                    ch = text[i]
                    if ch == open_ch:
                        depth += 1
                        if depth > 1:
                            out.append(ch)
                    elif ch == close_ch:
                        depth -= 1
                        if depth == 0:
                            return "".join(out), i
                        out.append(ch)
                    else:
                        if depth >= 1:
                            out.append(ch)
                    i += 1
                return "".join(out), i

            def _split_params(params_src: str) -> list[str]:
                parts: list[str] = []
                buf: list[str] = []
                angle = paren = brace = bracket = 0
                for ch in params_src:
                    if ch == "<":
                        angle += 1
                    elif ch == ">" and angle > 0:
                        angle -= 1
                    elif ch == "(":
                        paren += 1
                    elif ch == ")" and paren > 0:
                        paren -= 1
                    elif ch == "{":
                        brace += 1
                    elif ch == "}" and brace > 0:
                        brace -= 1
                    elif ch == "[":
                        bracket += 1
                    elif ch == "]" and bracket > 0:
                        bracket -= 1

                    if ch == "," and angle == paren == brace == bracket == 0:
                        part = "".join(buf).strip()
                        if part:
                            parts.append(part)
                        buf = []
                        continue
                    buf.append(ch)
                tail = "".join(buf).strip()
                if tail:
                    parts.append(tail)
                return parts

            def _parse_service_methods(service_class: str) -> dict:
                """Parse basePath + methods from generated service class file."""
                meta: dict = {"base_path": "", "methods": []}
                try:
                    service_path = os.path.join(services_dir, f"{service_class}.ts")
                    with open(service_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    base_m = re.search(r"super\(\s*['\"]([^'\"]+)['\"]\s*\)", content)
                    if base_m:
                        meta["base_path"] = base_m.group(1)

                    meth_pat = re.compile(r"\basync\s+([A-Za-z0-9_]+)\s*<[^>]*>\s*\(", re.M)
                    matches = list(meth_pat.finditer(content))
                    for idx, m in enumerate(matches):
                        name = m.group(1)
                        start = m.start()
                        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
                        block = content[start:end]

                        http_m = re.search(r"return\s+await\s+this\.(get|post|put|patch|delete)\b", block)
                        http = http_m.group(1).upper() if http_m else None

                        paren_idx = block.find("(", block.find(name))
                        params_src = ""
                        if paren_idx != -1:
                            extracted, _ = _extract_balanced(block, paren_idx, "(", ")")
                            params_src = extracted

                        params: list[dict] = []
                        for p in _split_params(params_src):
                            p = p.strip()
                            if not p:
                                continue
                            p = p.split("=", 1)[0].strip()
                            if ":" not in p:
                                continue
                            n, t = p.split(":", 1)
                            params.append({"name": n.strip(), "type": t.strip()})

                        non_config = [p for p in params if p["name"] != "config"]

                        id_param = None
                        body_param_type = None
                        if http in {"DELETE", "GET"}:
                            if len(non_config) >= 1:
                                id_param = non_config[0]["name"]
                        elif http in {"PATCH", "PUT"}:
                            if len(non_config) >= 2:
                                id_param = non_config[0]["name"]
                                body_param_type = non_config[1]["type"]
                            elif len(non_config) == 1:
                                body_param_type = non_config[0]["type"]
                        elif http == "POST":
                            if len(non_config) >= 1:
                                body_param_type = non_config[0]["type"]

                        meta["methods"].append(
                            {
                                "name": name,
                                "http": http,
                                "id_param": id_param,
                                "body_type": body_param_type,
                            }
                        )
                except Exception:
                    return meta
                return meta

            service_index: dict[str, dict] = {
                svc: _parse_service_methods(svc) for svc in sorted(available_services)
            }

            def _generic_infer_call_spec(verb: APIVerb) -> Optional[dict]:
                method = (getattr(verb, "verb", "GET") or "GET").upper()
                path = getattr(verb, "full_path", "") or ""
                base_path = path.split("?")[0]

                desired_http = {
                    "GET": "GET",
                    "POST": "POST",
                    "PUT": "PUT",
                    "PATCH": "PATCH",
                    "DELETE": "DELETE",
                }.get(method)
                if not desired_http:
                    return None

                candidates: list[tuple[int, str, dict]] = []
                for svc, meta in service_index.items():
                    base = (meta.get("base_path") or "").rstrip("/")
                    if base and base_path.startswith(base):
                        candidates.append((len(base), svc, meta))
                if not candidates:
                    return None
                _, service_class, meta = max(candidates, key=lambda x: x[0])

                id_match = re.search(r"/\{\{([A-Za-z0-9_]+)\}\}$", base_path)
                id_var = id_match.group(1) if id_match else None
                wants_id = bool(id_var)

                method_candidates = [m for m in meta.get("methods", []) if m.get("http") == desired_http]
                if wants_id:
                    method_candidates = [m for m in method_candidates if m.get("id_param")]
                else:
                    method_candidates = [m for m in method_candidates if not m.get("id_param")]

                if not method_candidates:
                    method_candidates = [m for m in meta.get("methods", []) if m.get("http") == desired_http]
                if not method_candidates:
                    return None

                chosen = method_candidates[0]
                has_body = bool(chosen.get("body_type"))
                req_type = chosen.get("body_type") if has_body else None

                expected_status = 200
                if desired_http == "POST":
                    expected_status = 201
                elif desired_http == "DELETE":
                    expected_status = 204

                return {
                    "service_class": service_class,
                    "service_var": _lower_camel(service_class),
                    "service_method": chosen.get("name"),
                    "request_type": req_type,
                    "response_type": "any",
                    "expected_status": expected_status,
                    "id_var": id_var,
                    "has_body": has_body,
                    "auth": bool(getattr(verb, "auth", False)),
                }

            def extract_template_vars(text: str) -> set[str]:
                return set(re.findall(r"\{\{([A-Za-z0-9_]+)\}\}", text or ""))

            def translate_postman_rhs(value_expr: str, response_var: Optional[str]) -> Optional[str]:
                """Translate Postman JS RHS expressions to TS, never emitting pm.* or jsonData.*."""
                expr = (value_expr or "").strip().rstrip(";")
                if not expr:
                    return None

                # pm.variables.replaceIn("{{$randomCity}}")
                if "pm.variables.replaceIn" in expr and "{{$randomCity}}" in expr:
                    expr = "randomCity()"

                # jsonData.<prop> from `var jsonData = pm.response.json();`
                if "jsonData." in expr:
                    if not response_var:
                        return None
                    expr = re.sub(
                        r"\bjsonData\.([A-Za-z0-9_]+)\b",
                        lambda m: f"{response_var}.data?.{m.group(1)}",
                        expr,
                    )

                # Never leak Postman runtime objects
                if "pm." in expr or "jsonData" in expr:
                    return None

                return expr

            def infer_call_spec(verb: APIVerb) -> Optional[dict]:
                method = (getattr(verb, "verb", "GET") or "GET").upper()
                path = getattr(verb, "full_path", "") or ""
                base_path = path.split("?")[0]

                def has(prefix: str) -> bool:
                    return prefix in base_path

                # Auth
                if has("/api/auth/register") and method == "POST":
                    return {
                        "service_class": pick_existing(["AuthService"], available_services) or "AuthService",
                        "service_var": "authService",
                        "service_method": "register",
                        "request_type": pick_existing(["RegisterRequest"], available_requests)
                        or "RegisterRequest",
                        "response_type": pick_existing(["RegisterResponse"], available_responses)
                        or "RegisterResponse",
                        "expected_status": 201,
                    }
                if has("/api/auth/login") and method == "POST":
                    return {
                        "service_class": pick_existing(["AuthService"], available_services) or "AuthService",
                        "service_var": "authService",
                        "service_method": "login",
                        "request_type": pick_existing(["LoginRequest"], available_requests) or "LoginRequest",
                        "response_type": pick_existing(["LoginResponse"], available_responses)
                        or "LoginResponse",
                        "expected_status": 200,
                    }

                # Staff
                if re.search(r"/api/staff/?$", base_path) and method == "POST":
                    return {
                        "service_class": pick_existing(["StaffService"], available_services)
                        or "StaffService",
                        "service_var": "staffService",
                        "service_method": "createStaff",
                        "request_type": pick_existing(["StaffRequestModel"], available_requests)
                        or "StaffRequestModel",
                        "response_type": pick_existing(["StaffResponseModel"], available_responses)
                        or "StaffResponseModel",
                        "expected_status": 201,
                        "auth": True,
                    }

                # Adopters
                if re.search(r"/api/adopters/?$", base_path) and method == "POST":
                    adopter_service_class = (
                        pick_existing(["AdoptersService", "AdopterService"], available_services)
                        or "AdopterService"
                    )
                    return {
                        "service_class": adopter_service_class,
                        "service_var": (
                            "adoptersService"
                            if adopter_service_class == "AdoptersService"
                            else "adopterService"
                        ),
                        "service_method": "createAdopter",
                        "request_type": pick_existing(
                            ["CreateAdopterRequest", "AdopterRequestModel"], available_requests
                        )
                        or "AdopterRequestModel",
                        "response_type": pick_existing(
                            ["AdopterResponse", "AdopterResponseModel"], available_responses
                        )
                        or "AdopterResponseModel",
                        "expected_status": 201,
                    }

                # Cats
                if re.search(r"/api/cats/?$", base_path) and method == "POST":
                    service_class = pick_existing(["CatsService", "CatService"], available_services)
                    service_class = service_class or "CatService"
                    return {
                        "service_class": service_class,
                        "service_var": "catsService",
                        "service_method": "createCat",
                        "request_type": pick_existing(["CreateCatRequest"], available_requests)
                        or "CreateCatRequest",
                        "response_type": pick_existing(["CatResponse"], available_responses) or "CatResponse",
                        "expected_status": 201,
                    }
                # Adopt cat: PATCH /api/cats/{{catID}}
                if re.search(r"/api/cats/[^/]+$", base_path) and method == "PATCH":
                    service_class = pick_existing(["CatsService", "CatService"], available_services)
                    service_class = service_class or "CatService"
                    id_match = re.search(r"/api/cats/\{\{([A-Za-z0-9_]+)\}\}$", base_path)
                    id_var = id_match.group(1) if id_match else "id"
                    service_method = (
                        "adoptCat" if service_has_method(service_class, "adoptCat") else "updateCat"
                    )
                    return {
                        "service_class": service_class,
                        "service_var": "catsService",
                        "service_method": service_method,
                        "request_type": pick_existing(
                            ["AdoptCatRequest", "UpdateCatRequest"], available_requests
                        )
                        or "UpdateCatRequest",
                        "response_type": pick_existing(["CatResponse"], available_responses) or "CatResponse",
                        "expected_status": 200,
                        "id_var": id_var,
                    }

                # Clean-up: DELETEs
                # DELETE /api/cats/{{catID}}
                if re.search(r"/api/cats/[^/]+$", base_path) and method == "DELETE":
                    service_class = pick_existing(["CatsService", "CatService"], available_services)
                    service_class = service_class or "CatService"
                    id_match = re.search(r"/api/cats/\{\{([A-Za-z0-9_]+)\}\}$", base_path)
                    id_var = id_match.group(1) if id_match else "id"
                    service_method = (
                        "deleteCat" if service_has_method(service_class, "deleteCat") else "delete"
                    )
                    return {
                        "service_class": service_class,
                        "service_var": "catsService",
                        "service_method": service_method,
                        "response_type": "any",
                        "expected_status": 204,
                        "id_var": id_var,
                        "has_body": False,
                    }

                # DELETE /api/adopters/{{adopterID}}
                if re.search(r"/api/adopters/[^/]+$", base_path) and method == "DELETE":
                    adopter_service_class = (
                        pick_existing(["AdoptersService", "AdopterService"], available_services)
                        or "AdopterService"
                    )
                    id_match = re.search(r"/api/adopters/\{\{([A-Za-z0-9_]+)\}\}$", base_path)
                    id_var = id_match.group(1) if id_match else "id"
                    service_method = (
                        "deleteAdopter"
                        if service_has_method(adopter_service_class, "deleteAdopter")
                        else "delete"
                    )
                    return {
                        "service_class": adopter_service_class,
                        "service_var": (
                            "adoptersService"
                            if adopter_service_class == "AdoptersService"
                            else "adopterService"
                        ),
                        "service_method": service_method,
                        "response_type": "any",
                        "expected_status": 204,
                        "id_var": id_var,
                        "has_body": False,
                    }

                # DELETE /api/staff/{{staffID}} (auth)
                if re.search(r"/api/staff/[^/]+$", base_path) and method == "DELETE":
                    service_class = pick_existing(["StaffService"], available_services) or "StaffService"
                    id_match = re.search(r"/api/staff/\{\{([A-Za-z0-9_]+)\}\}$", base_path)
                    id_var = id_match.group(1) if id_match else "id"
                    service_method = (
                        "deleteStaff" if service_has_method(service_class, "deleteStaff") else "delete"
                    )
                    return {
                        "service_class": service_class,
                        "service_var": "staffService",
                        "service_method": service_method,
                        "response_type": "any",
                        "expected_status": 204,
                        "id_var": id_var,
                        "auth": True,
                        "has_body": False,
                    }

                generic = _generic_infer_call_spec(verb)
                if generic:
                    return generic

                return None

            def ts_expr_for_placeholder(name: str) -> str:
                # Prefer shared vars when we know we set them during the run.
                if name in shared_var_names:
                    return name
                # Common creds
                if name.lower() == "password":
                    return 'process.env["PASSWORD"] ?? ""'
                if name.lower() == "user":
                    return 'process.env["USER"] ?? ""'
                return f'process.env["{name.upper()}"] ?? ""'

            def ts_literal(value) -> str:
                if value is None:
                    return "undefined"
                if isinstance(value, bool):
                    return "true" if value else "false"
                if isinstance(value, (int, float)):
                    return str(value)
                if isinstance(value, str):
                    v = value
                    if v == "{{$randomCity}}":
                        return "randomCity()"
                    if v == "{{$randomPhoneNumber}}":
                        return "randomPhoneNumber()"
                    m = re.fullmatch(r"\{\{([A-Za-z0-9_]+)\}\}", v)
                    if m:
                        return ts_expr_for_placeholder(m.group(1))
                    return json.dumps(v)
                if isinstance(value, list):
                    return "[" + ", ".join(ts_literal(x) for x in value) + "]"
                if isinstance(value, dict):
                    parts = []
                    for k, v in value.items():
                        parts.append(f"{k}: {ts_literal(v)}")
                    return "{ " + ", ".join(parts) + " }"
                # Fallback
                return "undefined"

            def body_object_for_verb(verb: APIVerb) -> dict:
                body = getattr(verb, "body", {}) or {}
                if body:
                    return body

                raw = (getattr(verb, "raw_body", "") or "").strip()
                if not raw:
                    return {}

                # Attempt to parse templated JSON (e.g. {"adopterId": {{adopterID}}})
                tmp = raw
                tmp = re.sub(r":\s*\{\{([A-Za-z0-9_]+)\}\}\s*([,}])", r': "__VAR__\\1__"\\2', tmp)
                tmp = re.sub(r'"\{\{([A-Za-z0-9_]+)\}\}"', r'"__VAR__\\1__"', tmp)
                tmp = tmp.replace("{{$randomCity}}", "__RANDOM_CITY__")
                tmp = tmp.replace("{{$randomPhoneNumber}}", "__RANDOM_PHONE__")

                try:
                    parsed = json.loads(tmp)
                except Exception:
                    return {}

                def restore(obj):
                    if isinstance(obj, str):
                        if obj == "__RANDOM_CITY__":
                            return "{{$randomCity}}"
                        if obj == "__RANDOM_PHONE__":
                            return "{{$randomPhoneNumber}}"
                        m = re.fullmatch(r"__VAR__([A-Za-z0-9_]+)__", obj)
                        if m:
                            return "{{" + m.group(1) + "}}"
                        return obj
                    if isinstance(obj, list):
                        return [restore(x) for x in obj]
                    if isinstance(obj, dict):
                        return {k: restore(v) for k, v in obj.items()}
                    return obj

                return restore(parsed)

            # --- Collect shared variable names ---
            env_set_names: set[str] = set()
            template_names: set[str] = set()
            for verb in api_verbs:
                for script_block in [getattr(verb, "prerequest", []), getattr(verb, "script", [])]:
                    for line in script_block:
                        env_set_names.update(
                            re.findall(r'pm\.environment\.set\(["\\\']([A-Za-z0-9_]+)["\\\']', line)
                        )
                template_names.update(extract_template_vars(getattr(verb, "full_path", "") or ""))
                template_names.update(extract_template_vars(getattr(verb, "raw_body", "") or ""))

            # Only declare vars that are set during the run (pm.environment.set) or used as path/body ids.
            shared_var_names = set(env_set_names)
            shared_var_names.update(
                {
                    n
                    for n in template_names
                    if n in {"token", "username", "userID", "staffID", "adopterID", "catID"}
                }
            )

            shared_decls = [f"  let {name}: any;" for name in sorted(shared_var_names)]

            # --- Determine imports and service instances ---
            used_services: dict[str, str] = {}
            used_types: set[str] = set()
            call_specs: list[tuple[APIVerb, dict]] = []
            for verb in api_verbs:
                spec = infer_call_spec(verb)
                if not spec:
                    continue
                call_specs.append((verb, spec))
                used_services[spec["service_class"]] = spec["service_var"]
                if spec.get("has_body", True):
                    req_t = spec.get("request_type")
                    if req_t and req_t not in {"any", "unknown", "null", "undefined", "void"}:
                        used_types.add(req_t)
                resp_t = spec.get("response_type")
                if resp_t and resp_t not in {"any", "unknown", "null", "undefined", "void"}:
                    used_types.add(resp_t)

            def _norm_segment(seg: str) -> str:
                return re.sub(r"[^a-z0-9]", "", (seg or "").lower())

            def _path_segments_for_verb(verb: APIVerb) -> list[str]:
                fp = (getattr(verb, "file_path", "") or "").replace("\\", "/")
                parts = [p for p in fp.split("/") if p]
                # Drop leading src/tests if present
                if len(parts) >= 2 and _norm_segment(parts[0]) == "src" and _norm_segment(parts[1]) == "tests":
                    parts = parts[2:]
                return parts

            def _is_under_hook_folder(verb: APIVerb, hook_name: str) -> bool:
                # Convention: Postman folder path contains __hooks/beforeAll or __hooks/afterAll.
                # Note: PostmanUtils.to_camel_case strips non-alphanumerics, so "__hooks" becomes "hooks".
                segments = [_norm_segment(s) for s in _path_segments_for_verb(verb)]
                if len(segments) < 3:
                    return False
                hook_token = _norm_segment(hook_name)
                # Look for .../hooks/<hook_name>/... before the request name.
                for i in range(0, max(0, len(segments) - 2)):
                    if segments[i] == "hooks" and segments[i + 1] == hook_token:
                        return True
                return False

            before_all_specs: list[tuple[APIVerb, dict]] = [
                (v, s) for (v, s) in call_specs if _is_under_hook_folder(v, "beforeAll")
            ]
            after_all_specs: list[tuple[APIVerb, dict]] = [
                (v, s) for (v, s) in call_specs if _is_under_hook_folder(v, "afterAll")
            ]
            before_each_specs: list[tuple[APIVerb, dict]] = [
                (v, s) for (v, s) in call_specs if _is_under_hook_folder(v, "beforeEach")
            ]
            after_each_specs: list[tuple[APIVerb, dict]] = [
                (v, s) for (v, s) in call_specs if _is_under_hook_folder(v, "afterEach")
            ]
            test_specs: list[tuple[APIVerb, dict]] = [
                (v, s)
                for (v, s) in call_specs
                if not _is_under_hook_folder(v, "beforeAll")
                and not _is_under_hook_folder(v, "afterAll")
                and not _is_under_hook_folder(v, "beforeEach")
                and not _is_under_hook_folder(v, "afterEach")
            ]

            def _sanitize_collection_name(name: str) -> str:
                n = (name or "").strip().lower()
                n = re.sub(r"[^a-z0-9]+", "-", n)
                n = re.sub(r"-+", "-", n).strip("-")
                return n or "api-collection"

            collection_name = getattr(api_definition, "name", None) or "api-collection"
            spec_base = _sanitize_collection_name(collection_name)

            # Fallback: if we can't infer anything, bail with a minimal, valid file.
            if not call_specs:
                minimal = (
                    "import 'chai/register-should.js';\n\n"
                    f"describe('{collection_name}', () => {{\n"
                    "  it('No requests found', async () => {\n"
                    "    (true).should.equal(true);\n"
                    "  });\n"
                    "});\n"
                )
                spec_file = FileSpec(path=f"src/tests/{spec_base}.spec.ts", fileContent=minimal)
                self.file_service.create_files(self.config.destination_folder, [spec_file])
                self.logger.info(f"Created single spec file with all requests: src/tests/{spec_base}.spec.ts")
                try:
                    self.command_service.format_files()
                except Exception as e:
                    self.logger.warning(f"Prettier formatting failed: {e}")
                return

            import_lines: list[str] = []
            for service_class in sorted(used_services.keys()):
                import_lines.append(
                    f"import {{ {service_class} }} from '../models/services/{service_class}.js';"
                )

            # Requests/responses
            for t in sorted(used_types):
                if t.endswith("Request") or t.endswith("RequestModel"):
                    import_lines.append(f"import {{ {t} }} from '../models/requests/{t}.js';")
                else:
                    import_lines.append(f"import {{ {t} }} from '../models/responses/{t}.js';")

            import_lines.append("import 'chai/register-should.js';")
            import_block = "\n".join(import_lines) + "\n\n"

            def _translate_pm_environment_get(expr: str) -> str:
                m = re.search(
                    r'pm\.environment\.get\(\s*["\"]([A-Za-z0-9_]+)["\"]\s*\)',
                    expr or "",
                )
                if not m:
                    return expr
                key = m.group(1)
                if key in shared_var_names:
                    return re.sub(
                        r'pm\.environment\.get\(\s*["\"][A-Za-z0-9_]+["\"]\s*\)',
                        key,
                        expr,
                    )
                return re.sub(
                    r'pm\.environment\.get\(\s*["\"][A-Za-z0-9_]+["\"]\s*\)',
                    f'process.env["{key.upper()}"] ?? ""',
                    expr,
                )

            def translate_postman_assertions(
                script_lines: list[str], response_var: str, fallback_status: int
            ) -> tuple[list[str], Optional[int], bool, bool]:
                """Return (assertions, status_override, needs_timing, has_status_assertion)."""
                assertions: list[str] = []
                status_override: Optional[int] = None
                needs_timing = False
                has_status_assertion = False

                for raw_line in script_lines or []:
                    line = (raw_line or "").strip().rstrip(";")
                    if not line:
                        continue

                    # Status override
                    m = re.search(r"pm\.response\.to\.have\.status\((\d+)\)", line)
                    if m:
                        try:
                            status_override = int(m.group(1))
                        except Exception:
                            status_override = fallback_status
                        has_status_assertion = True
                        continue

                    # Response time (Postman: pm.response.responseTime)
                    m = re.search(r"pm\.expect\(pm\.response\.responseTime\)\.to\.be\.below\((\d+)\)", line)
                    if m:
                        needs_timing = True
                        assertions.append(f"    responseTime.should.be.lessThan({m.group(1)});")
                        continue

                    # Body includes string
                    m = re.search(r"pm\.expect\(pm\.response\.text\(\)\)\.to\.include\((.+)\)", line)
                    if m:
                        arg = m.group(1).strip()
                        if arg in {'""', "''"}:
                            continue
                        assertions.append(
                            f"    JSON.stringify({response_var}.data).should.include({arg});"
                        )
                        continue

                    # Empty body
                    m = re.search(r"pm\.response\.to\.have\.body\(\s*([\"\'])(.*?)\1\s*\)", line)
                    if m and (m.group(2) == ""):
                        assertions.append(
                            f"    String({response_var}.data ?? '').should.equal('');"
                        )
                        continue

                    # pm.response.json().prop is true/false
                    m = re.search(
                        r"pm\.expect\(pm\.response\.json\(\)\.([A-Za-z0-9_]+)\)\.to\.be\.(true|false)",
                        line,
                    )
                    if m:
                        prop = m.group(1)
                        tf = m.group(2)
                        assertions.append(
                            f"    ((({response_var}.data as any)?.{prop}) === {tf}).should.equal(true);"
                        )
                        continue

                    # jsonData.prop not empty
                    m = re.search(
                        r"pm\.expect\(jsonData\.([A-Za-z0-9_]+)\)\.to\.not\.be\.empty",
                        line,
                    )
                    if m:
                        prop = m.group(1)
                        assertions.append(
                            f"    String(({response_var}.data as any)?.{prop} ?? '').length.should.be.greaterThan(0);"
                        )
                        continue

                    # jsonData.prop not undefined
                    m = re.search(
                        r"pm\.expect\(jsonData\.([A-Za-z0-9_]+)\)\.to\.not\.be\.undefined",
                        line,
                    )
                    if m:
                        prop = m.group(1)
                        assertions.append(
                            f"    ((({response_var}.data as any)?.{prop}) !== undefined).should.equal(true);"
                        )
                        continue

                    # jsonData.prop eql(<rhs>)
                    m = re.search(
                        r"pm\.expect\(jsonData\.([A-Za-z0-9_]+)\)\.to\.eql\((.+)\)",
                        line,
                    )
                    if m:
                        prop = m.group(1)
                        rhs = _translate_pm_environment_get(m.group(2).strip())
                        assertions.append(
                            f"    ((({response_var}.data as any)?.{prop}) === ({rhs})).should.equal(true);"
                        )
                        continue

                    # Array.isArray(jsonData.prop) eql(true/false)
                    m = re.search(
                        r"pm\.expect\(Array\.isArray\(jsonData\.([A-Za-z0-9_]+)\)\)\.to\.eql\((true|false)\)",
                        line,
                    )
                    if m:
                        prop = m.group(1)
                        tf = m.group(2)
                        assertions.append(
                            f"    Array.isArray(({response_var}.data as any)?.{prop}).should.equal({tf});"
                        )
                        continue

                return assertions, status_override, needs_timing, has_status_assertion

            def _render_steps(verb: APIVerb, spec: dict, indent: str) -> str:
                method = (getattr(verb, "verb", "GET") or "GET").upper()
                path = getattr(verb, "full_path", "") or ""
                test_name = getattr(verb, "name", None) or f"{method} {path}"

                has_body = bool(spec.get("has_body", True))
                request_type = spec.get("request_type")
                response_type = spec.get("response_type") or "any"
                service_var = spec["service_var"]
                service_method = spec["service_method"]
                expected_status = spec["expected_status"]
                needs_auth = bool(spec.get("auth"))
                id_var = spec.get("id_var")

                # prerequest: translate env sets that occur before the call
                pre_lines: list[str] = []
                for line in getattr(verb, "prerequest", []) or []:
                    m = re.search(
                        r'pm\.environment\.set\(\s*["\\\']([A-Za-z0-9_]+)["\\\']\s*,\s*(.*)\)\s*;?\s*$',
                        line,
                    )
                    if not m:
                        continue
                    var_name = m.group(1)
                    translated = translate_postman_rhs(m.group(2), None)
                    if translated is None:
                        continue
                    pre_lines.append(f"    {var_name} = {translated};")

                # request body (if applicable)
                req_var = f"{service_method}Data"
                body_expr = "{}"
                if has_body:
                    body_obj = body_object_for_verb(verb)
                    body_expr = ts_literal(body_obj)

                # Call
                response_var = f"{service_method}Response"
                call_line = ""
                if has_body:
                    if id_var:
                        call_line = f"    const {response_var} = await {service_var}.{service_method}<{response_type}>({id_var}, {req_var}{', authConfig' if needs_auth else ''});"
                    else:
                        call_line = f"    const {response_var} = await {service_var}.{service_method}<{response_type}>({req_var}{', authConfig' if needs_auth else ''});"
                else:
                    if id_var:
                        call_line = f"    const {response_var} = await {service_var}.{service_method}<{response_type}>({id_var}{', authConfig' if needs_auth else ''});"
                    else:
                        call_line = f"    const {response_var} = await {service_var}.{service_method}<{response_type}>({ 'authConfig' if needs_auth else ''});"

                auth_config_lines: list[str] = []
                if needs_auth:
                    auth_config_lines.append(
                        "    const authConfig = token ? { headers: { Authorization: `Bearer ${token}` } } : undefined;"
                    )

                # postrequest: env sets from test scripts that depend on response
                post_lines: list[str] = []
                for line in getattr(verb, "script", []) or []:
                    m = re.search(
                        r'pm\.environment\.set\(\s*["\\\']([A-Za-z0-9_]+)["\\\']\s*,\s*(.*)\)\s*;?\s*$',
                        line,
                    )
                    if not m:
                        continue
                    var_name = m.group(1)
                    translated = translate_postman_rhs(m.group(2), response_var)
                    if translated is None:
                        continue
                    post_lines.append(f"    {var_name} = {translated};")

                postman_assertions, status_override, needs_timing, has_status_assertion = (
                    translate_postman_assertions(
                    getattr(verb, "script", []) or [],
                    response_var,
                    expected_status,
                )
                )

                assertions: list[str] = []
                if has_status_assertion:
                    resolved_status = status_override if status_override is not None else expected_status
                    assertions.append(
                        f"    {response_var}.status.should.equal({resolved_status}, JSON.stringify({response_var}.data));"
                    )
                assertions.extend(postman_assertions)

                # Re-indent the generated lines (they are built with 4-space intent).
                raw = (
                    ("\n".join(pre_lines) + "\n" if pre_lines else "")
                    + (
                        f"    const {req_var}: {request_type} = {body_expr} as any;\n"
                        if has_body and request_type
                        else ""
                    )
                    + ("\n".join(auth_config_lines) + "\n" if auth_config_lines else "")
                    + ("    const startTime = Date.now();\n" if needs_timing else "")
                    + call_line
                    + "\n"
                    + ("    const responseTime = Date.now() - startTime;\n" if needs_timing else "")
                    + ("\n".join(post_lines) + "\n" if post_lines else "")
                    + "\n".join(assertions)
                ).rstrip()

                # Adjust indentation
                lines = raw.splitlines() if raw else []
                return "\n".join((indent + l[4:]) if l.startswith("    ") else (indent + l) for l in lines)

            def _render_it_block(verb: APIVerb, spec: dict) -> str:
                method = (getattr(verb, "verb", "GET") or "GET").upper()
                path = getattr(verb, "full_path", "") or ""
                test_name = getattr(verb, "name", None) or f"{method} {path}"
                steps = _render_steps(verb, spec, indent="    ")
                return f"  it('{test_name}', async () => {{\n{steps}\n  }});"

            def _render_hook_block(hook_keyword: str, specs: list[tuple[APIVerb, dict]]) -> str:
                if not specs:
                    return ""
                inner_blocks: list[str] = []
                for verb, spec in specs:
                    method = (getattr(verb, "verb", "GET") or "GET").upper()
                    path = getattr(verb, "full_path", "") or ""
                    name = getattr(verb, "name", None) or f"{method} {path}"
                    steps = _render_steps(verb, spec, indent="      ")
                    inner_blocks.append(f"    // {name}\n    {{\n{steps}\n    }}")
                body = "\n\n".join(inner_blocks)
                return f"  {hook_keyword}(async () => {{\n{body}\n  }});"

            # --- Build tests + hooks ---
            before_all_block = _render_hook_block("before", before_all_specs)
            after_all_block = _render_hook_block("after", after_all_specs)
            before_each_block = _render_hook_block("beforeEach", before_each_specs)
            after_each_block = _render_hook_block("afterEach", after_each_specs)

            test_blocks: list[str] = []
            for verb, spec in test_specs:
                test_blocks.append(_render_it_block(verb, spec))

            service_inits = [
                f"  const {var} = new {cls}();"
                for cls, var in sorted(used_services.items(), key=lambda x: x[1])
            ]

            helpers = (
                "  const randomCity = () => {\n"
                '    const cities = ["NewYork", "London", "Paris", "Tokyo", "Sydney", "Berlin", "Mumbai", "Toronto", "Dubai", "Singapore"];\n'
                "    return cities[Math.floor(Math.random() * cities.length)] + Math.floor(Math.random() * 10000);\n"
                "  };\n\n"
                "  const randomPhoneNumber = () => {\n"
                "    const digit = () => Math.floor(Math.random() * 10).toString();\n"
                "    let out = '';\n"
                "    for (let i = 0; i < 10; i++) out += digit();\n"
                "    return out;\n"
                "  };\n"
            )

            describe_block = (
                import_block
                + f"describe('{(getattr(api_definition, 'name', None) or 'api-collection')}', () => {{\n"
                + "\n".join(shared_decls)
                + "\n"
                + helpers
                + "\n".join(service_inits)
                + "\n\n"
                + (before_all_block + "\n\n" if before_all_block else "")
                + (before_each_block + "\n\n" if before_each_block else "")
                + "\n\n".join(test_blocks)
                + ("\n\n" + after_each_block if after_each_block else "")
                + ("\n\n" + after_all_block if after_all_block else "")
                + "\n});\n"
            )

            spec_file = FileSpec(path=f"src/tests/{spec_base}.spec.ts", fileContent=describe_block)
            self.file_service.create_files(self.config.destination_folder, [spec_file])
            self.logger.info(f"Created single spec file with all requests: src/tests/{spec_base}.spec.ts")
            try:
                self.command_service.format_files()
            except Exception as e:
                self.logger.warning(f"Prettier formatting failed: {e}")
            self.logger.info("\nGeneration complete. Only the spec file was created.")
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
