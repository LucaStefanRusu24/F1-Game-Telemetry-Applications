import socket 
import struct

#UDP connection setup

UDP_IP = "0.0.0.0"
UDP_PORT = 20777

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

def receive_telemetry():
    data = sock.recvfrom(2048)
    return data

def parse_telemetry_packet(data):
    #Extract telemetry data
    speed = struct.unpack_from("<H", data, 7)[0] # speed at position 7
    throttle = struct.unpack_from("<f", data, 9)[0] # throttle at position 9
    brake = struct.unpack_from("<f", data, 13)[0] # brake at position 13
    gear = struct.unpack_from("b", data, 21)[0] # gear at position 21
    lap_time = struct.unpack_from("<f", data, 30)[0] # lap time position 30

    return {
        "speed": speed,
        "throttle": throttle,
        "brake": brake,
        "gear": gear,
        "lap_time": lap_time
    }

