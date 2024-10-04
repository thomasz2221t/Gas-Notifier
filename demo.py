# -*- coding:utf-8 -*-
from gpiozero import MCP3008, PWMLED, Buzzer,Button
from email.mime.text import MIMEText
from time import sleep
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.core import lib

from luma.oled.device import sh1106
import RPi.GPIO as GPIO
import smtplib
import os
import time
import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Load default font.
font = ImageFont.load_default()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = 128
height = 64
image = Image.new('1', (width, height))

# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

serial = spi(device=0, port=1, bus_speed_hz = 8000000, transfer_size = 4096, gpio_DC = 24, gpio_RST = 25)

device = sh1106(serial, rotate=2) #sh1106

#0 - numer kanalu konwertera MCP3008
czujnik_gazu = MCP3008(0)
mostek_rezystancyjny_konwertera = MCP3008(7)
brzeczyk = Buzzer(14)
prog_alarmu = 0.09
email_wyslany = False
poczekanie_z_mailem = 0
status_przycisku = 0

#tworzenie obiektow diody RGB
led_red = PWMLED(2)
led_green = PWMLED(3)
led_blue = PWMLED(4)

#obiekt dla przycisku
#przycisk = Button(13)
GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def wyslij_email():
    global email_wyslany
    if(email_wyslany == False):
        #dane mail
        adres_email_nadawcy = 'tomek.cichon18@gmail.com'
        haslo_email_nadawcy = 'katowice2'
        adres_email_odbiorcy = 'tomekcichon@onet.pl'
        #wysylanie wiadomosci
        wartosc_przeliczona = int(czujnik_gazu.value*20000) #wprowadzenie poprawki 
        tresc = 'Uwaga! Wysokie stezenie gazu lub czadu w pomieszczeniu. Zmierzone stezenie substancji w powietrzu wynosi: '+ str(wartosc_przeliczona) + ' ppm.'
        msg = MIMEText(tresc)
        
        #ustawienie nadawcy i odbiorcy
        msg['From'] = adres_email_nadawcy
        msg['To'] = adres_email_odbiorcy
        
        #ustawienie tematu wiadomosci
        msg['Subject'] = 'POWIADOMIENIE Z POWIADAMIACZA PRECIWDYMNEGO I PRZECIWGAZOWEGO'
        
        #polaczenie z serwerem i wyslanie wiadomosci
        server = smtplib.SMTP('smtp.gmail.com', 587)
        
        server.starttls()
        server.login(adres_email_nadawcy, haslo_email_nadawcy)
        server.sendmail(adres_email_nadawcy, adres_email_odbiorcy, msg.as_string())
        server.quit()
        email_wyslany = True
        print('Email wyslany')


def przycisk_Wcisniety(channel):
    global status_przycisku
    czas_startu = time.time()
    
    while GPIO.input(channel) == 0: #czekamy dopoki wejscie nie wroci do stanu wysokiego
        pass
    
    czas_wcisniety = time.time() - czas_startu
    
    if .1 <= czas_wcisniety < 3: #uruchomienie sprawdzenia
        #test_Sprzetowy()
        status_przycisku = 1
        
    elif czas_wcisniety >= 3:
        #wylacz_Raspberry()
        status_przycisku = 2
        
def wylacz_Raspberry():
    print("Shutting Down")
    time.sleep(5)
    os.system("sudo shutdown -h now")
    
def test_Sprzetowy():
    czas_startu = time.time()
    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d\' \' -f1"
    IP = subprocess.check_output(cmd, shell = True )
    cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell = True )
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell = True )
    cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
    Disk = subprocess.check_output(cmd, shell = True )
    # Write two lines of text

    draw.text((x, top),"IP: " + str(IP),  font=font, fill=255)
    draw.text((x, top+8),str(CPU), font=font, fill=255)
    draw.text((x, top+16),str(MemUsage),  font=font, fill=255)
    draw.text((x, top+25),str(Disk),  font=font, fill=255)

GPIO.add_event_detect(13, GPIO.FALLING, callback = przycisk_Wcisniety, bouncetime=500)

 #wylaczenie diod led
led_red.value = 1
led_green.value = 1
led_blue.value = 1

while True:
    print(czujnik_gazu.value)
    if(email_wyslany == True):
        led_red.value = 1
        led_blue.value = 0
        poczekanie_z_mailem = poczekanie_z_mailem + 1
        print(poczekanie_z_mailem)
        #Program czeka minute aby wyslac kolejna wiadomosc
        if(poczekanie_z_mailem > 30):
            led_blue.value = 1
            email_wyslany = False
            poczekanie_z_mailem = 0
            brzeczyk.off()
    if(czujnik_gazu.value >= prog_alarmu):
        led_green.value = 1
        led_red.value = 0
        brzeczyk.beep() 
        wyslij_email()
    elif(email_wyslany == False):
        #wylaczenie diody led
        led_green.value = 0
    try:        
        with canvas(device) as draw:
            if (status_przycisku == 1):
                test_Sprzetowy()
            elif(status_przycisku == 2):
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((15,20),"Wylaczanie",fill="white")
            elif(status_przycisku == 3):
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((30,20),str(mostek_rezystancyjny_konwertera.value),fill="white")
                print(str(mostek_rezystancyjny_konwertera.value))
            else:
                wartosc_przeliczona_gaz = int(czujnik_gazu.value*20000) #wprowadzenie poprawki 
                draw.rectangle(device.bounding_box, outline="white", fill="black")
                draw.text((30,20),str(wartosc_przeliczona_gaz)+' ppm',fill="white")
                print(str(wartosc_przeliczona_gaz)+' ppm')
    except:
        print("except")
        raise()
    if (status_przycisku == 1):
        #sprawdzenie czy raspberry podlaczone do wi-fi
        check_if_wifi = subprocess.Popen(['iwgetid'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            output = subprocess.check_output(('grep','ESSID'), stdin=check_if_wifi.stdout)
            led_blue.value=0
            led_green.value=1
            led_red.value=1
        except subprocess.CalledProcessError:
            led_red.value=0
            led_green.value=1
            led_blue.value=1
        brzeczyk.beep()
        sleep(5)
        status_przycisku = 3 #przelaczenie na koleina czesc testu sprzetowego
        brzeczyk.off()
        led_red.value=1
        led_green.value=1
        led_blue.value=1
    elif(status_przycisku == 2):
        status_przycisku = 0
        wylacz_Raspberry()
    elif(status_przycisku == 3):
        sleep(5)
        status_przycisku = 0
    else:
        sleep(2)

GPIO.cleanup()
