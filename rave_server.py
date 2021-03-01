#!/usr/bin/env python

from SimpleHTTPServer import SimpleHTTPRequestHandler
from openravepy import *
import BaseHTTPServer
import argparse
import simplejson
import numpy as np

rave_env = Environment()
# This was supposed to be used for being able to query the server for data 
# about each robot. Still possible, work needed to JSONify nparrays and send over TCP.
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
        """
        Sets headers for server-side responses. All responses are sent in JSON format.
        """
        self.send_response(response_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def _encode(self, response={}, success=1, error_message='', file=None):
        """
        Encode the responses and add success flag, error message, and list of all robots in the collection. File flag was in anticipation of sending a file to client, but better solution will be to encode XML data in JSON and convert back on client-side (akin to adding a server-side robot).
        """
        response['Success'] = success
        response['Error Message'] = error_message
        response['Robots'] = [r.GetName() for r in rave_env.GetRobots()]

        return simplejson.dumps(response)

    def do_GET(self):
        """
        Base query of which robots are in the collection.
        """
        output = self._encode()

        self._set_headers()
        self.wfile.write(output)

    def do_POST(self):
        """
        Post request handles multiple types of queries:
        
        - [add] Add a new robot to the collection. Requires extra keyword [xml] with data
        - [set] Modify an existing robot. Requires [robot] name and [set] dict with new parameters.
        - [remove] Remove an existing robot from collection. Requires [robot] name.
        - [download] Currently not implemented
        
        Asking for any other request will throw an unkown request error. All other mistakes are assumed to be syntax errors (robot names and attributes are case sensitive).
        """
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

            else: # Unknown request type
                response_code = 418
                response_data = {'success': 0,
                                 'error_message': 'Unknown POST request type'}

        except: # Error in syntax
            response_code = 400
            response_data = {'success': 0, 'error_message': 'Bad syntax'}

        self._set_headers(response_code)
        self.wfile.write(self._encode(**response_data))


def start_server(server_class=BaseHTTPServer.HTTPServer, handler_class=RequestHandler, addr="0.0.0.0", port=8888, env=None):
    global rave_env
    rave_env.Load(env)

    # addr defaults to 0.0.0.0 to allow binding within docker container to host computer's localhost
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
