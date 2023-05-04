def crc8(bytes):
    crc = 0
    for b in bytes:
        crc ^= b
        for i in range(8):
            if ((crc & 0x80) != 0):
                crc = ((crc << 1) ^ 1) & 0xff
            else:
                crc <<= 1
    return crc


def to_bool(v):
    if isinstance(v, str):
        return v.lower() in ("yes", "true", "t", "1")
    else:
        return bool(v)


def check_sum(buf, idx):
    sum = buf[idx]
    buf[idx] = 0
    chk = crc8(buf)
    return {"CheckSum": (sum == chk, hex(chk))}


def get_flag(byte, flags: dict):
    res = []
    for k, v in flags.items():
        if k & byte == k:
            res.append(v)
    return res


def parse_nibble(byte, mask, desc: dict):
    for k, v in desc.items():
        if byte & mask == k:
            return v


PRETTY = {
    "cool": "Cooling",
    "vent": "Ventilation",
    "dehum": "dehum",
    "heat": "Heating",
    "auto": "Auto",
    "normal": "Normal",
    "health": "Health",
    "turbo": "Turbo",
    "low noise": "Low Noise",
    "cmd": "Command",
    "len": "Length",
    "pwr": "Power",
    "eco": "Eco",
    "disp": "Display",
    "buzz": "Buzzer",
    "mode": "Mode",
    "state": "State",
    "temp": "Set Temperature °C",
    "fan": "Fan Speed",
    "Vanes": "vanes"
}

AC_MODE = {
    0x01: "cool",
    0x02: "fan",
    0x03: "dehum",
    0x04: "heat",
    0x05: "auto"
}

AC_STATE = {
    0x10: "On",
    0x20: "0x20?",
    0x40: "Eco",
    0x80: "Turbo",
}

FAN_SPEED = {
    0x80: "auto",
    0x90: "1",  # low noise (1001)
    0xc0: "2",  # (1100)
    0xa0: "3",  #(1010)
    0xd0: "4",  #(1101)
    0xb0: "5"  #turbo (1011)
}

COMMAND = {
    0x03: ("Command Set", {}),
    0x04: ("Command Get", {}),
}

VANE_MODE = {0x20: "horizontal move", 0x40: "vertical move"}

AC_RESP = {
    4: lambda buf, idx: {
        "state": get_flag(buf[idx], AC_STATE),
        "mode": parse_nibble(buf[idx], 0x0f, AC_MODE),
        "pwr": 0x10 & buf[idx] == 0x10,
        "eco": 0x40 & buf[idx] == 0x40,
        "turbo": 0x80 & buf[idx] == 0x80,
    },
    5: lambda buf, idx: {
        "temp": (buf[idx] & 0xf) + 16 + int(buf[idx + 1] & 0x2 == 0x2) * .5,
        "fan": parse_nibble(buf[idx], 0xf0, FAN_SPEED)
    },
    6: lambda buf, idx: {
        "vanes": get_flag(buf[idx], VANE_MODE)
    }
}

RESPONSE = {
    0x03: ("Set", AC_RESP),
    0x04: ("Get", AC_RESP),
}

PROTOCOL = {
    0xbb: ("Packet", {
        -1:
        check_sum,
        0:
        lambda buf, idx: {
            "Preamble": buf[idx] == 0xbb
        },
        1:
        lambda buf, idx: {
            "RX": bool(buf[idx])
        },
        2:
        lambda buf, idx: {
            "TX": bool(buf[idx])
        },
        4:
        lambda buf, idx: {
            "Length": (buf[idx], buf[idx] == len(buf) - 6)
        },
        3:
        lambda buf, idx: parse_packet(buf[idx:-1], COMMAND
                                      if bool(buf[2]) else RESPONSE),
    })
}


def set_flag(flags: dict):
    res = 0
    for k, v in flags.items():
        if k & byte == k:
            res.append(v)
    return res


SET_CMD_INITIAL_BITS = [
    0x00, 0x00, 0x00, 0x00, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x80
]

SET_FLAGS = {
    "eco": 0x80,
    "disp": 0x40,
    "buzz": 0x20,
}

SET_AC_MODE = {
    "heat": 0x01,
    "dehum": 0x02,
    "cool": 0x03,
    "vent": 0x07,
    "auto": 0x08
}

SET_AC_STATE = {
    "normal": 0x00,
    "health": 0x10,
    "turbo": 0x40,
    "low noise": 0x80
}

SET_FAN_SPEED = {"auto": 0x00, 1: 0x02, 2: 0x06, 3: 0x03, 4: 0x07, 5: 0x05}

SET_COMMAND = {
    "cmd":
    lambda: [(0, 0xff, 0x03)],
    "len":
    lambda: [(1, 0xff, 29)],
    #"flags": lambda arg = ["disp", "buzz"]: [(4, v,  v) for k, v in SET_FLAGS.items() if k in arg],
    "pwr":
    lambda arg=True: [(4, 0x0f, 0x04 if to_bool(arg) else 0x00)],
    "eco":
    lambda arg=True: [(4, 0x80, 0x80 if to_bool(arg) else 0x00)],
    "disp":
    lambda arg=True: [(4, 0x40, 0x40 if to_bool(arg) else 0x00)],
    "buzz":
    lambda arg=True: [(4, 0x20, 0x20 if to_bool(arg) else 0x00)],
    "mode":
    lambda arg="heat": [(5, 0x0f, SET_AC_MODE[arg])],
    "state":
    lambda arg="normal": [(5, 0xf0, SET_AC_STATE[arg])],
    "temp":
    lambda arg=16.0: [(6, 0x0f, max(min(0xf + 16 - int(float(arg)), 0xf), 0x0)
                       ), (8, 0x02, 0x00 if float(arg) % 1 < .5 else 0x02)],
    "fan":
    lambda arg="auto": [(7, 0x07, SET_FAN_SPEED[arg])],
}


def parse_packet(buf, desc=PROTOCOL):
    prot = desc[buf[0]]
    res = {}
    for k, v in prot[1].items():
        #print(v(buf, idx + k))
        res.update(v(buf, k))
    return {prot[0]: res}


def make_packet(payload):
    buf = [0] * (len(payload) + 4)
    buf[0] = 0xbb
    buf[2] = 1
    buf[3:-1] = payload
    buf[4] = len(payload) - 2
    buf[-1] = crc8(buf)
    return buf


def init_set_cmd():
    buf = [0] * (len(SET_CMD_INITIAL_BITS) + 2)
    buf[2:] = SET_CMD_INITIAL_BITS
    for val in SET_COMMAND.values():
        for res in val():
            buf[res[0]] = buf[res[0]] & ~res[1] | res[2]
    return buf


def set(buf, field, val):
    for res in SET_COMMAND[field](val):
        buf[res[0]] = buf[res[0]] & ~res[1] | res[2]