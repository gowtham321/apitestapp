import csv
from typing import List
from webbrowser import get
from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np 
import pandas as pd
import time, warnings
import datetime as dt


app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

class ItemURL(BaseModel):
    url: str
    #integrate all the necessary models into the class item
    
    
@app.post("/createReport/") #only have option params in the function createReport
def createReport(csvlink: ItemURL, invoiceDate: str = "InvoiceDate", 
 customerId: str = "CustomerID", quantity: str = "Quantity",
  invoiceNo: str = "InvoiceNo", country: str = 'Country',
  unitPrice: str = "UnitPrice"):

    file_id = csvlink.url.split('/')[-2]
    dwn_url='https://drive.google.com/uc?id=' + file_id
    print(dwn_url)
    retailData = pd.read_csv(dwn_url, encoding= 'unicode_escape')
    retailData = retailData[retailData[quantity]>0]
    retailData.dropna(subset=[customerId],how='all',inplace=True)

    #to - do restrict data to year or months based on request

#Recency calculation
    now = dt.date.today() #current date to calculate recency
    retailData['date'] = pd.DatetimeIndex(retailData[invoiceDate]).date
    recency_df = retailData.groupby(by=customerId, as_index=False)['date'].max()
    recency_df.columns = [customerId,'LastPurshaceDate']
    recency_df['Recency'] = recency_df['LastPurshaceDate'].apply(lambda x: (now - x).days)
    recency_df.drop('LastPurshaceDate',axis=1,inplace=True)

#Frequency calculation
    retail_copy = retailData #copy used for calculating the frequency
    retail_copy.drop_duplicates(subset=[invoiceNo,customerId], keep='first', inplace=True)
    frequency_df = retail_copy.groupby(by=[customerId], as_index=False)['InvoiceNo'].count()
    frequency_df.columns = [customerId,'Frequency']

#Monetary calculation
    retailData['TotalCost'] = retailData[quantity] * retailData['UnitPrice']
    monetary_df = retailData.groupby(by=customerId,as_index=False).agg({'TotalCost': 'sum'})
    monetary_df.columns = [customerId,'Monetary']


    temp_df = recency_df.merge(frequency_df,on=customerId)
    rfm_df = temp_df.merge(monetary_df,on=customerId)
    rfm_df.set_index(customerId,inplace=True)
    quantiles = rfm_df.quantile(q=[0.25,0.5,0.75])
    quantiles.to_dict()

    def RScore(x,p,d):
        if x <= d[p][0.25]:
            return 4
        elif x <= d[p][0.50]:
            return 3
        elif x <= d[p][0.75]: 
            return 2
        else:
            return 1

    def FMScore(x,p,d):
        if x <= d[p][0.25]:
            return 1
        elif x <= d[p][0.50]:
            return 2
        elif x <= d[p][0.75]: 
            return 3
        else:
            return 4
    
    rfm_segmentation = rfm_df
    rfm_segmentation['R_Quartile'] = rfm_segmentation['Recency'].apply(RScore, args=('Recency',quantiles,))
    rfm_segmentation['F_Quartile'] = rfm_segmentation['Frequency'].apply(FMScore, args=('Frequency',quantiles,))
    rfm_segmentation['M_Quartile'] = rfm_segmentation['Monetary'].apply(FMScore, args=('Monetary',quantiles,))
    rfm_segmentation['RFMScore'] = rfm_segmentation.R_Quartile.map(str) \
                            + rfm_segmentation.F_Quartile.map(str) \
                            + rfm_segmentation.M_Quartile.map(str)

    return rfm_segmentation.to_json(orient='index')
