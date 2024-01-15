# this project has been written  by ILTERAY for MEKAR company
__device_model__="MILKAR W"
__version__ = "2.1.2"
import time
import os
from time import sleep
from struct import unpack
import network
import machine
import json
import socket
import math
import gc
import BlynkLib
import wifimgr
from ssd1351 import Display, color565
from machine import Pin, SPI, ADC,SoftSPI
from xglcd_font import XglcdFont
from mfrc522 import MFRC522
from struct import unpack
from hx711_pio import HX711
from machine import Timer
machine.freq(250000000)
# hx711 pin definitions
pin_OUT = Pin(7, Pin.IN, pull=Pin.PULL_DOWN)
pin_SCK = Pin(6, Pin.OUT)
hx711 = HX711(pin_SCK, pin_OUT)
# ----------------#
gc.enable()
"""termistor pin tanimlama"""
thermistor = machine.ADC(26)
"""screen spi begin"""
spi = SPI(1, baudrate=48000000, sck=Pin(10), mosi=Pin(11))
display = Display(spi, dc=Pin(12), cs=Pin(13), rst=Pin(14))
"""card reader spi begin"""
reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)
""" Setup the Rotary Encoder"""
sw_pin = Pin(16, Pin.IN, Pin.PULL_UP)
clk_pin = Pin(17, Pin.IN, Pin.PULL_UP)
dt_pin = Pin(18, Pin.IN, Pin.PULL_UP)
previous_value = True
button_down = False
""""cooler & mixer pin definition"""
cooler_pin = Pin(20, Pin.OUT)
mixer_pin = Pin(21, Pin.OUT)
"""pressure pins"""
high_pressure=Pin(8, Pin.IN, Pin.PULL_UP)
low_pressure=Pin(9, Pin.IN, Pin.PULL_UP)
"""fonts prepairing"""
arcadepix = XglcdFont('fonts/ArcadePix9x11.c', 9, 11)
unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)
"""constants"""
width = 128
height = 128
line = 1
highlight = 1
shift = 0
list_length = 0
previous_C = 0
previous_gr = 0
previous_ml = 0
steinhart_y = 40
weight_y = steinhart_y + 24
liter_y = weight_y + 24
steinhart=0

mixer_state = False
temp_treshould_state = False
blynk_icon = False
last_toggle_time = time.ticks_ms()

access = False
def timer_callback(t):
    global access
    access = False
def clean_garbage(x):
    gc.collect()
timer = Timer(period=300000, mode=Timer.PERIODIC, callback=timer_callback)
# mem_clean = Timer(period=1000,mode=Timer.PERIODIC,callback=clean_garbage)

with open('config.json', 'r') as f:  # read the json file
    config = json.load(f)
display.contrast(config['brightness'])

def open_language_file(language,change=None):# read language packet
    global lang
    if change:
        del lang
    with open(f'languages/{language}.json', 'r') as l:
        lang = json.load(l)
    return lang

open_language_file(config["language"])# get language packet

def write_config(a=config):
    with open('config.json', 'w') as f:
        json.dump(config, f)

def center_text(y, text, font, color):
    global center, w
    w = font.measure_text(text)  # Measure length of text in pixels
    # Calculate position for centered text
    center = int(display.width / 2 - w / 2)
    display.draw_text(center, y, text, font, color)
    return center

def draw_image(image_path, x, y, width, height):
    display.draw_image(image_path, x, y, width, height)

def home():
    global text,blynk_icon
    display.clear()
    if network.WLAN(network.STA_IF).isconnected():
        draw_image('assets/4.raw', 102, 0, 24, 24)  # offline icon
    else:
        draw_image('assets/3.raw', 102, 0, 24, 24)  # online icon
    if cooler_pin.value() == 0:
        draw_image('assets/8.raw', 0, 0, 24, 24)  # cooler off icon
    elif cooler_pin.value() == 1:
        draw_image('assets/2.raw', 0, 0, 24, 24)  # cooler on icon
    if mixer_pin.value() == 0:
        draw_image('assets/10.raw', 25, 0, 24, 24)  # mixer off icon
    elif mixer_pin.value() == 1:
        draw_image('assets/6.raw', 25, 0, 24, 24)  # mixer on icon
    if blynk_icon is True:
        draw_image('assets/blynkicon.raw', 75, 0, 24, 24)  # blynk off icon
    elif blynk_icon is False:
        draw_image('assets/blynkiconno.raw', 75, 0, 24, 24)  # blynk on icon
    if config['alertcond'] == 1:
        draw_image('assets/alarm.raw', 0, 52, 24, 24)  # alert icon
"""RFID READER CODES"""
def read_uids():
    with open("card_lib.dat") as f:
        lines = f.readlines()
    uids = []
    for line in lines:
        uid = line.strip("\n").replace('[', '').replace(']', '').split(', ')
        uid = [int(x, 0) for x in uid]  # Hexadecimal olarak okuma
        uids.append(uid)
    return uids

def write_uids(uids):
    with open("card_lib.dat", "w") as f:
        for uid in uids:
            f.write("[%s]\n" % (', '.join(hex(x) for x in uid)))

def card_generator(cond):
    display.clear()
    center_text(0, lang["adding_card"], arcadepix, color565(0, 255, 0))
    center_text(50, lang["card"], arcadepix, color565(0, 255, 0))
    center_text(64, lang["scan"], arcadepix, color565(0, 255, 0))
    from mfrc522 import MFRC522
    import utime
    reader = MFRC522(spi_id=0, sck=2, miso=4, mosi=3, cs=1, rst=0)
    try:
        while True:
            reader.init()
            (stat, tag_type) = reader.request(reader.REQIDL)
            if stat == reader.OK:
                (stat, uid) = reader.SelectTagSN()
                if stat == reader.OK:
                    try:
                        uids = read_uids()
                    except Exception as e:
                        uids = []
                        print(e)
                    if cond == 'add':
                        print(uids)
                        if uid in uids:
                            center_text(50, lang["card"], arcadepix, color565(0, 255, 0))
                            center_text(64, lang["already_registered"], arcadepix, color565(180, 0, 0))
                            config['setup']=True
                            time.sleep_ms(1000)
                        else:
                            print("liste: ",uids,"okunan uid: ",uid)
                            uids.append(uid)
                            print("yeni liste: ",uids)
                            write_uids(uids)
                            center_text(50, lang["card"], arcadepix, color565(0, 255, 0))
                            center_text(64, lang["registered"], arcadepix, color565(0, 255, 0))
                            config['setup']=True
                            time.sleep_ms(1000)
                    elif cond == 'delete':
                        if uid in uids:
                            print("liste: ",uids,"okunan uid: ",uid)
                            uids.remove(uid)
                            print("yeni liste: ",uids)
                            write_uids(uids)
                            center_text(50, lang["card"], arcadepix, color565(0, 255, 0))
                            center_text(64, lang["deleted"], arcadepix, color565(0, 255, 0))
                            del uids
                            time.sleep_ms(1000)
                        elif uid not in uids:
                            center_text(50, lang["card"], arcadepix, color565(0, 255, 0))
                            center_text(64, lang["not_in_list"], arcadepix, color565(0, 0, 255))
                            time.sleep_ms(1000)
                    PreviousCard = uid
                    break
                else:
                    pass
            else:
                PreviousCard = [0]
            time.sleep_ms(50)

    except KeyboardInterrupt:
        pass
def rfidread():
    global access
    display.clear()
    center_text(0, lang["scan_card"], arcadepix, color565(0, 255, 0))  # call for center the text
    draw_image('assets/rfidread.raw', 14, 14, 100, 100)
    rfid_timout = 0
    while rfid_timout <= 20:
        reader.init()
        (stat, tag_type) = reader.request(reader.REQIDL)
        if stat == reader.OK:
            (stat, uid) = reader.SelectTagSN()
            if stat == reader.OK:
                PreviousCard = uid
                try:
                    uids = read_uids()
                except BaseException:
                    uids = []
                print(uid,type(uid))
                if uid == [211, 86, 206, 149] or uid in uids:
                    access = True
                    rfiddone()
                    sleep(1)
                    gc.collect()
                    mainmenu()
                    rfid_timout=19
                else:
                    rfidno()
                    break
            else:
                pass
        else:
            PreviousCard = [0]
        rfid_timout += 1
        sleep(0.5)
    home()

def rfiddone():
    display.clear()
    center_text(0, lang["card_read"], arcadepix, color565(72, 222, 105))  # call for center the text
    draw_image('assets/rfiddone.raw', 14, 20, 100, 100)

def rfidno():
    display.clear()
    center_text(0,lang["invalid_card"],arcadepix,color565(198,59,59))  # call for center the text
    draw_image('assets/rfidno.raw', 14, 20, 100, 100)
    sleep(2)
    home()

def draw_message(text):
    try:
        display.fill_rectangle(0, 115, 128, 13, color565(0, 0, 0))
        display.draw_text(0, 115, text, arcadepix, color565(255, 255, 255))
    except:
        pass

def set_time():  # get time function
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo("pool.ntp.org", 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    finally:
        s.close()
    val = unpack("!I", msg[40:44])[0]
    t = val - 2208978000  # gmt+3 saat dilimini ayarladik
    tm = time.gmtime(t)
    machine.RTC().datetime(
        (tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

def display_time():
    dcurrent_time = "{}.{}.{} {:02d}:{:02d}".format(
        machine.RTC().datetime()[2], machine.RTC().datetime()[1], machine.RTC().datetime()[0], int(
            machine.RTC().datetime()[4]), int(
            machine.RTC().datetime()[5]))
    center_text(30, dcurrent_time, arcadepix, color565(255, 255, 255))  # call for center the text

def temperature():
    global previous_C, steinhart, blynk
    temperature_reads = [thermistor.read_u16() for _ in range(5)]
    temperature_value = sum(temperature_reads) / len(temperature_reads)
    try:
        R = config['TH_RES'] / (65535 / temperature_value - 1)
        if config['termistor_type'] == 'ntc':
            steinhart = math.log(R / config['TH_RES']) / 3950.0
            steinhart += 1.0 / (25.0 + 273.15)
            steinhart = (1.0 / steinhart) - 273.15 + config['thermistor_offset']
        elif config['termistor_type'] == 'ptc':
            steinhart = -1 * (math.log(R / config['TH_RES']) * 3950.0)
            steinhart += 1.0 / (25.0 + 273.15)
            steinhart = (1.0 / steinhart) - 273.15 + config['thermistor_offset']
        if previous_C != unispace.measure_text(str(round(steinhart, 1))):
            center_text(steinhart_y, "       ", unispace, color565(0, 255, 0))
        center_text(steinhart_y, str(round(steinhart, 1)), unispace, color565(0, 255, 0))
        display.draw_text(center +unispace.measure_text(str(round(steinhart, 1))) +5, steinhart_y +10, "C", arcadepix, color565(255, 255, 255))
        previous_C = unispace.measure_text(str(round(steinhart, 1)))
        if network.WLAN(network.STA_IF).isconnected() and 'blynk_code.dat' in os.listdir():
            try:
                blynk.virtual_write(5, steinhart)
                if steinhart > config['cooler']['tempmax']:
                    blynk.log_event("high_temperature")
                elif steinhart < config['cooler']['tempmin']:
                    blynk.log_event("lower_temp")
            except Exception as e:
                print("temperature sync error:", e)
        del temperature_reads
        return steinhart
    except BaseException:
        draw_message(lang["error"]+" [T1]")

def weight():
    global previous_gr, previous_ml, blynk
    weights = []
    for i in range(5):
        weights.append(
            ((hx711.read() /
              config['weight']['scale_factor']) -
                config['weight']['self_weight']))
    # okunan raw values degerlerinin ortalamasi alinir
    weight = round((sum(weights) / len(weights)))
    if weight <= 1:
        weight = 0
    liter = round((weight / 1.033))

    if previous_gr != unispace.measure_text(str(weight)):
        center_text(weight_y,"              ",unispace,color565(0,0,255))  # call for center the text
    if previous_ml != unispace.measure_text(str(liter)):
        center_text(liter_y,"              ",unispace,color565(0,0,255))  # call for center the text
    center_text(weight_y,str(weight),unispace,color565(0,0,255))  # call for center the text
    display.draw_text(center +unispace.measure_text(str(weight)) +5,weight_y +10,"kg",arcadepix,color565(37,80,255))  # KG
    previous_gr = unispace.measure_text(str(weight))
    center_text(liter_y,str(liter),unispace,color565(255,80,37))  # call for center the text
    display.draw_text(center +unispace.measure_text(str(liter)) +5,liter_y +10,"L",arcadepix,color565(255,80,0))  # L
    previous_ml = unispace.measure_text(str(liter))
    if network.WLAN(network.STA_IF).isconnected() and 'blynk_code.dat' in os.listdir():
        try:
            blynk.virtual_write(10, weight)
        except Exception as e:
            print("Weight sync errror:", e)
            draw_message(lang["error"]+" [W]")
    del weights

def init_blynk():
    try:
        return BlynkLib.Blynk(wifimgr.read_blynk_auth(), insecure=True)
    except BaseException:
        return None

try:
    draw_message(lang["wifi_connecting"])
    wifimgr.get_connection('first_start')
except Exception as e:
    print("wifimgr hatsi: ", e)
    draw_message(lang["wifi_not_connected"])
try:
    blynk = init_blynk()
except:
    pass
try:
    @blynk.on("connected")
    def blynk_connected(ping):
        global blynk_icon
        blynk.virtual_write(9, config['thermistor_offset'])
        blynk.virtual_write(0, config['cooler']['tempset'])
        blynk.virtual_write(2, config['cooler']['tempmax'])
        blynk.virtual_write(3, config['cooler']['tempmin'])
        blynk.virtual_write(8, config['cooler']['temptolerance'])
        blynk.virtual_write(6, config['mixer']['mixerwork'])
        blynk.virtual_write(7, config['mixer']['mixerwait'])
        if config['cooler']['coolercond']=='AKTIF':
            blynk.virtual_write(1, 1)
        else:
            blynk.virtual_write(1, 0)
        if config['mixer']['mixercond']=='AKTIF':
            blynk.virtual_write(4, 1)
        else:
            blynk.virtual_write(4, 0)
        blynk_icon = True
        home()
        draw_message(lang["server_connected"])
        
    @blynk.on("disconnected")
    def blynk_disconnected():
        blynk_icon = False
        home()
        draw_message(lang["connection_interrupt"])

    @blynk.on("V*")
    def blynk_handle_vpins(pin, value):
        if pin == '0' and config['cooler']['tempset'] != round(float(value[0]), 1):
            config['cooler']['tempset'] = round(float(value[0]), 1)
            draw_message("tempset: {}".format(config['cooler']['tempset']))
        elif pin == '1':
            if value[0] == '1' and config['cooler']['coolercond'] == 'PASIF':
                config['cooler']['coolercond'] = 'AKTIF'
                cooler_pin.value(1)
                home()
                draw_message(lang["cooler"]+": {}".format(config['cooler']['coolercond']))
            elif value[0] == '0' and config['cooler']['coolercond'] == 'AKTIF':
                config['cooler']['coolercond'] = 'PASIF'
                cooler_pin.value(0)
                home()
                draw_message(lang["cooler"]+": {}".format(config['cooler']['coolercond']))
        elif pin == '2' and config['cooler']['tempmax'] != round(float(value[0]), 1):
            config['cooler']['tempmax'] = round(float(value[0]), 1)
            draw_message(lang["warning_max"]+": {}".format(config['cooler']['tempmax']))
        elif pin == '3' and config['cooler']['tempmin'] != round(float(value[0]), 1):
            config['cooler']['tempmin'] = round(float(value[0]), 1)
            draw_message(lang["warning_min"]+": {}".format(config['cooler']['tempmin']))
        elif pin == '4':
            if value[0] == '1' and config['mixer']['mixercond'] == 'PASIF':
                config['mixer']['mixercond'] = 'AKTIF'
                mixer_pin.value(1)
                home()
                draw_message(lang["mixer"]+": {}".format(config['mixer']['mixercond']))
            elif value[0] == '0' and config['mixer']['mixercond'] == 'AKTIF':
                config['mixer']['mixercond'] = 'PASIF'
                mixer_pin.value(0)
                home()
                draw_message(lang["mixer"]+": {}".format(config['mixer']['mixercond']))
        elif pin == '6' and config['mixer']['mixerwork'] != int(round(float(value[0]), 0)):
            config['mixer']['mixerwork'] = int(round(float(value[0]), 0))
            draw_message(lang["mixer_work"]+": {} "+lang["minute"]+"".format(config['mixer']['mixerwork']))
        elif pin == '7' and config['mixer']['mixerwait'] != int(round(float(value[0]), 0)):
            config['mixer']['mixerwait'] = int(round(float(value[0]), 0))
            draw_message(lang["mixer_wait"]+": {} "+lang["minute"]+"".format(config['mixer']['mixerwait']))
        elif pin == '8' and config['cooler']['temptolerance'] != round(float(value[0]), 1):
            config['cooler']['temptolerance'] = round(float(value[0]), 1)
            draw_message(lang["tolerance"]+": {}".format(config['cooler']['temptolerance']))
        elif pin == '9' and config['thermistor_offset'] != round(float(value[0]), 1):
            config['thermistor_offset'] = round(float(value[0]), 1)
            draw_message(lang["thermistor_offset"]+": {}".format(config['thermistor_offset']))
        elif pin == '11':
            value = value[0]
            parse_and_assign_config(config, value)
        write_config()
except Exception as e:
    print("blynk virtual sync", e)

def parse_and_assign_config(config, value):
    parts = value.split("=")
    if len(parts) == 2:
        var_name = parts[0].strip()
        var_value = parts[1].strip()
        # Gelen stringde config[] var mı diye kontrol etme
        if "config" in var_name and "[" in var_name and "]" in var_name:
            try:
                exec(var_name + " = " + var_value)
            except Exception as e:
                print("Error: {}".format(e))
        else:
            print("Invalid format: {}".format(value))
    else:
        print("Invalid format: {}".format(value))

def mixer_toogle(current_time):
    global mixer_state, temp_treshould_state, last_toggle_time
    try:
        cooler_pin.value(0)
        if mixer_state == False and (current_time -last_toggle_time) >= (config['mixer']['mixerwork'] *60000):  # 60000 olacak
            mixer_pin.value(0)
            mixer_state = True
            last_toggle_time = current_time
            home()
        if mixer_state and (current_time - last_toggle_time) >= (config['mixer']['mixerwait'] *60000):
            mixer_pin.value(1)
            mixer_state = False
            last_toggle_time = current_time
            home()
    except Exception as e:
        print("toggle error:", e)

def blynkrun():
    if network.WLAN(network.STA_IF).isconnected() and 'blynk_code.dat' in os.listdir():
        try:
            blynk.run()  # blynk cloud connection
        except Exception as e:
            print("blynk.run(): ", e)

def set_value(a, value, min_value=None, max_value=None):
        display.clear()
        global previous_value, button_down
        center_text(int((display.height - unispace.height - 2) / 2),
                    str(a), unispace, color565(0, 255, 0))
        while True:
            if previous_value != dt_pin.value():
                if dt_pin.value() == False:
                    if clk_pin.value() == False:
                        a -= value
                        a = round(a,-int(math.floor(math.log10(value))))
                        if min_value is not None and a <= min_value:
                            a = min_value
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),str(a), unispace, color565(0, 255, 0))
                        time.sleep_ms(3)
                    else:
                        a += value
                        a = round(a,-int(math.floor(math.log10(value))))
                        if max_value is not None and a >= max_value:
                            a = max_value
                        display.clear()
                        center_text(int((display.height - unispace.height - 2) / 2),str(a), unispace, color565(0, 255, 0))
                        time.sleep_ms(3)
                previous_value = dt_pin.value()
            time.sleep_ms(1)
            if sw_pin.value() == False and not button_down:
                button_down = True
                write_config()
                time.sleep_ms(1)
                break
            time.sleep_ms(1)
            if sw_pin.value() and button_down:
                button_down = False
            time.sleep_ms(1)
        return a

# def check_pressure():
#     if high_pressure.value()==0:
#         config['alertcond'] = 1
#         draw_message("yuksek basinc")
#     else:
#         config['alertcond'] = 0
#     if low_pressure.value()==0:
#         config['alertcond'] = 1
#         draw_message("dusuk basinc")
#     else:
#         config['alertcond'] = 0
#     write_config()
def show_menu(menu, box,total_lines):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, highlight, shift, list_length
        item = 1
        boxitem = 1
        line = 1
        line_height = 20
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        box_list_length = len(box)
        sort_box_list = box[shift:shift + total_lines]
        display.clear()
        for item, boxitem in zip(short_list, sort_box_list):
            if highlight == line:
                display.draw_text(0,(line - 1) * line_height + 5,'>',arcadepix,color565(255,255,255))  # menu item pointer
                if item == "AKTIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(0,255,0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,0,0))  # menu item text
                else:
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))  # menu item text
                display.draw_text(127-arcadepix.measure_text(str(boxitem)),(line - 1) * line_height + 5,str(boxitem),arcadepix,color565(255,255,255))  # menu item's values
            else:
                if item == "AKTIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(0,255,0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,0,0))  # menu item text
                else:
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))  # menu item text
                display.draw_text(127-arcadepix.measure_text(str(boxitem)),(line - 1) * line_height + 5,str(boxitem),arcadepix,color565(255,255,255))  # rest of menu items's values
            line += 1
"""--------------------------------------------------------------------------------"""
"""---------------------------------ABOUT------------------------------------------"""
"""--------------------------------------------------------------------------------"""
def about_page(cond):
    global button_down, previous_value

    def aboutpage():
        display.clear()
        if cond:
            center_text(0, lang["about"], arcadepix, color565(0, 255, 0))
        center_text(30, "MEKAR", unispace, color565(255, 0, 0))
        center_text(70,"mekarteknoloji.com",arcadepix,color565(255,255,255))
        center_text(100, __version__, arcadepix, color565(255, 255, 255))
    aboutpage()
    previous_time = time.ticks_ms()

    while cond:
        try:
            gc.collect()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                previous_time = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        break
                    # Turned Right
                    else:
                        break
                previous_value = dt_pin.value()
            time.sleep_ms(1)
            if sw_pin.value() == False and not button_down:
                previous_time = current_time
                button_down = True
                time.sleep_ms(3)
                break
            
            if sw_pin.value() and button_down:
                button_down = False
                time.sleep_ms(3)
            if elapsed_time >= 30000:  # 1 saniye geçti
                previous_time = current_time  # Geçen zamanı sıfırla
                break
        except Exception as e:
            print(e)
    if not cond:
        time.sleep_ms(3000)

"""--------------------------------------------------------------------------------"""
"""-------------------------------ABOUT END----------------------------------------"""
"""--------------------------------------------------------------------------------"""

"""--------------------------------------------------------------------------------"""
"""--------------------------------SETTINGS----------------------------------------"""
"""--------------------------------------------------------------------------------"""


def settings_menu():
    global button_down, blynk, previous_value, highlight, shift
    box = ['', config['thermistor_offset'],config['termistor_type'],
           config['brightness'], '', '', '',config["language"], '']
    file_list = [
        lang["back"],
        lang["thermistor_offset"],
        lang["termistor_type"],
        lang["brightness"],
        lang["wifi"],
        lang["adding_card"],
        lang["deleting_card"],
        lang["language"],
        lang["reset"]
        ]
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)

    def factory_settings():
        try:
            del config
            with open('config_backup.json', 'r') as f:  # read the json file
                config = json.load(f)
            os.remove('wifi.dat')
            os.remove('card_lib.dat')
            write_config()
            reset_settings=True
            time.sleep(1)
        except BaseException:
            display.clear()
            center_text(0, lang["reset_error"], arcadepix, color565(72, 222, 105))  # call for center the text
        if reset_settings:
            machine.reset()

    def wifi_client_setup():
        display.clear()
        center_text(60, lang["wifi_setup"], arcadepix, color565(0, 255, 0))
        time.sleep_ms(1000)
        display.clear()
        center_text(10, lang["wifi_name"]+":", arcadepix, color565(0, 255, 0))
        center_text(30, "MEKAR DEVICE", arcadepix, color565(255, 255, 255))
        center_text(50, lang["password"]+":", arcadepix, color565(0, 255, 0))
        center_text(70, "asdfghjk", arcadepix, color565(255, 255, 255))
        center_text(90, "IP:", arcadepix, color565(0, 255, 0))
        center_text(110, "192.168.4.1", arcadepix, color565(255, 255, 255))
        wlan = wifimgr.get_connection()
        if network.WLAN(network.STA_IF).isconnected():
            display.clear()
            center_text(60, lang["connected"], arcadepix, color565(0, 255, 0))
            time.sleep_ms(2000)
        if not network.WLAN(network.STA_IF).isconnected():
            display.clear()
            center_text(60, lang["error"], arcadepix, color565(255, 0, 0))
            time.sleep_ms(2000)

    def launch(filename):
        if filename == lang["thermistor_offset"]:
            config['thermistor_offset']=set_value(config['thermistor_offset'], 0.1)
            box[1]=config['thermistor_offset']
        elif filename == lang["brightness"]:
            config['brightness']=set_value(config['brightness'], 1,1,15)
            box[3]=config['brightness']
            display.contrast(config['brightness'])
        elif filename == lang["reset"]:
            factory_settings()
        elif filename == lang["wifi"]:
            wifi_client_setup()
        elif filename == lang["adding_card"]:
            card_generator('add')
        elif filename == lang["deleting_card"]:
            card_generator('delete')
        elif filename == lang["language"]:
            language_menu()
        elif filename==lang["termistor_type"]:
            if config['termistor_type']=='ntc':
                config['termistor_type']='ptc'
            elif config['termistor_type']=='ptc':
                config['termistor_type']='ntc'
            box[2]=config['termistor_type']
            write_config()
    show_menu(file_list, box,total_lines)
    previous_time = time.ticks_ms()
    msg_prev_time = time.ticks_ms()
    while True:
        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            msg_runout_time = current_time - msg_prev_time
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                previous_time = current_time
                if dt_pin.value() == False:
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list, box,total_lines)
                previous_value = dt_pin.value()
            time.sleep_ms(1)

            if sw_pin.value() == False and not button_down:
                button_down = True
                time.sleep_ms(3)
                if file_list[(highlight - 1) + shift]==lang["back"]:
                    break
                else:
                    launch(file_list[(highlight - 1) + shift])
                show_menu(file_list, box,total_lines)
                previous_time = current_time
            if sw_pin.value() and button_down:
                button_down = False
                time.sleep_ms(3)
            if elapsed_time >= 1000:  # 1 saniye geçti
                previous_time = current_time  # Geçen zamanı sıfırla
                if network.WLAN(network.STA_IF).isconnected():
                    try:
                        blynk.virtual_write(9, config['thermistor_offset'])
                    except Exception as e:
                        print(e)
            if msg_runout_time >= 30000:  # 1 saniye geçti
                msg_prev_time = current_time
                break
        except Exception as e:
            print(e)
"""--------------------------------------------------------------------------------"""
"""-------------------------------SETTINGS END-------------------------------------"""
"""--------------------------------------------------------------------------------"""

"""--------------------------------------------------------------------------------"""
"""----------------------------------WEIGHT----------------------------------------"""
"""--------------------------------------------------------------------------------"""


def weight_menu():
    global button_down, temp_treshould_state, blynk, previous_value, highlight, shift
    box = [
        '',
        '',
        '',
        '',
        config['weight']['scale_factor'],
        config['weight']['self_weight'],
        config['weight']['weight_1'],
        config['weight']['weight_2']]
    file_list = [
        lang["back"],
        config['weight']['weightcond'],
        lang["tare"],
        lang["calibration"],
        lang["scale_factor_set"],
        lang["tank_weight"],
        lang["weight1"],
        lang["weight2"]]
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)
    steinhart_y = 40
    weight_y = steinhart_y + 24
    liter_y = weight_y + 24

    def calibrate_weight_sensor():
        global button_down
        display.clear()
        center_text(55, f"{config['weight']['weight_1']}kg {lang['of_weight']}", arcadepix, color565(0, 255, 0))
        center_text(70, lang["put"], arcadepix, color565(0, 255, 0))
        measurement = False
        while measurement != True:
            if sw_pin.value() == False and not button_down:
                button_down = True
                raw_values1 = []
                for i in range(5):
                    raw_values1.append(hx711.read())
                raw_value1 = sum(raw_values1) / len(raw_values1)# okunan raw values degerlerinin ortalamasi alinir
                measurement = True
                sleep(1)
            if sw_pin.value() and button_down:
                button_down = False
        sleep(0.01)
        display.clear()
        center_text(55, f"{config['weight']['weight_1']}kg {lang['of_weight']}", arcadepix, color565(0, 255, 0))
        center_text(70, lang["take"], arcadepix, color565(0, 255, 0))
        sleep(2)
        display.clear()
        center_text(55, f"{config['weight']['weight_2']}kg {lang['of_weight']}", arcadepix, color565(0, 255, 0))
        center_text(70, lang["put"], arcadepix, color565(0, 255, 0))
        measurement = False
        while measurement != True:
            if sw_pin.value() == False and not button_down:
                button_down = True
                raw_values2 = []
                for i in range(5):
                    raw_values2.append(hx711.read())
                raw_value2 = sum(raw_values2) / len(raw_values2)# okunan raw values degerlerinin ortalamasi alinir
                measurement = True
                sleep(1)
            if sw_pin.value() and button_down:
                button_down = False
        sleep(0.01)
        try:
            # scale factor  ortalamasi alinir
            scale_factor = round((raw_value1 - raw_value2) / (float(config['weight']['weight_1']) - float(config['weight']['weight_2'])))
            config['weight']['scale_factor'] = scale_factor
            display.clear()
            write_config()
            center_text(55, lang["calibration"], arcadepix, color565(0, 255, 0))
            center_text(70, lang["ok"], arcadepix, color565(0, 255, 0))
            sleep(2)
        except BaseException:
            display.clear()
            center_text(55, lang["calibration"], arcadepix, color565(0, 255, 0))
            center_text(70, lang["error"], arcadepix, color565(0, 255, 0))
            sleep(2)

    def tare():
        display.clear()
        center_text(55, lang["tare_process"], arcadepix, color565(0, 255, 0))
        tares = []
        for i in range(5):
            tares.append(hx711.read())
        config['weight']['self_weight'] = round(((sum(tares) / len(tares)) / config['weight']['scale_factor']),1)  # okunan raw values degerlerinin ortalamasi alinir
        write_config()
        time.sleep_ms(1000)
        display.clear()
        center_text(55, lang["tare_ok"], arcadepix, color565(0, 255, 0))
        time.sleep_ms(1000)

    def launch(filename):
        if filename == file_list[1]:
            if config['weight']['weightcond'] == "AKTIF":
                config['weight']['weightcond'] = "PASIF"
            elif config['weight']['weightcond'] == "PASIF":
                config['weight']['weightcond'] = "AKTIF"
            write_config()
            file_list[1] = config['weight']['weightcond']
        elif filename == lang["scale_factor_set"]:
            config['weight']['scale_factor']=set_value(config['weight']['scale_factor'], 1)
            box[4]=config['weight']['scale_factor']
        elif filename == lang["calibration"]:
            calibrate_weight_sensor()
        elif filename == lang["tare"]:
            tare()
        elif filename == lang["tank_weight"]:
            config['weight']['self_weight']= set_value(config['weight']['self_weight'], 1)
            box[5]=config['weight']['self_weight']
        elif filename ==lang["weight1"]:
            config['weight']['weight_1']=set_value(config['weight']['weight_1'],1)
            box[6]=config['weight']['weight_1']
        elif filename ==lang["weight2"]:
            config['weight']['weight_2']=set_value(config['weight']['weight_2'],1)
            box[7]=config['weight']['weight_2']
    show_menu(file_list, box,total_lines)
    screen_timeout_in = time.ticks_ms()
    while True:
        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            screen_timeout = current_time - screen_timeout_in  # Geçen süreyi kontrol et
            if previous_value != dt_pin.value():
                screen_timeout_in = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list, box,total_lines)
                previous_value = dt_pin.value()
            time.sleep_ms(1)
            if sw_pin.value() == False and not button_down:
                screen_timeout_in = current_time
                button_down = True
                if file_list[(highlight - 1) + shift]==lang["back"]:
                    break
                else:
                    launch(file_list[(highlight - 1) + shift])
                show_menu(file_list, box,total_lines)
                
            if sw_pin.value() and button_down:
                button_down = False
                time.sleep_ms(3)
            if screen_timeout >= 30000:  # 1 saniye geçti
                screen_timeout_in = current_time  # Geçen zamanı sıfırla
                break
        except Exception as e:
            print("while(): ", e)
"""--------------------------------------------------------------------------------"""
"""--------------------------------WEIGHT END--------------------------------------"""
"""--------------------------------------------------------------------------------"""
"""--------------------------------------------------------------------------------"""
"""----------------------------------MIXER-----------------------------------------"""
"""--------------------------------------------------------------------------------"""
def mixer_menu():
    global button_down, temp_treshould_state, blynk, previous_value, highlight, shift
    box = ['', '', config['mixer']['mixerwork'], config['mixer']['mixerwait']]
    file_list = [
        lang["back"],
        config['mixer']['mixercond'],
        lang["work_time"],
        lang["wait_time"]]
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)

    def launch(filename):
        if filename == file_list[1]:
            if config['mixer']['mixercond'] == "AKTIF":
                config['mixer']['mixercond'] = "PASIF"
                mixer_pin.value(0)
            elif config['mixer']['mixercond'] == "PASIF":
                config['mixer']['mixercond'] = "AKTIF"
                mixer_pin.value(1)
            write_config()
            file_list[1] = config['mixer']['mixercond']
        elif filename == lang["work_time"]:
            config['mixer']['mixerwork']= set_value(config['mixer']['mixerwork'], 1)
            box[2]=config['mixer']['mixerwork']
        elif filename == lang["wait_time"]:
            config['mixer']['mixerwait']=set_value(config['mixer']['mixerwait'], 1)
            box[3]=config['mixer']['mixerwait']
    show_menu(file_list, box,total_lines)

    previous_time = time.ticks_ms()
    screen_timeout_in = time.ticks_ms()
    while True:
        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time  # Geçen süreyi kontrol et
            screen_timeout = current_time - screen_timeout_in  # Geçen süreyi kontrol et
            if elapsed_time >= 1000:  # 1 saniye geçti
                if network.WLAN(network.STA_IF).isconnected():
                    try:
                        blynk.virtual_write(4, config['mixer']['mixercond'])
                        blynk.virtual_write(6, config['mixer']['mixerwork'])
                        blynk.virtual_write(7, config['mixer']['mixerwait'])
                    except Exception as e:
                        print("blynk.wirtual_write(): ", e)
                previous_time = current_time  # Geçen zamanı sıfırla
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                screen_timeout_in = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list, box,total_lines)
                previous_value = dt_pin.value()
            time.sleep_ms(1)
            if sw_pin.value() == False and not button_down:
                screen_timeout_in = current_time
                button_down = True
                if file_list[(highlight - 1) + shift]==lang["back"]:
                    break
                else:
                    launch(file_list[(highlight - 1) + shift])
                show_menu(file_list, box,total_lines)
            if sw_pin.value() and button_down:
                button_down = False
                time.sleep_ms(1)
            if screen_timeout >= 30000:  # 1 saniye geçti
                screen_timeout_in = current_time  # Geçen zamanı sıfırla
                break
        except Exception as e:
            print("while(): ", e)

"""--------------------------------------------------------------------------------"""
"""---------------------------------MIXER END--------------------------------------"""
"""--------------------------------------------------------------------------------"""
"""--------------------------------------------------------------------------------"""
"""---------------------------------LANGUAGE---------------------------------------"""
"""--------------------------------------------------------------------------------"""

def language_menu():
    global button_down, previous_value, highlight, shift
    line = 1
    highlight = 1
    shift = 0
    file_list = [
        lang["back"],
        "TURKCE",
        "ENGLISH",
        ]
    if len(file_list) >= 6:
        total_lines = 6
    else:
        total_lines = len(file_list)

    def show_menu(menu):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, highlight, shift, list_length
        item = 1
        line = 1
        line_height = 20
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        display.clear()
        for item in short_list:
            if highlight == line:
                display.draw_text(0,(line - 1) * line_height + 5,'>',arcadepix,color565(255,255,255))  # menu item pointer
                display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))  # menu item text
            else:
                display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))  # menu item text
            line += 1

    def launch(filename):
        if filename=='TURKCE':
            config["language"]='tr'
        elif filename=='ENGLISH':
            config["language"]='en'
        write_config()
        try:
            open_language_file(config["language"],change=True)
        except Exception as s:
            print(s)
        
    show_menu(file_list)
    previous_time = time.ticks_ms()
    screen_timeout_in = time.ticks_ms()
    while True:
        try:
            gc.collect()
            current_time = time.ticks_ms()
            screen_timeout = current_time - screen_timeout_in  # Geçen süreyi kontrol et
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                screen_timeout_in = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(file_list)
                previous_value = dt_pin.value()
            time.sleep_ms(1)

            if sw_pin.value() == False and not button_down:
                button_down = True
                if file_list[(highlight - 1) + shift]==lang["back"]:
                    break
                else:
                    launch(file_list[(highlight - 1) + shift])
                display.clear()
                draw_message(lang["please_wait"])
                screen_timeout_in = current_time
                time.sleep_ms(3)

            if sw_pin.value() and button_down:
                button_down = False
                time.sleep_ms(3)
            if screen_timeout >= 30000:  # 1 saniye geçti
                screen_timeout_in = current_time  # Geçen zamanı sıfırla
                break
        except OSError:
            time.sleep_ms(1000)

"""--------------------------------------------------------------------------------"""
"""---------------------------------LANG END --------------------------------------"""
"""--------------------------------------------------------------------------------"""
"""--------------------------------------------------------------------------------"""
"""----------------------------------COOLER ---------------------------------------"""
"""--------------------------------------------------------------------------------"""

def cooler_menu():
    global button_down, temp_treshould_state, blynk, previous_value, highlight, shift
    box = [
        '',
        '',
        config['cooler']['tempset'],
        config['cooler']['tempmax'],
        config['cooler']['tempmin'],
        config['cooler']['temptolerance']]
    file_list = [
        lang["back"],
        config['cooler']['coolercond'],
        lang["constant_tem"],
        lang["warning_max"],
        lang["warning_min"],
        lang["tolerance"]]
    # İki listenin elemanlarını birleştirme
    combined_list = [box[i] + file_list[i] for i in range(min(len(box), len(file_list)))]

    # Oluşturulan birleştirilmiş listeyi yazdırma
    print(combined_list)
    menu = [
        (lang["back"], ''),
        (config['cooler']['coolercond'], ''),
        (lang["constant_tem"], config['cooler']['tempset']),
        (lang["warning_max"], config['cooler']['tempmax']),
        (lang["warning_min"], config['cooler']['tempmin']),
        (lang["tolerance"], config['cooler']['temptolerance'])]
    if len(menu) >= 6:
        total_lines = 6
    else:
        total_lines = len(menu)
    def show_menu(menu):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, list_length
        # menu variables
        item = 1
        line = 1
        line_height = 20
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        display.clear()
        for item, ifilename in short_list:
            if highlight == line:
                display.draw_text(0,(line - 1) * line_height + 5,'>',arcadepix,color565(255,255,255))
                display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))
                if item == "AKTIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(0,255,0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,0,0))  # menu item text
                else:
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))  # menu item text
                display.draw_text(127-arcadepix.measure_text(str(ifilename)),(line - 1) * line_height + 5,str(ifilename),arcadepix,color565(255,255,255))  # menu item's values
            else:
                if item == "AKTIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(0,255,0))  # menu item text
                elif item == "PASIF":
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,0,0))  # menu item text
                else:
                    display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))  # menu item text
                display.draw_text(127-arcadepix.measure_text(str(ifilename)),(line - 1) * line_height + 5,str(ifilename),arcadepix,color565(255,255,255))  # rest of menu items's values
            line += 1
        return ifilename
    def launch(filename):
        print(type(filename[1]))
        if filename[0] == "AKTIF":
            filename[0] = 'PASIF'
        elif filename[0] == "PASIF":
            filename[0] = 'AKTIF'
#         elif filename == lang["constant_tem"]:
#             config['cooler']['tempset']=set_value(config['cooler']['tempset'], 0.1)
#             filename[2]=config['cooler']['tempset']
#         elif filename == lang["warning_max"]:
#             config['cooler']['tempmax']=set_value(config['cooler']['tempmax'], 0.1)
#             box[3]=config['cooler']['tempmax']
#         elif filename == lang["warning_min"]:
#             config['cooler']['tempmin']= set_value(config['cooler']['tempmin'], 0.1)
#             box[4]=config['cooler']['tempmin']
#         elif filename == lang["tolerance"]:
#             config['cooler']['temptolerance']= set_value(config['cooler']['temptolerance'], 0.1)
#             box[5]=config['cooler']['temptolerance']
        else:
            filename[1]=set_value(filename[1], 0.1)
        print(config['cooler']['coolercond'])
        write_config()
    show_menu(menu)
    previous_time = time.ticks_ms()
    screen_timeout_in = time.ticks_ms()
    

    while True:
        try:
            gc.collect()
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time  # Geçen süreyi kontrol et
            screen_timeout = current_time - screen_timeout_in  # Geçen süreyi kontrol et
            if elapsed_time >= 1000:  # 1 saniye geçti
                try:
                    blynk.virtual_write(0, config['cooler']['tempset'])
                    blynk.virtual_write(2, config['cooler']['tempmax'])
                    blynk.virtual_write(3, config['cooler']['tempmin'])
                    blynk.virtual_write(8, config['cooler']['temptolerance'])
                except BaseException:
                    pass
                previous_time = current_time  # Geçen zamanı sıfırla
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                screen_timeout_in = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(menu)
                previous_value = dt_pin.value()
            time.sleep_ms(1)

            if sw_pin.value() == False and not button_down:
                button_down = True
                if menu[(highlight - 1) + shift][0]==lang["back"]:
                    break
                print(menu[(highlight - 1) + shift])
                launch(menu[(highlight - 1) + shift])
                show_menu(menu)
                screen_timeout_in = current_time
                time.sleep_ms(3)

            if sw_pin.value() and button_down:
                button_down = False
                time.sleep_ms(3)
            if screen_timeout >= 30000:  # 1 saniye geçti
                screen_timeout_in = current_time  # Geçen zamanı sıfırla
                break
        except OSError:
            time.sleep_ms(1000)

"""--------------------------------------------------------------------------------"""
"""--------------------------------COOLER END--------------------------------------"""
"""--------------------------------------------------------------------------------"""

"""--------------------------------------------------------------------------------"""
"""---------------------------------MAIN MENU -------------------------------------"""
"""--------------------------------------------------------------------------------"""

def mainmenu():
    menu = [
        (lang["back"], ''),
        (lang["cooler"], 'cooler_menu()'),
        (lang["mixer"], 'mixer_menu()'),
        (lang["weight"], 'weight_menu()'),
        (lang["settings"], 'settings_menu()'),
        (lang["about"], 'about_page(True)')
    ]

    width = 128
    line = 1
    highlight = 1
    shift = 0
    list_length = 0
    if len(menu) >= 6:
        total_lines = 6
    else:
        total_lines = len(menu)

    previous_value = True
    button_down = False

    def show_menu(menu):
        """ Shows the menu on the screen"""
        # bring in the global variables
        global line, list_length
        # menu variables
        item = 1
        line = 1
        line_height = 20
        list_length = len(menu)
        short_list = menu[shift:shift + total_lines]
        display.clear()
        for item, ifilename in short_list:
            if highlight == line:
                display.draw_text(0,(line - 1) * line_height + 5,'>',arcadepix,color565(255,255,255))
                display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))
            else:
                display.draw_text(10,(line - 1) * line_height + 5,item,arcadepix,color565(255,255,255))
            line += 1
        return ifilename

    def launch(filename):
        eval(filename[1])
    show_menu(menu)
    previous_time = time.ticks_ms()
    while True:
        try:
            gc.collect()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            # Check for encoder rotated
            if previous_value != dt_pin.value():
                previous_time = current_time
                if dt_pin.value() == False:
                    # Turned Left
                    if clk_pin.value() == False:
                        if highlight > 1:
                            highlight -= 1
                        else:
                            if shift > 0:
                                shift -= 1
                    # Turned Right
                    else:
                        if highlight < total_lines:
                            highlight += 1
                        else:
                            if shift + total_lines < list_length:
                                shift += 1
                    show_menu(menu)
                previous_value = dt_pin.value()
            if sw_pin.value() == False and not button_down:
                button_down = True
                if menu[(highlight - 1) + shift][0]==lang["back"]:
                    break
                launch(menu[(highlight - 1) + shift])
                show_menu(menu)
                time.sleep_ms(3)
            if sw_pin.value() and button_down:
                button_down = False
                time.sleep_ms(3)
            if elapsed_time >= 30000:  # 1 saniye geçti
                previous_time = current_time  # Geçen zamanı sıfırla
                home()
                break
        except Exception as e:
            print(e)


"""--------------------------------------------------------------------------------"""
"""------------------------------MAIN MENU END-------------------------------------"""
"""--------------------------------------------------------------------------------"""


def main():
    home()
    global button_down, steinhart, temp_treshould_state, blynk,access
    previous_time = time.ticks_ms()
    msg_prev_time = time.ticks_ms()

    while True:
        try:
            blynkrun()
            current_time = time.ticks_ms()
            elapsed_time = current_time - previous_time
            msg_runout_time = current_time - msg_prev_time
            # Geçen süreyi kontrol et
            if elapsed_time >= 1000:  # 1 saniye geçti
                gc.collect()
                if network.WLAN(network.STA_IF).isconnected():
                    if 'blynk_code.dat' in os.listdir():
                        try:
                            blynk.sync_virtual(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
                        except Exception as e:
                            print("blynk sync wirtual: ", e)
                            draw_message(lang["sync_error"])
                    display_time()
                temperature()
                weight()
                previous_time = current_time  # Geçen zamanı sıfırla
            if msg_runout_time >= 30000:
                display.fill_rectangle(0, 115, 128, 13, color565(0, 0, 0))
                text = " "
                msg_prev_time = current_time
                if machine.RTC().datetime()[0] < 2023 and network.WLAN(
                        network.STA_IF).isconnected():
                    set_time()
#                 check_pressure()
            if sw_pin.value() == False and not button_down:
                button_down = True
                if access:
                    mainmenu()
                else:
                    rfidread()
                home()
            if sw_pin.value() and button_down:
                button_down = False

            if steinhart >= config['cooler']['tempset'] + \
                    config['cooler']['temptolerance'] and config['cooler']['coolercond'] == 'AKTIF' and config['mixer']['mixercond'] == 'AKTIF':
                cooler_pin.value(1)
                mixer_pin.value(1)
                if not temp_treshould_state:
                    home()
                temp_treshould_state = True
            if steinhart < config['cooler']['tempset'] and config['mixer']['mixercond'] == 'AKTIF':
                temp_treshould_state == False
                mixer_toogle(current_time)
            if steinhart >= config['cooler']['tempset'] and temp_treshould_state == False and config['mixer']['mixercond'] == 'AKTIF':
                mixer_toogle(current_time)
            sleep(0.01)
        except Exception as e:
            print("main loop error: ", e)
            draw_message(lang["error"]+" [M]")

if __name__ == "__main__":
    about_page(False)
    if config['setup']!=True or not 'card_lib.dat' in os.listdir():
        display.clear()
        center_text(50, lang["first"], arcadepix, color565(0, 255, 0))
        center_text(64, lang["setup"], arcadepix, color565(0, 255, 0))
        time.sleep(2)
        center_text(50, lang["card"], arcadepix, color565(0, 255, 0))
        center_text(64, lang["identify"], arcadepix, color565(0, 255, 0))
        time.sleep(2)
        card_generator('add')
    main()

