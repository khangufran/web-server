import os
import socket
import io
import sys
from datetime import datetime

class Server():
    def __init__(self,server_address):
        # Since  we are using IPv4 address only server_address will be 2-tuple
        # (host,port)

        # Backlog is number of unaccepted connections system will allow before
        # refusing new connections
        backlog = 5

        # Listening socket using IPv4 address system and TCP based connection
        self.listen_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM)
        # Prevents error address already in use by reusing same port
        self.listen_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        # Binding server address to socket
        self.listen_socket.bind(server_address)
        # Activating socket
        self.listen_socket.listen(backlog)

        # Information about server
        self.hostname = socket.getfqdn(server_address[0])
        self.port = server_address[1]

        # Headers returned by web application
        self.headers_set = []

    def set_application(self,application):
        # WSGI abiding frameworks provide an application callable that is used to
        # communicate between server and web framework
        self.application = application

    def start_serving(self):
        while True:
            # Accepting new connection
            self.client_socket,client_address = self.listen_socket.accept()
            # fork() to create a new process, this allows handling multiple requests
            # at the same time
            pid = os.fork()
            if pid == 0:
                self.listen_socket.close()
                self.handle_request(self.client_socket)
                self.client_socket.close()
                os._exit(0)
            else:
                self.client_socket.close()

    def handle_request(self,client_socket):
        request_content = client_socket.recv(2048)
        request_content = request_content.decode('utf-8')

        # start debug segment
        #for line in request_content.splitlines():
            #print(line)
        #print('\n')
        # end debug segment

        # Getting components of request line
        request_line  = request_content.splitlines()[0]
        method = request_line.split()[0]
        request_uri = request_line.split()[1]
        http_version = request_line.split()[2]

        # Generat env for passing to web application callable as specified in WSGI
        # standards
        env = {}
        env['wsgi.version'] = (1,0)
        env['wsgi.input'] = io.StringIO(request_content)
        env['wsgi.errors']  = sys.stderr
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.multithread']  =False
        env['wsgi.multiprocess']  = False
        env['wsgi.run_once'] = False

        env['REQUEST_METHOD'] = method
        env['PATH_INFO'] = request_uri
        env['SERVER_NAME'] = self.hostname
        env['SERVER_PORT'] = self.port

        # calling application callable and getting back the result generated by
        # web application
        result = self.application(env,self.start_response)

        # finishing response by calling finish_response to send all relevant headers
        # along with body
        self.finish_response(result)

    def start_response(self,status,response_headers,exc_info=None):
        # Populating all headers to be sent along response to client
        server_headers = [('Date',str(datetime.now())),('Server','Simple Web server')]
        self.headers_set = [status,response_headers+server_headers]

    def finish_response(self,result):
        status = self.headers_set[0]
        # Response status line
        response = f'HTTP/1.1 {status}\n'
        
        # Adding all headers in response
        headers = self.headers_set[1]
        for header in headers:
            response+=f'{header[0]}: {header[1]}\n'
        response += '\n'
        
        # Adding result from web-application in response
        for data in result:
            response += data.decode('utf-8')
            
        # start debug segment
        #for line in response.splitlines():
            #print(line)
        #print('\n')
        # end debug segment

        # Sending response to client and closing the connection
        response_bytes = response.encode()
        self.client_socket.sendall(response_bytes)
        self.client_socket.close()
