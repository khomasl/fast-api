from typing import Any, Callable, List, Optional
from pydantic.fields import ModelField
 
class Dependant:
    def __init__(
        self,
        *,
        path_params: Optional[List[ModelField]] = None,
        query_params: Optional[List[ModelField]] = None,
        body_params: Optional[List[ModelField]] = None,
        call: Optional[Callable[..., Any]] = None,
        path: Optional[str] = None
    ) -> None:
        self.path_params = path_params or []
        self.query_params = query_params or []
        self.body_params = body_params or []
        self.call = call
        self.path = path