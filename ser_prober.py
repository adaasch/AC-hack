import serial

ser = serial.Serial('/dev/ttyUSB0', 9600, parity=serial.PARITY_EVEN)

last_msg = [0]
req = b"\xBB\x00\x01\x04\x02\x01\x00\xBD"

def rep_diff(buf):
    for i, v in enumerate(last_msg[:-1]):
        if v != buf[i]:
            print("{}: {}->{}".format(i,v.hex(),buf[i].hex()),end='\t')
    print()


def parse_msg(buf: bytes):
    global last_msg
    if buf[:4] == [b'\xbb', b'\x01', b'\x00', b'\x04']:
    #if buf[:4] == [b'\xbb', b'\x00', b'\x01', b'\x03']:
        rep_diff(buf)
        last_msg = buf
        ser.write(req)


ser.write(req)
buf = []
idx = -1
try:
    while True:
        idx += 1
        x = ser.read(1)  # read one byte
        if x[0] == 0xbb and idx == 0:
            print()
            #parse_msg(buf)
            buf = []
        if idx == 4:
            len = int(x[0])
        buf.append(x)
        print(x.hex(), end=' ', flush=True)
        if idx + 5 == len:
            parse_msg(buf)
            idx = -1

except KeyboardInterrupt:
    pass

# write a string
ser.close()  # close port
