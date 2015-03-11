## Standard set for Ice
import sys, traceback#, Ice
import time
from math import *
import random
import csv
import lineutils
import pika

eps = 1.0e-10

bearing_noise = 0.3 ## Noise parameter: should be included in sense function.
steering_noise = 0.1 ## Noise parameter: should be included in move function.
distance_noise = 0.1 ## Noise parameter: should be included in move function.

world_x_range = [0.0, 0.0]
world_y_range = [0.0, 0.0]

room_plan = []

n = None
z = None

userinfo = pika.PlainCredentials('bbb','123123')
connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='172.21.11.242', credentials=userinfo))

channel1 = connection.channel()
channel2 = connection.channel()

def move(particle, motion):
    (x,y,theta0) = particle
    (delta_theta, s) = motion
    delta_theta = random.gauss(delta_theta, steering_noise)
    s = random.gauss(s, distance_noise)
    
    theta = theta0 + delta_theta;
    x += s * cos(theta)
    y += s * sin(theta)

    return (x,y,theta)

def measurement_prob(plan_list, particle, measurements):
    ## exclude particles outside the room
    if not lineutils.point_inside_polygon(plan_list, particle):
        return 0.0

    ## calculate the correct measurement
    predicted_measurements = lineutils.measurements(room_plan, particle)

    ## compute errors
    prob = 1.0
    count = 0
    for i in xrange(0, len(measurements)):
        if measurements[i] != 0:
            error_mes = abs(measurements[i] - predicted_measurements[i])

            prob += (exp(- (error_mes ** 2) / (bearing_noise ** 2) / 2.0) / sqrt(2.0 * pi * (bearing_noise ** 2)))
            count += 1
    prob /= count
    prob = prob ** 4
    
    return prob

def callback(ch, method, properties, body):
    global n
    n = body
    print " [x] Done receiving particle"
    ch.basic_ack(delivery_tag = method.delivery_tag)

    channel1.stop_consuming()

def callback1(ch, method, properties, body):
    global z
    z = body
    print " [x] Done receiving measurement"
    ch.basic_ack(delivery_tag = method.delivery_tag)

    channel1.stop_consuming()

with open('plan.dat', 'r') as planfile:
    planreader = csv.reader(planfile, delimiter='\t')
    b = None
    for (x, y) in planreader:
        ## Calculate world boundaries
        if float(x) < world_x_range[0]:
            world_x_range[0] = float(x)
        elif float(x) > world_x_range[1]:
            world_x_range[1] = float(x)

        if float(y) < world_y_range[0]:
            world_y_range[0] = float(y)
        elif float(y) > world_y_range[1]:
            world_y_range[1] = float(y)

        ## Construct wall segment and add to the room_plan
        if b is not None:
            a = b
            b = (float(x), float(y))
            room_plan.append((a,b))
        else:
            b = (float(x), float(y))

while True:
    channel1.queue_declare(queue='particle', durable=True)
    print ' [*] Waiting for messages(pariticle).'

    channel1.basic_qos(prefetch_count=1)
    channel1.basic_consume(callback,
                        queue='particle')

    channel1.start_consuming()

    split_list = n.split()
    change_float = map(float, split_list)
    change_list = [change_float[i:i+3] for i in range(0, len(change_float),3)]
    motion = change_list[len(change_list)-1]
    del change_list[len(change_list)-1]
    p = change_list

    print 'praticle len', len(p)

    ##update movement
    p = map(lambda particle: move(particle, motion), p)


    channel1.queue_declare(queue='measurement', durable=True)
    print ' [*] Waiting for messages(measurement).'

    channel1.basic_qos(prefetch_count=1)
    channel1.basic_consume(callback1,
                        queue='measurement')

    channel1.start_consuming()

    measurement = z.split()
    Z = map(float, measurement)
    print 'Z', Z

    ##update weight
    w = map(lambda particle: measurement_prob(room_plan, particle, Z), p)


    w_str = ' '.join(str(n) for n in w)
    p_str = ' '.join(' '.join(map(str,l)) for l in p)

    w_and_p = w_str + 'A' + p_str

	## First PC
    channel2.queue_declare(queue='w_and_p1', durable=True)

    channel2.basic_publish(exchange='',
                    routing_key='w_and_p1',
                    body=w_and_p,
                    properties=pika.BasicProperties(
                        delivery_mode = 2, # make message persistent
                    ))
    print 'Done sending w and p'

##change @@
##channel@@.queue_declare(queue='w_and_p@@', durable=True)
##
##    channel@@.basic_publish(exchange='',
##                    routing_key='w_and_p@@',
##                    body=w_and_p,
##                    properties=pika.BasicProperties(
##                        delivery_mode = 2, # make message persistent
##                    ))
##    print 'Done sending w and p'

##ex) Second PC
##    channel3.queue_declare(queue='w_and_p2', durable=True)
##
##    channel3.basic_publish(exchange='',
##                    routing_key='w_and_p2',
##                    body=w_and_p,
##                    properties=pika.BasicProperties(
##                        delivery_mode = 2, # make message persistent
##                    ))
##    print 'Done sending w and p'

## third PC
##    channel4.queue_declare(queue='w_and_p3', durable=True)
##
##    channel4.basic_publish(exchange='',
##                    routing_key='w_and_p3',
##                    body=w_and_p,
##                    properties=pika.BasicProperties(
##                        delivery_mode = 2, # make message persistent
##                    ))
##    print 'Done sending w and p'
