from typing import Union
from myfastapi.applications import FastAPI
# from fastapi import FastAPI
from starlette.responses import JSONResponse
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    description: Union[str, None] = None
    price: float
    tax: Union[float, None] = None


app = FastAPI()


@app.get("/")
async def homepage():
    return JSONResponse({'hello': 'world'})

@app.post("/items/{item_id}")
async def create_item(item: Item, item_id: int):
    return JSONResponse({"item": item.dict(), "item_id": item_id})

@app.get("/get_items/{item_id}")
async def read_item(item_id: int):
    print("item_id", item_id)
    return {"item_id": item_id}