from typing import Any, Callable
# from fastapi import APIRouter
from myfastapi.routing import ApiRouter
import starlette
from starlette.types import Receive, Send, Scope

class FastApi(starlette):
    def __init__(
        self,
        version: str = "0.1.0"
    ) -> None:
        self.version = version
    self.router: APIRouter = APIRouter()
        
    def get(
        self,
        path: str,
    ) -> Callable[..., Any]:
        return self.router.get(path)    
    
    def post(
        self,
        path: str,
    ) -> Callable[..., Any]:
        return self.router.post(path)
    
    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        await super().__call__(scope, receive, send)

async def app(scope, receive, send):
    """
    Echo the request body back in an HTTP response.
    """
    body = await read_body(receive)
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            [b'content-type', b'text/plain'],
        ]
    })
    await send({
        'type': 'http.response.body',
        'body': body,
    })        