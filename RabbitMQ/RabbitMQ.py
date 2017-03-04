import os, sys, threading
import pika
import configparser

from multiprocessing import Queue
from ..helpers import getSentinelLogger

Config = configparser.ConfigParser(interpolation=None)
mydir = os.path.dirname(os.path.abspath(__file__))
Config.read(os.path.join(mydir, '..', "global_config.ini"))

defaultuname = Config.get('RabbitMQ', 'Username')
defaultpass  = Config.get('RabbitMQ', 'Password')

# Support Docs: https://www.rabbitmq.com/amqp-0-9-1-reference.html

class Rabbit_Consumer():
    def __init__(self, exchange, routing_key, QueueName, durable=True, exclusive=False, auto_delete=False, host='localhost'):
        self.logger = getSentinelLogger()
        self.exchange = exchange
        self.routing_key = routing_key
        self.processQueue = Queue()

        credentials = pika.PlainCredentials(defaultuname, defaultpass)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                    host=host,
                    port=5672,
                    virtual_host='/',
                    credentials=credentials,
                    socket_timeout=5))

        self.channel = self.connection.channel()
        self.channel.exchange_declare(durable=durable, exchange=self.exchange, type='direct')
        self.channel.queue_declare(queue=QueueName, durable=durable, exclusive=exclusive, auto_delete=auto_delete)
        self.channel.queue_bind(exchange=self.exchange, queue=QueueName, routing_key=self.routing_key)

        self.logger.info('Initialized Rabbit Consumer. Exchange: {}, Routing Key: {}'.format(self.exchange, self.routing_key))

    def callback(self, ch, method, properties, body):
        self.processQueue.put(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

class Rabbit_Producer():
    def __init__(self, exchange, routing_key, QueueName, durable=True, host='localhost'):
        self.logger = getSentinelLogger()
        self.exchange = exchange
        self.routing_key = routing_key

        credentials = pika.PlainCredentials(defaultuname, defaultpass)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                    host=host,
                    port=5672,
                    virtual_host='/',
                    credentials=credentials,
                    socket_timeout=5))

        self.channel = self.connection.channel()
        self.channel.exchange_declare(durable=durable, exchange=exchange, type='direct')

        self.logger.info('Initialized Rabbit Producer. Exchange: {}, Routing Key: {}'.format(self.exchange, self.routing_key))

    def send(self, message):
        self.channel.basic_publish(exchange=self.exchange,
                                   routing_key=self.routing_key,
                                   body=message)