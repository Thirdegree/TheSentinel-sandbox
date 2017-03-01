import sys, threading
import pika
import configparser

from multiprocessing import Queue
from ..helpers import getSentinelLogger

Config = configparser.ConfigParser()
mydir = os.path.dirname(os.path.abspath(__file__))
Config.read(os.path.join(mydir, '..', "global_config.ini"))

defaultuname = Config.get('RabbitMQ', 'Username')
defaultpass  = Config.get('RabbitMQ', 'Password')

# Support Docs: https://www.rabbitmq.com/amqp-0-9-1-reference.html

class Rabbit_Consumer():
    def __init__(self, exchange, routing_key, durable=True, exclusive=False, auto_delete=False, host='localhost'):
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
        result = self.channel.queue_declare(durable=durable, exclusive=exclusive, auto_delete=auto_delete)
        self.queue_name = result.method.queue
        self.channel.queue_bind(exchange=self.exchange, queue=self.queue_name, routing_key=self.routing_key)

        self.logger.info('Initialized Rabbit Consumer. Exchange: {}, Routing Key: {}'.format(self.exchange, self.routing_key))

    def callback(self, ch, method, properties, body):
        self.processQueue.put(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        self.logger.debug('Rabbit recieved message. Exchange: {}, Routing Key: {}'.format(self.exchange, self.routing_key))


class Rabbit_Producer():
    def __init__(self, exchange, routing_key, durable=True, host='localhost'):
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
        self.logger.debug('Rabbit sent message. Exchange: {}, Routing Key: {}'.format(self.exchange, self.routing_key))




#----------
# producer
try:
    rabbit = Rabbit_Producer(exchange='test', routing_key='Test_ToProcess', host='localhost')
    rabbit.send('test message')
except KeyboardInterrupt:
    print('exiting')
except StopIteration:
    print('exiting, sentinel value seen')


#----------
# consumer
try:
    rabbit = Rabbit_Consumer(exchange='test', routing_key='Test_ToProcess', host='localhost')
    rabbit.channel.basic_consume(rabbit.callback, queue=rabbit.queue_name)
    thread = threading.Thread(target=rabbit.channel.start_consuming)
    thread.start()
    for item in iter(rabbit.processQueue.get, b'0'):
        print(item)
except KeyboardInterrupt:
    print('exiting')
except StopIteration:
    print('exiting, sentinel value seen')