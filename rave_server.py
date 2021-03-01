#!/usr/bin/env python

from SimpleHTTPServer import SimpleHTTPRequestHandler
from openravepy import *
import BaseHTTPServer
import argparse
import simplejson
import numpy as np

rave_env = Environment()
ROBOT_DATA_TYPES = [
    'DOFAccelerationLimits',
    'DOFLimits',
    'DOFTorqueLimits',
    'DOFValues',
    'DOFVelocityLimits',
    'DOFWeights',
    'Name']


class RequestHandler(SimpleHTTPRequestHandler):
    global rave_env

    def _set_headers(self, response_code=200):
        self.send_response(response_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def _encode(self, response={}, success=1, error_message='', file=None):
        response['Success'] = success
        response['Error Message'] = error_message
        response['Robots'] = [r.GetName() for r in rave_env.GetRobots()]

        return simplejson.dumps(response)

    def do_GET(self):
        output = self._encode()

        self._set_headers()
        self.wfile.write(output)

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        response_code = 200

        content_length = int(self.headers['Content-Length'])
        data = simplejson.loads(self.rfile.read(content_length))
        response_data = {}

        try:
            post_type = data['type']
            if post_type == 'add':
                xml_data = simplejson.loads(data['xml'])
                new_robot = rave_env.ReadRobotXMLData(xml_data)
                rave_env.AddRobot(new_robot)

            elif post_type == 'set':
                robot_name = data['robot']
                robot = rave_env.GetRobot(robot_name)
                set_dict = data['set']

                for key, val in set_dict.items():
                    method = 'Set'+key
                    getattr(robot, method)(val)

            elif post_type == 'remove':
                robot_name = data['robot']
                rave_env.Remove(rave_env.GetRobot(robot_name))

            elif post_type == 'download':
                pass

            else:
                # Unknown request type
                response_code = 418
                response_data = {'success': 0,
                                 'error_message': 'Unknown POST request type'}

        except:
            response_code = 400
            response_data = {'success': 0, 'error_message': 'Bad syntax'}

        self._set_headers(response_code)
        self.wfile.write(self._encode(**response_data))


def start_server(server_class=BaseHTTPServer.HTTPServer, handler_class=RequestHandler, addr="0.0.0.0", port=8888, env=None):
    global rave_env
    rave_env.Load(env)

    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print("Starting openRAVE environment {}".format(env))
    print("Starting HTTP server on {}:{}".format(addr, port))
    httpd.serve_forever()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Initialize an openRAVE environment and spin a server to handle requests")
    parser.add_argument("-l", "--listen",
                        default="0.0.0.0",
                        help="Server IP address")
    parser.add_argument("-p", "--port",
                        type=int,
                        default=8888,
                        help="Server port",
                        )
    parser.add_argument("-e", "--env",
                        default="data/lab1.env.xml",
                        help="openRAVE environment",
                        )
    args = parser.parse_args()
    start_server(addr=args.listen, port=args.port, env=args.env)
