from typing import List, Optional

from pydantic import BaseModel, Field


class CacheDetails(BaseModel):
    cache_read: int = 0
    cache_creation: int = 0


class LLMCallUsageData(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_token_details: Optional[CacheDetails] = None
    cost: Optional[float] = None


class AggregatedUsageMetadata(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cache_details: CacheDetails = Field(default_factory=CacheDetails)
    total_cost: float = 0.0
    total_fix_attempts: int = 0
    call_details: List[LLMCallUsageData] = Field(default_factory=list)

    def add_call_usage(self, usage_data: LLMCallUsageData):
        """Helper method to update totals and append details."""
        self.total_input_tokens += usage_data.input_tokens
        self.total_output_tokens += usage_data.output_tokens
        self.total_tokens += usage_data.total_tokens
        if usage_data.cost is not None:
            self.total_cost += usage_data.cost
        if usage_data.input_token_details:
            self.total_cache_details.cache_read += usage_data.input_token_details.cache_read
            self.total_cache_details.cache_creation += usage_data.input_token_details.cache_creation
        self.call_details.append(usage_data)

    def increment_fix_attempts(self, count: int = 1):
        """Increment the total number of fix attempts recorded for this run."""
        if count < 0:
            raise ValueError("count must be non-negative")
        self.total_fix_attempts += count
