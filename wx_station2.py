from fastapi import FastAPI, Request, Form
from fastapi.responses import  HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from datetime import datetime
import time
import json
import asyncio
from pydantic import BaseModel
from typing import Annotated
import websockets
import asyncio
import aiohttp
import json
import uuid
import time
import numpy as np


session = {}
PORT = 7890
CHAT_USERNAMES = []
print(f"started Server and its listening on port:{PORT}")

connected = {}
COMMANDS = {"init", "close", "message"}
ZIP_CODES = []
TAF = {}
WX = {}
OLD_IP = ""
LAST_UPDATE = 0
last_update_time = 0
DATA = {"display": {"data": ''}, "users": {}, "wx": {}, "metar": {"Airport ID": ["METAR"]}}
PORT = 7890
print(f"started Server and its listening on port:{PORT}")
ZIP = None

# Generic SSE Server to build on.
app = FastAPI()
templates = Jinja2Templates(directory= "templates")
app.mount("/static", StaticFiles(directory="static"), name= "static")

#video_stream = cv2.VideoCapture(-1)

class Chat_window(BaseModel):
	submit: str = None
	model_config = {"extra": "allow"}

class Add_user(BaseModel):
    add_user: str = None
    user_id: str = None
    log_out: str = None
    model_config = {"extra": "allow"}

class Input(BaseModel):
    value: str = None
    submit: str = None
    model_config = {"extra": "allow"}


OBJECTS = {}
config_data = {"dial_1" : 0, "message": {"status":" "}}


@app.get("/", response_class=HTMLResponse)  
async def main(req: Request):
	return templates.TemplateResponse(
		name="wx_station_async.html",
		context={"request": req, "session": session}
		) 
@app.get("/metar", response_class=HTMLResponse)  
async def metar_get(req: Request):
	return templates.TemplateResponse(
		name="metar_async.html",
		context={"request": req, "session": session}
    )
@app.get("/taf", response_class=HTMLResponse)  
async def taf_get(req: Request):
	return templates.TemplateResponse(
		name="taf_async.html",
		context={"request": req, "session": session}
    )
@app.post("/chat", response_class=HTMLResponse)
def chat(req: Request, form_data: Annotated[Chat_window, Form()]):
        if form_data.submit:
            session["chat"] = True
            if "user_id" not in session or session["user_id"] == None:
                session["val"] = "Welcome, please log in!"
                print("New login requested")
            print("Chat window opened")
            return templates.TemplateResponse(
                name="wx_station_async.html",
		        context={"request": req, "session": session}
            )
@app.get("/chat", response_class=HTMLResponse)
async def chat_get(req: Request):
    return templates.TemplateResponse(
        name="chat_async.html",
		context={"request": req, "session": session}
    )
@app.post("/add_user", response_class=HTMLResponse)
async def add_user(req: Request, form_data: Annotated[Add_user, Form()]):
    if form_data.user_id and form_data.user_id != '':
        user = form_data.user_id
        if user in DATA["users"]:
            session["val"] = "Username already in use!!!"
        else:
            session["user_id"]  = user
            DATA["users"][user] = None
            DATA["display"]["data"] = ''
            print(f"added user: {user}")
    elif form_data.add_user and form_data.user_id == '':
        session["val"] = "Username Cannot be blank!!!"
    elif form_data.log_out:
        _log_out()
    return templates.TemplateResponse(
        name="chat_async.html",
		context={"request": req, "session": session}
    )
@app.get("/add_user")
async def add_user_get():
    html = "<html><body><h1>You are logged out!</h1></body><script>setTimeout(() => window.close(), 3000)</script></html>"
    _log_out()
    print("Logout")
    return HTMLResponse(content=html, status_code=200)
	
@app.get("/users", response_class=HTMLResponse)
def users(req: Request):
    return templates.TemplateResponse(
        name="users.html",
		context={"request": req, "session": session}
    )
@app.post("/input", response_class=HTMLResponse)
def input(req: Request, form_data: Annotated[Input, Form()]):
    if form_data.submit:
        data = form_data.value if form_data.value else "Blank"
        DATA["display"] = {"user": session["user_id"], "data": data, "message_id": time.time()}
        print(DATA)
    return templates.TemplateResponse(
        name="input.html",
		context={"request": req}
    )
@app.get("/input", response_class=HTMLResponse)
def input_get(req: Request):
    return templates.TemplateResponse(
        name="input.html",
		context={"request": req}
    )
@app.get("/output", response_class=HTMLResponse)
def output(req: Request):
    return templates.TemplateResponse(
        name="output.html",
		context={"request": req}
    )
# log out function
def _log_out():
    if "user_id" in session:
        DATA["users"].pop(session['user_id'], None)
    session['user_id'] = None
    session['chat'] = False
    session['val'] = "Successfully logged out!"
    print("Logged out")
    print(DATA["users"])

#-------------------------------------------------------------------------------------------------


async def metar(airport_id):
    metar_data = None
    airport_id = airport_id.upper()
    print(airport_id) 
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://aviationweather.gov/api/data/metar?ids={airport_id}&format=json") as response:
                metar_data = await response.json()
        metar_data = metar_data[0].get("rawOb", "Not Working")
    except:
        metar_data = "Invalid Airport Code"
    print(metar_data)
    return {airport_id: metar_data}

async def taf(airport_id):
    taf_data= None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://aviationweather.gov/api/data/taf?ids={airport_id}&format=json") as response:
                taf_data = await response.json()
        taf_data = taf_data[0].get("rawTAF", None)
    except:
        taf_data = "Invalid Airport Code"
    
    return {airport_id: taf_data}
        
async def get_wx(zip):
    key = "373ee2691da6e29a8a5a3315557f8fff"
    addr = f"http://api.openweathermap.org/data/2.5/weather?zip={zip},us&appid={key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(addr) as response:
            raw_data = await response.json()
    data = raw_data
    for key, value in data.items():
        print(f"{key} : {value}")
        
    now = data["dt"]
    sun_rise = data['sys']['sunrise']
    sun_set = data['sys']['sunset']
    main = data['weather'][0]['main']
    desc = data['weather'][0]['description']
    if now < sun_rise:
        day = False
    elif sun_rise < now < sun_set:
        day = True
    elif sun_set < now:
        day = False
    else:
        day = False
    if main == "Clear" and day is True:
        logo = "sunny.png"
    elif main == "Clear" and day is False:
        logo = "moon.png"
    elif main == "Clouds" and (desc == "few clouds" or desc == "scattered clouds"):
        if day:
            logo = "few_clouds_day.png"
        else:
            logo = "few_clouds_nite_2.png"
    elif main == "Clouds" and (desc == "broken clouds" or desc == "overcast clouds"):
        logo = "cloudy_2.png"
    elif main == "Rain":
        logo = "raining.png"
    elif main == "Snow":
        logo = "snow.png"
    elif main == "Thunderstorm":
        logo = "t_storm.png"
    elif main == "Mist" or main == "Fog":
        logo = "mist.png"
    else:
        logo = "cloudy_2.png"
    temp_f = round((data["main"]["temp"]*(9/5)) - 459.67)
    temp_c = round((temp_f - 32) / 1.8, 1)
    press = data["main"]["pressure"]
    humid = data["main"]["humidity"]
    dew_point_c =243.04*(np.log(humid/100)+((17.625*temp_c)/(243.04+temp_c)))/(17.625-np.log(humid/100)-((17.625*temp_c)/(243.04+temp_c))) 
    dew_point_f = round((dew_point_c * 1.8) + 32, 1)
    dew_point_c = round(dew_point_c, 1)
    wind_speed = round(data['wind']['speed'] * 2.23694)
    gust = round(data["wind"].get("gust", 0) * 2.23694)
    wind_deg = "{:03d}".format(data['wind']['deg'])
    clouds = data['clouds']['all']
    sun_rise = datetime.fromtimestamp(sun_rise).strftime("%H:%M:%S")
    sun_set = datetime.fromtimestamp(sun_set).strftime("%H:%M:%S")
    vis = data.get("visibility", 0.0)
    now  = datetime.fromtimestamp(now).ctime()
    wind_compass = data['wind']['deg'] if data['wind']['deg'] < 359 else 0
    wind_compass = round(wind_compass / 22.5)
    lat = data['coord']['lat']
    lon = data['coord']['lon']
    name = data['name']
    compass = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        
    wx = {"wx": main, "desc": desc, "temp": temp_c, "dew_point_c": dew_point_c, "dew_point_f": dew_point_f,
            "press": press, "humid": humid, 
            "wind_dir": wind_deg, "wind_speed": wind_speed, "gust": gust,
            "compass": compass[wind_compass if wind_compass <= 15 else 15], "ceiling": clouds,
            "now": now, "sunrise": sun_rise, "sunset": sun_set, "vis": vis * 0.000621371, "logo": logo,
            "lat":lat, "lon":lon, "city":name}
    return wx
    
async def send_msg():
    while True:
        await asyncio.sleep(0.1)
        print("While running loop")
        count = 0
        for key, val in connected.copy().items():
            print(f"Key: {key} : Val: {val}")
            if "zip" in val and "last_update" in connected[key]:
                if time.time() - connected[key]["last_update"] > 60:
                    try:
                        await key.send(json.dumps({"wx": await get_wx(val["zip"]), "time": datetime.now().strftime("%c")}))
                        connected[key]["last_update"] = time.time()
                    except websockets.exceptions.ConnectionClosed:
                        connected.pop(key, None)
                        await key.close()
                        print("connecton closed in while loop")
                else:
                    try:
                        await key.send(json.dumps({"time": datetime.now().strftime("%c")}))
                    except websockets.exceptions.ConnectionClosed:
                        connected.pop(key, None)
                        await key.close()
                        print("connecton closed in while loop")

            else:
                try:
                    await key.send(json.dumps({"server": "test if connected"}))
                except websockets.exceptions.ConnectionClosed:
                    connected.pop(key, None)
                    await key.close()
                    print("connecton closed in while loop")
            count += 1
        print(f"Number of client: {count}")
async def send_chat_msg(socket, user_id, message):
    for key, val in connected.items():
        if key == socket:
            await key.send(json.dumps({"chat": {"message" : message, "from": "You"}}))
        else:
            await key.send(json.dumps({"chat": {"message" : message, "from" : user_id}}))

async def add_user(socket, user_id):
    if user_id not in CHAT_USERNAMES:
        globals()["CHAT_USERNAMES"].append(connected[socket]["chat"]["user_id"])
        print(CHAT_USERNAMES)
        del connected[socket]["chat"]["login"]
        del connected[socket]["message"]
        print(f"New User: {connected[socket]}")
        await socket.send(json.dumps({"chat" : {"user_id" : user_id}}))
        for key, val in connected.items():
            try:
                await key.send(json.dumps({"chat" : {"users" : CHAT_USERNAMES}}))
            except websockets.exceptions.ConnectionClosed as e:
                connected[key]["close"] = True
                print(f"closing connection while sending add user with {val} due to a connection already being closed")  
        
        await socket.send(json.dumps({"chat" : {"timestamp": datetime.now().strftime("%c")}}))
    else:
        await socket.send(json.dumps({"chat" : {"ERROR" : "user already exists"}}))
    

async def del_user(sock, user_id):
    if user_id in CHAT_USERNAMES:
        CHAT_USERNAMES.remove(user_id)
        for key, val in connected.items():
            try:
                if key != sock:
                    await key.send(json.dumps({"chat" : {"users" : CHAT_USERNAMES}}))
            except websockets.exceptions.ConnectionClosed as e:
                connected[key]["close"] = True
                print(f"closing connection with {val} due to a connection already being closed")
        connected[sock]["close"] = True
async def resend():
    for key in connected.keys():
        try:
            await key.send(json.dumps({"chat" : {"users" : CHAT_USERNAMES}}))
        except Exception as e:
            print(e)

async def echo(websocket):
    if websocket not in connected:
        connected.update({websocket : {}})
    try:
        async for message in websocket:
            addr = websocket.request.headers.get("Host", None).split(":")[0]
            rcvd = json.loads(message)
            print(f"Message: {rcvd}")
            print(f"Received message from {addr}, msg: {connected[websocket].get("message", None)}")
            if "init"  in rcvd:
                id = uuid.uuid4()
                connected[websocket]["addr"] = addr
                connected[websocket]["ID"] = str(id)
                connected[websocket]["close"] = False
                connected[websocket]["message"] = None
                connected[websocket]["init"] = 0
                connected[websocket]["user_id"] = None
                print(f"New Connection: {connected[websocket]}")
            elif "close" in rcvd:
                connected[websocket]["close"] = True
                connected[websocket]["message"] = connected[websocket]["ID"]
                print("close received")
                print(connected)
            else:
                print(f"ID: {connected[websocket]["ID"]}")
                print(f"_id: {rcvd["_id"]}")
                connected[websocket].update(rcvd)
            for key, val in connected.copy().items():
                try:
                    if "chat" in val:
                        if not connected[websocket]["close"] and connected[websocket]["init"] == 1:
                            if "logout" in val["chat"]:
                                if key == websocket:
                                    print("Logging out")
                                    await del_user(key, val["chat"]["user_id"])
                                    break
                                print(f"User: {val["chat"]["user_id"]} Logged out")
                            elif "login" in val["chat"]:
                                print(f"Message from: {val["chat"]["user_id"]}")
                                if key == websocket:
                                    await add_user(key, val["chat"]["user_id"]) 
                                    break
                            elif "user_id" in val["chat"]:
                                    if "message" in val["chat"] and val["chat"]["message"]:
                                        await send_chat_msg(key, val["chat"]["user_id"], val["chat"]["message"]) 
                                        del connected[key]["chat"]["message"]                    
                    elif "zip" in val:  
                        if key == websocket:
                            if not connected[websocket]["close"] and connected[websocket]["init"] == 1:
                                print("Zip was in value")
                                await key.send(json.dumps({"wx": await get_wx(val["zip"]), "time": datetime.now().strftime("%c")}))
                                connected[key]["last_update"] = time.time()
                    elif "metar" in val:
                        if key == websocket:
                            if not connected[websocket]["close"] and connected[websocket]["init"] == 1:
                                if "message" in connected[key]:
                                    del connected[key]["message"]
                                await key.send(json.dumps({"metar": await metar(val["metar"])})) 
                                connected[websocket].pop("metar", None)
                                print("sent metar")
                    elif "taf" in val:
                       if key == websocket:
                            if not connected[websocket]["close"] and connected[websocket]["init"] == 1:
                                if "message" in connected[key]:
                                    del connected[key]["message"]
                                await key.send(json.dumps({"taf": await taf(val["taf"])})) 
                                connected[websocket].pop("taf", None) 
                                print("sent taf")                         
                    if "message" in val:
                        if key != websocket: # to send message back to sender
                            if not connected[websocket]["close"] and connected[websocket]["init"] == 1:
                                if connected[websocket].get("message", None):
                                    await key.send(json.dumps({"Other": connected[websocket]["message"]}))     
                        else:                # to send a message to other recipients
                            if val["init"] == 0:
                                await key.send(json.dumps({"ID": connected[websocket]["ID"]}))
                                val["init"] = 1
                            else:
                                if connected[websocket].get("message", None):
                                    await key.send(json.dumps({"You": connected[websocket]["message"]}))
                except websockets.exceptions.ConnectionClosed as e:
                    print(e)
                    print(f"Connection with client closed")
                    connected[key]["close"] = True
                    print(key)
                    print(websocket)
                    await resend()
            if websocket in connected:
                if connected[websocket]["close"] == True:
                    await websocket.close()
                    connected.pop(websocket)
                    print("Clowed a websocket connection")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Excepton occured: {e}")
        connected.pop(websocket, None)
    except KeyboardInterrupt:
        for key in connected.copy():
            connected.pop(key)
        print("Program closed with Ctl + C")
    print(connected)
    
        
async def main_loop():
    
    #task = asyncio.create_task(send_msg())
    
    
    async with websockets.serve(echo, "localhost", PORT):
        print("Test print")
        asyncio.create_task(send_msg())
        await asyncio.Future()  
    
try:
    asyncio.create_task(main_loop())
except KeyboardInterrupt:
    print("Exited loop")

