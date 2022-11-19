import tinyweb
import network
import time
import json
import machine
import uasyncio as asyncio

from machine import Pin, I2C, UART
from lcd_api import LcdApi
from machine_i2c_lcd import I2cLcd
from time import sleep
from AS_GPS import AS_GPS
from math import floor, modf

# Globals
rs232DictArr = []
gpsDictArr = []

# LCD
I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16

i2c = I2C(scl=Pin(21), sda=Pin(22), freq=10000)
lcd_obj = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)
lcd_obj.putstr("Waiting for GPS")

# Control the MOSFETs for power selection.
# Be careful not to turn both of them on if you have two supplies connected >.<
ext_pwr_status = Pin(19, Pin.IN)
ext_pwr_ctrl = Pin(18, Pin.OUT)
ext_pwr_ctrl.on() # Turn off external power because we don't want to kill the regulator (need to replace with a new buck converter).

usb_pwr_stats = Pin(4, Pin.IN)
usb_pwr_ctrl = Pin(5, Pin.OUT)
usb_pwr_ctrl.off() # Turn on USB power for charging.

# Magnetometer serial
magSerial = UART(1, 9600, bits=7, parity=None, stop=2, rx=16, tx=10)

# We implement a falling edge detector in software instead of using a hardware interrupt for two reasons.
# Firstly, the time savings between asynchronously polling the pin and using a hardware interrupt is negligible.
# Secondly, introducing an interrupt into asynchronous code increases the complexity of the code.
magSyncPin = Pin(23, mode=Pin.IN)
pin_state = magSyncPin.value()
last_pin_state = pin_state

# GPS serial
gpsSerial = UART(2, baudrate=9600, bits=8, parity=None, stop=1, tx=25, rx=33) 
sreader = asyncio.StreamReader(gpsSerial)
gps = AS_GPS(sreader)
isGPSReady = False

# Create web server application
app = tinyweb.webserver()

async def gpsRecv():
    while True:
        global isGPSReady
        if isGPSReady == False:
            await gps.data_received(position=True, altitude=True)
            lcd_obj.clear()
            lcd_obj.putstr("GPS ready\nSurvey can begin")
            isGPSReady = True
            await asyncio.sleep_ms(100)
        else:
            while True:
                pin_state = magSyncPin.value()
                if not pin_state and last_pin_state:
                    # read gps
                    print("Reading GPS\n")
                    await gps.data_received(position=True, altitude=True)
                    lcd_obj.clear()
                    lcd_obj.putstr("lat:" + gps.latitude_string(coord_format=4) + "\nlon:" + gps.longitude_string(coord_format=4))
                    global gpsDictArr
                    gpsDictArr.append({"lat": gps.latitude_string(coord_format=4), "lon": gps.longitude_string(coord_format=4), "altitude": str(gps.altitude)})
                    await asyncio.sleep_ms(100)

                last_pin_state = pin_state
                await asyncio.sleep_ms(10)

async def rs232Recv(uart):
    reader = asyncio.StreamReader(uart)
    while True:
        message = await reader.readline()
        await asyncio.sleep_ms(100)
        message = message.decode("ASCII")

        # Using the info in the manual, we can split up the output from the magnetometer.
        lineNum = message[1:4]
        julianDay = message[5:8]
        time = message[9:15]
        stationNum = message[16:20]
        field = message[21:27]

        # Format the time so it changes from hhmmss to hh:mm:ss.
        time = str(time[:2]) + ":" + str(time[2:4]) + ":" + str(time[4:6])

        # Replace any question marks with zeros. This happens because of a bug in the G-856AX's serial code.
        if '?' in field:
            field = field.replace('?', '0')

        # Format the field reading to have its decimal point. A raw value is 517643 which is formatted to 51764.3
        field = field[:len(field) - 1] + "." + field[len(field) - 1:]

        rs232DictArr.append({"lineNum": str(lineNum), "julianDay": str(julianDay), "time": str(time), "stationNum": str(stationNum), "field": str(field)})

        await asyncio.sleep_ms(100)


# Landing page
@app.route('/')
async def index(request, response):
    global rs232DictArr
    global gpsDictArr
    
    # Start HTTP response with content-type text/html
    await response.start_html()

    vals = ""
    # This if statement should just check that each magnetometer reading has a corresponding gps reading.
    if len(rs232DictArr) != 0 and len(gpsDictArr) != 0 and len(rs232DictArr) == len(gpsDictArr):
        #vals = "lineNum, julianDay, time, stationNum, field, lat, lon, altitude\b"
        for i in range(len(rs232DictArr)):
            vals += json.dumps(rs232DictArr[i]) + json.dumps(gpsDictArr[i])
    else:
        # Our device is just being used to pull readings from the magnetometer. It wasn't used to save GPS values for each reading.
        if len(rs232DictArr) != 0 and len(gpsDictArr) == 0:
            #vals = "lineNum, julianDay, time, stationNum, field\n"
            for i in range(len(rs232DictArr)):
                vals += json.dumps(rs232DictArr[i]) 

    strHtml = """<!DOCTYPE html>
    <html>
    <head>
         <title>MAGNETT | Home</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="/css" rel="stylesheet">
        <style>
            html {
                font-family: Arial;
                display: inline-block;
                margin: 0px auto;
                text-align: center;
            }

            .button {
                background-color: #000000;
                border: none;
                color: white;
                padding: 16px 40px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border-radius: 25px;
            }
        </style>
        <script>/*
            function download(filename, text) {
                let element = document.createElement('a');
                element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
                element.setAttribute('download', filename);

                element.style.display = 'none';
                document.body.appendChild(element);
                element.click();
                document.body.removeChild(element);
            }*/
        </script>
    </head>

    <script>
    function download()
    {
        var dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify('""" + vals + """'));
        var readings = document.createElement('a');
        readings.setAttribute("href",     dataStr);
        readings.setAttribute("download", "measurements.txt");
        document.body.appendChild(readings); // required for firefox
        readings.click();
        readings.remove();
    }
    </script>

    <body>
        <h2>MAGNETT Home</h2>
        <p>
            <a href=\"table\"><button class="btn btn-primary">Show Table</button></a>
        </p>
        <p>
            <a href=\"graph\"><button class="btn btn-primary">Show Graph</button></a>
        </p>
        <p>
        
        <button class="btn btn-primary" onclick="download()">Download Magnetometer value as txt</button> 
        <a id="readings" style="display:none"></a>

        <!--<form onsubmit="download('Magnetometer Values', 'vals')">
            <input type="submit" class="btn btn-primary" value="Download readings as txt">
        </form>-->
        </p>
    </body>
    </html>
    """

    # Send actual HTML page
    await response.send(strHtml)

@app.route('/about')
async def index(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()

    strHtml = """
    <!DOCTYPE html>
    <html>
    <head>
         <title>MAGNETT | About</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="/css" rel="stylesheet">
    </head>

    <body>
        <h2>MAGNETT About</h2>
        <p>
            This device was made for the Geoscience Department by Huan Lei and Nicholas Warrener for their final year investigation project. The code and design files can be found on GitHub by searching for the 'MAGNETT' repo maintained by Ray-R4y and UntidyRAM.
        </p>
    </body>
    </html>
    """
    
    # Send actual HTML page
    await response.send(strHtml)

@app.route('/js')
async def getChartLib(req, res):
    await res.send_file('/Chart.js')

@app.route('/css')
async def getChartLib(req, res):
    await res.send_file('/bootstrap.min.css')

#this is  where the chart.js and the new page will be using the /table with button above
@app.route('/table')
async def table(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()

    if len(gpsDictArr) != 0:
        await response.send('<!DOCTYPE html><html><head><title>MAGNETT | Table</title><link href="/css" rel="stylesheet"></head><body><h1>Raw values</h1>'
                            '<table class="table table-striped">'
                            '<thead>'
                                '<tr>'
                                    '<th scope="col">Time (hh:mm:ss)</th>'
                                    '<th scope="col">Magnitude (nT)</th>'
                                    '<th scope="col">Latitude (&deg;)</th>'
                                    '<th scope="col">Longitude (&deg;)</th>'
                                    '<th scope="col">Altitude (m)</th>'
                                    '</tr>'
                            '</thead>'
                            '<tbody>')

        # The table value here is a bit tricky, but we can pull it off from list, the format underneath here
        # so if we want the x and y value we put in change  it to format(x,y)

        cntr = 0

        for x in rs232DictArr:
            jsonData = json.dumps(x)
            data = json.loads(jsonData)

            tempJsonData = json.dumps(gpsDictArr[cntr])
            tempData = json.loads(tempJsonData)

            await response.send('<tr><th scope="row">' + data['time'] + '</th><td>' + data['field'] + '</td><td>' + tempData['lat'] + '</td><td>' + tempData['lon'] + '</td><td>' + tempData['altitude'] + '</td></tr>')
            
            cntr = cntr + 1

    else:
        await response.send('<!DOCTYPE html><html><head><title>MAGNETT | Table</title><link href="/css" rel="stylesheet"></head><body><h1>Raw values</h1>'
                            '<table class="table table-striped">'
                            '<thead>'
                                '<tr>'
                                    '<th scope="col">Time (hh:mm:ss)</th>'
                                    '<th scope="col">Magnitude (nT)</th>'
                                    '</tr>'
                            '</thead>'
                            '<tbody>')

        # The table value here is a bit tricky, but we can pull it off from list, the format underneath here
        # so if we want the x and y value we put in change  it to format(x,y)

        for x in rs232DictArr:
            jsonData = json.dumps(x)
            data = json.loads(jsonData)

            await response.send('<tr><th scope="row">' + data['time'] + '</th><td>' + data['field'] + '</td></tr>') 

    await response.send('</tbody></table>'
                        """<button type="button" class="btn btn-dark" onclick="history.go(-1)">Back</button></html>""")
    
@app.route('/graph')
async def graph(request, response):
    # Start HTTP response with content-type text/html
    await response.start_html()
  
    xValue = ""
    yValue = ""
    #try getting real values
    for x in rs232DictArr:
        jsonData = json.dumps(x)
        data = json.loads(jsonData)
        xValue = xValue + "'"+(data['time']) + "',"
        yValue = yValue + "'"+(data['field']) + "',"   
    xValue = xValue[:-1]
    yValue = yValue[:-1]
    #print(xValue)
    await response.send("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAGNETT | Graph</title>
        <link href="/css" rel="stylesheet">
    </head>
    <script type="application/javascript" src="/js"></script>

    <body>
        <h2>A graph displaying the magnetic field strength versus time</h2>
        <canvas id="FieldStrengthTimeGraph" style="width:100%;max-width:600px"></canvas>

        <script>
            let xValues = [""" + xValue +"""];
            let yValues = [""" + yValue +"""];

            new Chart("FieldStrengthTimeGraph", {
                type: "line",
                data: {
                    labels: xValues,
                    datasets: [{
                        fill: false,
                        lineTension: 0,
                        backgroundColor: "rgba(0,0,255,1.0)",
                        borderColor: "rgba(0,0,255,0.1)",
                        data: yValues
                    }]
                },
                options: {
                    legend: { display: false },
                    scales: {
                        yAxes: [{
                            scaleLabel: {
                                display: true,
                                labelString: 'Magnitude (nT)'
                            }
                        }],
                        xAxes: [{
                            scaleLabel: {
                                display: true,
                                labelString: 'Time (hhmmss)'
                            }
                        }],
                    }
                }
            });
        </script>
        <button type="button" class="btn btn-dark" onclick="history.go(-1)">
            Back
        </button>
    </body>
    </html>""")
    
          
async def main():
    # -----------------{Act as a router (this is how it will work in our final version)}-----------------
    sta_if = network.WLAN(network.AP_IF)
    sta_if.active(True)
    sta_if.config(essid='MAGNETT', password='123456789')

    while sta_if.active() == False:
        pass

    # Loop_forever=True would turn this function into a blocking function which would stop
    # our code below it from running.
    app.run(host='0.0.0.0', port=80, loop_forever=False)

    loop = asyncio.get_event_loop()
    loop.create_task(rs232Recv(magSerial))
    loop.create_task(gpsRecv())


# These three lines are what actually make everything run.
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
