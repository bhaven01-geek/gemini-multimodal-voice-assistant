# server 
 
import os
import time
import json
import uvicorn
import requests
from loguru import logger
from datetime import datetime, timezone
from google.cloud import storage
from botv2 import run_bot
from utils import (read_csv_from_gcs, add_data_to_firestore, get_user_details_from_firestore,
                   get_call_details, get_phonenumbers_from_collection, get_send_at)
from fastapi import FastAPI, WebSocket , Request, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()


app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],  # Allow all origins for testing
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
   """Websocket connection from telephony endpoint
   Args:
       request: The incoming Websocket connection request object from Telephony.
   """
   websocket_receive = time.time()
  
   await websocket.accept()
   start_data = websocket.iter_text()
   await start_data.__anext__()
   websocket_accept = time.time()
   logger.info("Websocket connection accepted")
  
   call_data = json.loads(await start_data.__anext__())
   stream_sid = call_data['start']['stream_sid']
   phone_number = call_data['start']['from']
   custom_params = call_data['start'].get('custom_parameters')
   if custom_params:
       collection_id = custom_params.get('collection_id', '')
   else:
       collection_id = ''
   websocket_time = websocket_accept - websocket_receive
   logger.info(f"{stream_sid} : Websocket Accepted : {websocket_time:.4f} seconds")


   query_start = time.time()
   if phone_number:
       # Fetch user metadata from firestore
       sop_data = get_user_details_from_firestore(phone_number, collection_id)
   query_end = time.time()
   firestore_time = query_end - query_start
   logger.info(f"{stream_sid} : DB Query Time: {firestore_time:.4f} seconds")
  
   await run_bot(websocket, stream_sid, sop_data=sop_data, websocket_start_time=websocket_time+firestore_time)


if __name__ == "__main__":
   uvicorn.run(app, host="0.0.0.0", port=8080)