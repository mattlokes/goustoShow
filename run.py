import os
import requests
import re
import json
import random
from flask import Flask, request, jsonify, render_template, url_for
from flask_socketio import SocketIO

from recipe_scrapers import scrape_me

import pdb

app = Flask(__name__)
socketio = SocketIO(app)

viewPorts = {}

def recipeIdLookup( id ):
    lookup = f"https://production-api.gousto.co.uk/cmsreadbroker/v1/recipe-by-id/{id}"
    response = requests.get(lookup)
    suffix = response.json()['data']['entry']['url']
    return f"https://www.gousto.co.uk/cookbook/recipes{suffix}"


@app.route('/')
def index():
    host = url_for('index',_external=True)
    context ={ 'wsUrl'   : f"{host}",
             }
    return render_template('index.html', **context)

@socketio.on('connect')
def connect():
    global viewPorts #YUCK!
 
    host = url_for('index',_external=True)
    vp = request.sid
    viewPorts[vp] = True

    print(f"[{vp}] - CONNECT")

    socketio.emit('init', 
            {'vp'      : vp, 
             'pushUrl' : f"{host}/push?vp={vp}&rurl=",})

@socketio.on('disconnect')
def disconnect():
    global viewPorts #YUCK!
    
    vp = request.sid
    print(f"[{vp}] - DISCONNECT")

    #Recycle ViewPort
    viewPorts.pop(vp)
    


@app.route('/push')
def push():
    rUrl= request.args.get('rurl')
    vp  = request.args.get('vp', 0)

    print(request.args)

    m = re.match(r'.*recipeDetailId=([0-9]+).*', rUrl)
    if m is None:
        return jsonify({'success': False, 'info': "No recipeDetailId!"})
    rId = m.group(1)

    cUrl = recipeIdLookup(rId)
    print(f"[{vp}] - PUSH: {cUrl}")
    
    r = scrape_me(cUrl)

    print(r.title())
    print(r.image())

    socketio.emit("push",{
        'title': r.title(),
        'img'  : r.image(),
        },to=vp)

    return jsonify({'success'    : True, 
                    'recipeId'   : rId, 
                    'recipeTitle': r.title(), 
                    'viewPort'   : vp, })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=os.environ.get('GS_PORT',54321))
