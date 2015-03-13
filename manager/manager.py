import bluetooth as bt
from light import Light
from comet import Comet
import colorsys
from time import sleep
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import json

# Stores each light
lights = {}

# Stores each comet
comets = []

def find_lights():
    """ Finds nearby lights and adds them to the dictionary """
    print("Discovering devices...")
    nearby_devices = bt.discover_devices()

    for address in nearby_devices:
        name = bt.lookup_name(address)
        # Ignore non-lights
        if name.startswith("Light"):
            # Get the light number from the name
            num = int(name[-2:])
            # Check to see if we already found the light
            if not num in lights:
                # Create a light object
                print("Found light", num)
                lights[num] = Light(address, num)
            elif not lights[num].is_connected:
                # We found the light, but it wasn't able to connect. Try again
                print("Attempting to reconnect light", num)
                lights[num].connect_light()

    # Figure out how many lights are connected
    count = 0
    for light in lights:
        if lights[light].is_connected:
            count += 1
    
    if count == 0:
        print("No lights are connected!")
    return count

def cycle_hue():
    """Cycles the hue of each light"""
    while True:
        count = 0
        for light in lights:
            if lights[light].is_connected:
                count += 1
                # Test all lights by cycling the hue
                for hue in [x/256 for x in range(0, 255)]:
                    rgb = colorsys.hsv_to_rgb(hue, 1, 1)
                    lights[light].send_rgb(int(255*rgb[0]), int(255*rgb[1]), int(255*rgb[2]))
        if count == 0:
            print("No connected lights. Quitting.")
            quit()

def test_rgb():
    """ Tests each channel of each light sequentially """
    while True:
        for light in lights:
            if lights[light].is_connected:
                print("Testing light", light)
                print("Red")
                lights[light].send_rgb(255, 0, 0)
                sleep(1)
                print("Green")
                lights[light].send_rgb(0, 255, 0)
                sleep(1)
                print("Blue")
                lights[light].send_rgb(0, 0, 255)
                sleep(1)
                lights[light].send_rgb(0, 0, 0)



class WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        print("Websocket connection opened")

    def on_message(self, message):
        print("Websocket message received:", message)

        json_dict = json.loads(message)
        rgb = json_dict["color"]
        hsl = json_dict["colorHSL"]
        pos = json_dict["position"]
        lifespan = json_dict["lifespan"]

        print("RGB:", (rgb["r"], rgb["g"], rgb["b"]))
        print("HSL:", (hsl["h"], hsl["s"], hsl["l"]))
        print("Position:", (pos["x"], pos["y"], pos["z"]))
        print("Lifespan:", lifespan)

        comet = Comet(pos, hsl, lifespan)
        comets.append(comet)

    def on_close(self):
        print("Websocket connection closed")

application = tornado.web.Application([
    (r'/', WSHandler),
])

def frame_update():
    # Update the lights based on each comet
    colors = []
    if len(comets) == 0:
        # Nothing to update
        return

    # Get the colors from each comet
    for comet in comets:
        if comet.get_age() < comet.lifespan:
            colors.append(comet.get_colors(lights))
        else:
            print("Comet too old:", comet)
            comets.remove(comet)

    # print(colors)
    # sleep(1)
    # Get the average of the hues
    mixed_colors = {}
    for light in lights:
        rgb = {}
        rgb["r"] = max(sum(colors[:][light]["r"]), 255)
        rgb["g"] = max(sum(colors[:][light]["g"]), 255)
        rgb["b"] = max(sum(colors[:][light]["b"]), 255)

        mixed_colors[light] = rgb


# Wait until at least one light has been discovered
while not find_lights():
    pass

# test_rgb()
# cycle_hue()

print("Starting websocket IO loop")
application.listen(7445)
timer = tornado.ioloop.PeriodicCallback(frame_update, 5)
timer.start()
tornado.ioloop.IOLoop.instance().start()
