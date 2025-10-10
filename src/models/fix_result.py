from typing import List, Optional
from pydantic import BaseModel
from src.ai_tools.models.file_spec import FileSpec
from src.ai_tools.models.test_fix_input import FixStop


class FixResult(BaseModel):
    fixed_files: List[FileSpec]
    changes: Optional[str]
    stop: Optional[FixStop]
