from typing import Callable, Coroutine

import asyncio

from pydantic import ValidationError

from fastapi import Request, Response
from fastapi.exceptions import RequestErrorModel
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.routing import request_response, Router, Any

from myfastapi.dependencies.models import Dependant
from myfastapi.dependencies.utils import get_dependant, get_request_handler, solve_dependencies, run_endpoint_function

class APIRouter(Router):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        method: str
    ) -> None:
        super().__init__()
        self.route_class = APIRoute
        self.path = path
        self.endpoint = endpoint
        self.method = method
        assert callable(endpoint), "An endpoint must be a callable"
        self.dependant = get_dependant(path=self.path, call=self.endpoint)
        self.app = request_response(get_request_handler(dependant=self.dependant))

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
	    method: str
    ) -> None:
        route = self.route_class(
        path, 
        endpoint=endpoint, 
        method=method
        )
        self.routes.append(route)

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self.add_api_route(path, func, method="get")
                return func
            return decorator

    def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self.add_api_route(path, func, method="post")
                return func
            return decorator    
    
    def get_request_handler(
        dependant: Dependant,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
            is_coroutine = asyncio.iscoroutinefunction(dependant.call)
            async def app(request: Request) -> Response:
                body = None
                if dependant.body_params:
                    body = await request.json()
                solved_result = await solve_dependencies(
                    request=request,
                    dependant=dependant,
                    body=body
                )
                values, errors = solved_result
                if errors: raise ValidationError(errors, RequestErrorModel)

                raw_response = await run_endpoint_function(
                    dependant=dependant, values=values, is_coroutine=is_coroutine
                )
                if isinstance(raw_response, Response): return raw_response
                if isinstance(raw_response, (dict, str, int, float, type(None))):
                    return JSONResponse(raw_response)
                else: raise Exception("Type of response is not supported yet.")

            return app