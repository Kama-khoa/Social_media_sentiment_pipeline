from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from elt.quota_budget import QuotaBudget

if TYPE_CHECKING:
    from elt.extract.comment_extractor import CommentExtractor


class BaseExtractor(ABC):

    @abstractmethod
    def run_daily(
        self,
        execution_date: str,
        dag_run_id: str,
        budget: QuotaBudget,
        comment_extractor: Optional[CommentExtractor] = None,
    ) -> dict:
        ...

    @abstractmethod
    def run_historical(
        self,
        execution_date: str,
        dag_run_id: str,
        budget: QuotaBudget,
        comment_extractor: Optional[CommentExtractor] = None,
    ) -> dict:
        ...
