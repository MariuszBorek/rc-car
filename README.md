# RC Car on Raspberry Pi 4

### 1. File rc_car_code.py save in:<br>
`/home/pi/racing/controller.py`
<br><br>

### 2. File `racing-controller.service` save in:<br>
`/etc/systemd/system/racing-controller.service`
<br><br>

### 3. activate service:
```
sudo systemctl daemon-reload

sudo systemctl enable pigpiod
sudo systemctl enable racing-controller

sudo systemctl start racing-controller
```
<br>

### 4. Logs:<br><br>
`journalctl -u racing-controller -f`
