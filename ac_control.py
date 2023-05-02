#!/usr/bin/python3
import paho.mqtt.client as mqtt
import json
from proto import parse_packet, init_set_cmd, set, make_packet

MQTTHOST = "192.168.0.1"

last_cmd = None


def to_intlist(hex_list):
    return [
        int(hex_list[i:i + 2], 16) for i in range(len(hex_list)) if i % 2 == 0
    ]


def to_hexlist(int_list):
    hex_list = ""
    for i in int_list:
        hex_list += "{:02X}".format(i)
    return hex_list


def setup_mqtt(rc):

    def result_fn(_a, _b, msg):
        print(msg.payload.decode("utf-8"))
        jsn = json.loads(msg.payload.decode("utf-8"))
        if "SerialReceived" not in jsn:
            return
        state = jsn["SerialReceived"]
        state_int = [
            int(state[i:i + 2], 16) for i in range(len(state)) if i % 2 == 0
        ]
        try:
            resp = parse_packet(state_int)['Packet']
        except Exception as e:
            print(e)
            return
        if "Get" in resp:
            state_jsn =  resp["Get"]
        elif "Set" in resp:
            state_jsn =  resp["Set"]
        else:
            return
        print(state_jsn)
        client.publish("ac_control/state", json.dumps(state_jsn))
        

    client.message_callback_add("tele/AC/RESULT", result_fn)
    client.subscribe("tele/AC/RESULT")

    def set_fn(_a, _b, msg):
        global last_cmd
        if last_cmd == None:
            last_cmd = init_set_cmd()
        args = msg.payload.decode("utf-8").strip().split(' ', 1)
        set(last_cmd, args[0], args[1])
        pkt = to_hexlist(make_packet(last_cmd))
        client.publish("cmnd/AC/SerialSend5",pkt)

    client.message_callback_add("ac_control/set", set_fn)
    client.subscribe("ac_control/set")

    def get_fn(_a, _b, msg):
        pkt = to_hexlist(make_packet([4,2,1,0]))
        client.publish("cmnd/AC/SerialSend5",pkt)

    client.message_callback_add("ac_control/get", get_fn)
    client.subscribe("ac_control/get")

    def custom_fn(_a, _b, msg):
        pl = msg.payload.decode("utf-8")
        if len(pl)%2 != 0: # todo check hex
            return
        pkt = to_hexlist(make_packet(to_intlist(pl)))
        client.publish("cmnd/AC/SerialSend5",pkt)

    client.message_callback_add("ac_control/custom", custom_fn)
    client.subscribe("ac_control/custom")


if __name__ == "__main__":

    client = mqtt.Client()
    client.on_connect = lambda client, userdata, flags, rc: setup_mqtt(rc)
    client.connect(MQTTHOST, 1883, 60)

    client.loop_forever()