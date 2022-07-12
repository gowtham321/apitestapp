from typing import List
from webbrowser import get
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()

class Item(BaseModel):
    name: str
    description: str | None
    price: str
    tax: str
    salesCount: str
    
@app.post("/createReport/")    
def create_report(item: Item):
    #app logic goes here
    items = item.dict()
    return({"Processed data": "Success","items":items})