from typing import List

from pydantic import BaseModel, Field

from .model_file_spec import ModelFileSpec


class ModelCreationInput(BaseModel):
    files: List[ModelFileSpec] = Field(
        description="A list of dicts, each containing a 'path', 'fileContent', and 'summary' key. "
        "'fileContent' should be a valid JSON string enclosed in double quotes, with any "
        "special characters properly escaped.",
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
