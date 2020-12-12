#!/bin/bash


echo '----- script start -----' > /home/pi/InfluxDB_Grafana_backup.log

# start NAS
echo '----- wake up NAS' >> /home/pi/InfluxDB_Grafana_backup.log
wakeonlan <NA:SM:AC:AD:DR:00> >> /home/pi/InfluxDB_Grafana_backup.log
sleep 150 >> /home/pi/InfluxDB_Grafana_backup.log
echo '----- mount backup folder' >> /home/pi/InfluxDB_Grafana_backup.log
sudo mount -t cifs -o username=RPi_backup,password=<YOURPASSWORD>,vers=3.0 //<NAS IP ADDR>/Raspberry3_AQ_Grafana /mnt/Synology/ >> /home/pi/InfluxDB_Grafana_backup.log

# backup InfluxDB
echo '----- backup InfluxDB' >> /home/pi/InfluxDB_Grafana_backup.log
influxd backup -portable /home/pi/backups/influxdb/ >> /home/pi/InfluxDB_Grafana_backup.log
rm /home/pi/backups/influxdb/InfluxDB_backup.zip >> /home/pi/InfluxDB_Grafana_backup.log
zip -r -m /home/pi/backups/influxdb/InfluxDB_backup.zip /home/pi/backups/influxdb/* >> /home/pi/InfluxDB_Grafana_backup.log
sudo cp /home/pi/backups/influxdb/InfluxDB_backup.zip /mnt/Synology/backups/influxdb/InfluxDB_backup_$(date +%Y-%m-%d_%H-%M-%S).zip >> /home/pi/InfluxDB_Grafana_backup.log

# backup Grafana
echo '----- backup Grafana' >> /home/pi/InfluxDB_Grafana_backup.log
sudo zip -r /home/pi/backups/grafana/Grafana_backup.zip /var/lib/grafana/* >> /home/pi/InfluxDB_Grafana_backup.log
sudo zip -r /home/pi/backups/grafana/Grafana_backup.zip /var/log/grafana/* >> /home/pi/InfluxDB_Grafana_backup.log
sudo zip -r /home/pi/backups/grafana/Grafana_backup.zip /etc/grafana/* >> /home/pi/InfluxDB_Grafana_backup.log
sudo cp /home/pi/backups/grafana/Grafana_backup.zip /mnt/Synology/backups/grafana/Grafana_backup_$(date +%Y-%m-%d_%H-%M-%S).zip >> /home/pi/InfluxDB_Grafana_backup.log

echo '----- script end -----' >> /home/pi/InfluxDB_Grafana_backup.log
