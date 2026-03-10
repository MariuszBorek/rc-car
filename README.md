# RC Car on Raspberry Pi 4

### 0. Connect module to Raspberry Pi 4:
<br>

![rc_car_diagram_idc_socket.svg](scheme/rc_car_diagram_idc_socket.svg)

### 1. File rc_car_code.py save in:<br>
`/home/pi/racing/controller.py`
<br><br>

### 2. File `racing-controller.service` save in:<br>
`/etc/systemd/system/racing-controller.service`
<br><br>

### 3. activate service:

```shell
sudo systemctl daemon-reload

sudo systemctl enable pigpiod
sudo systemctl enable racing-controller

sudo systemctl start racing-controller
```
<br>

### 4. Logs:<br><br>
```shell
journalctl -u racing-controller -f
```


## systemd commands:

```shell
systemctl status racing-controller

sudo systemctl daemon-reload

sudo systemctl start racing-controller
sudo systemctl stop racing-controller
sudo systemctl restart racing-controller

sudo systemctl disable racing-controller

```