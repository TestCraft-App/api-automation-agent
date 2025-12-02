from typing import List, Dict, Any

from pydantic import BaseModel, Field

from .model_file_spec import ModelFileSpec


class ModelCreationInput(BaseModel):
    files: List[Dict[str, Any]] = Field(
        description="A list of dicts, each containing a 'path' (string), 'fileContent' (string), and 'summary' (string) key. "
        "'fileContent' should be a valid TypeScript/JavaScript code string with proper escaping for special characters.",
        examples=[
            [
                {
                    "path": "./UserService.ts",
                    "fileContent": "export class PetService extends ServiceBase {...}",
                    "summary": "User service: addUser, updateUser, deleteUser, getUserById, getUsers",
                },
                {
                    "path": "./../UserModel.ts",
                    "fileContent": "export interface UserModel {...}",
                    "summary": "User model. Properties: id, name, email, password",
                },
            ]
        ],
    )
