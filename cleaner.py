#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import yaml
from influxdb import InfluxDBClient
from influxdb import DataFrameClient
import pandas as pd


def parse_args():
    """ parse the args from the command line call """
    parser = argparse.ArgumentParser(description='Read sensor data.')
    parser.add_argument('-c', '--config', type=str,
                        default='airmonitor_config.yml',
                        help='configuration file')
    return parser.parse_args()


def read_configuration(args):
    """
    Read the configuration file.

    :param args: command line arguments submitted with the start of the script
    :return: configuration dictionary
    """
    with open(args.config, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    return cfg


def clean_DHT22_outliers(cfg):
    client = InfluxDBClient(host=cfg['database']['host'],
                            port=cfg['database']['port'],
                            username=cfg['database']['user'],
                            password=cfg['database']['password'],
                            database=cfg['database']['name'])
    query = f"select * from {cfg['DHT22']['measurement']}"
    df = pd.DataFrame(client.query(query, epoch='ns').get_points())

    # filter false readings
    false_readings = df[df['humidity'] > 100].index
    fixed_measurements = df.iloc[false_readings]

    # fix humidity readings
    false_readings = df[df['humidity'] > 100].index
    s1 = df.iloc[false_readings - 1]['humidity'].reset_index(drop=True)
    s2 = df.iloc[false_readings + 1]['humidity'].reset_index(drop=True)
    fixed = pd.concat([s1, s2], axis=1).mean(axis=1)
    fixed.index = false_readings
    fixed_measurements['humidity'] = fixed

    # fix temperature readings
    s1 = df.iloc[false_readings - 1]['temperature'].reset_index(drop=True)
    s2 = df.iloc[false_readings + 1]['temperature'].reset_index(drop=True)
    fixed = pd.concat([s1, s2], axis=1).mean(axis=1)
    fixed.index = false_readings
    fixed_measurements['temperature'] = fixed
    fixed_measurements['time'] = pd.to_datetime(fixed_measurements['time'])
    fixed_measurements = fixed_measurements.set_index('time')

    # write fixed values back to database
    df_client = DataFrameClient(host=cfg['database']['host'],
                                port=cfg['database']['port'],
                                username=cfg['database']['user'],
                                password=cfg['database']['password'],
                                database=cfg['database']['name'])
    df_client.write_points(fixed_measurements, cfg['DHT22']['measurement'])


if __name__ == '__main__':
    args = parse_args()
    cfg = read_configuration(args)
    clean_DHT22_outliers(cfg)
