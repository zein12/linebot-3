#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import hmac
import hashlib
import base64
import json
import requests

from flask import Flask
from flask import request

import redis
from rq import Queue
from worker import conn

app = Flask(__name__)
channelSecret = os.environ['LINE_CHANNEL_SECRET']
channelAccessToken = os.environ['LINE_CHANNEL_ACCESS_TOKEN']

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)
workerQueue = Queue('default', connection=conn)

def verifySignature(signature, requestBody):
    digest = hmac.new(channelSecret, requestBody, hashlib.sha256).digest()
    return signature == base64.b64encode(digest)

def replyMessage(token, message):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + channelAccessToken
    }
    data = {
        'replyToken': token,
        'messages': [
            {
                'type': 'text',
                'text': message
            }
        ]
    }
    requests.post('https://api.line.me/v2/bot/message/reply', headers=headers, data=json.dumps(data))
    return

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    requestBody = request.data
    if verifySignature(signature, requestBody) == False:
        print "Signature mismatched"
        return json.dumps('')
    data = json.loads(requestBody)
    for event in data['events']:
        replyToken = event['replyToken']
        if event['type'] == 'message':
            text = event['message']['text']
            workerQueue.enqueue_call(func=replyMessage, args=(replyToken, text), timeout=30)
    return json.dumps('')

if __name__ == "__main__":
    app.run()
