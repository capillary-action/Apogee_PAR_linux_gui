from tkinter import *
from typing import List
from serial import Serial
from time import sleep
import struct
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

GET_VOLT = b'\x55!'
READ_CALIBRATION = b'\x83!'
SET_CALIBRATION = b'\x84%s%s!'
READ_SERIAL_NUM = b'\x87!'
GET_LOGGING_COUNT = b'\xf3!'
GET_LOGGED_ENTRY = b'\xf2%s!'
ERASE_LOGGED_DATA = b'\xf4!'

class Quantum:
    def __init__(self, port='/dev/ttyACM0'):
        self.quantum = None
        self.offset = 0.0
        self.multiplier = 0.0
        self.port = port
        self.connect_to_device()

    def connect_to_device(self):
        self.quantum = Serial(self.port, 115200, timeout=0.5)
        try:
            self.quantum.write(READ_CALIBRATION)
            multiplier = self.quantum.read(5)[1:]
            offset = self.quantum.read(4)
            self.multiplier = struct.unpack('<f', multiplier)[0]
            self.offset = struct.unpack('<f', offset)[0]
        except (IOError, struct.error) as e:
            print(e)
            self.quantum = None

    def read_from_device(self, command):
        if self.quantum is None:
            self.connect_to_device()
            if self.quantum is None:
                raise IOError("Device not found")
        self.quantum.write(command)
        return self.quantum.read(5)[1:]

    def get_micromoles(self):
        voltage = self.read_voltage()
        if voltage == 9999:
            raise ValueError("Invalid voltage reading")
        micromoles = (voltage - self.offset) * self.multiplier * 1000
        if micromoles < 0:
            micromoles = 0
        return micromoles

    def read_voltage(self):
        response_list = []
        number_to_average = 5
        number_of_seconds = 1.0
        for i in range(number_to_average):
            try:
                response = self.read_from_device(GET_VOLT)
            except (IOError, ValueError) as e:
                print(e)
                return 9999
            if not response:
                continue
            voltage = struct.unpack('<f', response)[0]
            response_list.append(voltage)
            sleep(number_of_seconds/number_to_average)

        if not response_list:
            raise ValueError("No voltage reading received")
        return sum(response_list)/len(response_list)

class QuantumGUI:
    def __init__(self):
        self.quantum = Quantum()
        self.root = Tk()
        self.root.title("Quantum PAR Sensor")
        self.fig, self.ax = plt.subplots()
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.plot_canvas.get_tk_widget().pack()
        self.xdata = []
        self.ydata = []
        self.line, = self.ax.plot(self.xdata, self.ydata)

    def update_plot(self):
        par_value = self.quantum.get_micromoles()
        self.xdata.append(len(self.xdata) + 1)
        self.ydata.append(par_value)
        self.line.set_data(self.xdata, self.ydata)
        self.ax.relim()
        self.ax.autoscale_view()
        self.plot_canvas.draw()
        self.plot_canvas.flush_events()

    def run(self):
        while True:
            try:
                self.update_plot()
            except KeyboardInterrupt:
                break
        self.root.destroy()


if __name__ == '__main__':
    gui = QuantumGUI()
    gui.run()
