# MAGNETT 🧲
<b>M</b>agnetometer<br/>
<b>A</b>ugmentation<br/>
<b>G</b>adget for<br/>
<b>N</b>etwork<br/>
<b>E</b>nabled<br/>
<b>T</b>elemetry<br/>
<b>T</b>ransmission<br/>
<br/>

<p align="justify">
MAGNETT is a proof of concept device (or gadget) that allows one to retrieve measurements taken from a G-856AX (manufactured by Geometrics, Inc) over a WiFi connection. It has the ability to save a GPS position for each measurement taken by the G-856AX. It also displays the retrieved data in a table and graph on the web server.  
</p>

By Huan Lei & Nicholas Warrener 

# Dependencies 
## LCD
<p align="justify">
Our project uses a generic 1609 LCD with an I2C 'backpack' to reduce the number of wires needed for communication. We used the 
<a href="https://github.com/dhylands/python_lcd">python_LCD</a> library to configure the LCD and display text. Specifically, <code>machine_i2c_lcd.py</code> and <code>lcd_api.py</code> are used from this library.
</p>

## GPS
<p align="justify">
We used the <code>as_GPS.py</code> driver from the <a href="https://github.com/peterhinch/micropython-async">micropython-async</a> library to enable asynchronously parse the NMEA sentences from the GPS. Just make sure to use V2 and not V3 as the newer version contains functions not supported by the version of micropython-async running on TinyWeb.
</p>

## Webserver
[Bootstrap](https://github.com/twbs/bootstrap/tree/v5.2.2/site/content/docs/5.2)- We used the latest release at the time of writing (V5.2.2) <br/>
[Chart.js](https://www.chartjs.org/docs/2.9.4/) - We used an older version (V2.9.4) of this library because we ran into issues running the latest version<br/>
[TinyWeb](https://github.com/belyalov/tinyweb) - The latest release (V1.3.5) is from 2020 which means we had to use an older version of the as_GPS library.

Assembly instructions and circuit designs are coming soon!
