import socket
import threading
import ipaddress
import queue
import time
from http.client import responses
from FileHandler import FileHandler
from packet import Packet
from packetType import PacketType

'''
    PORT:       Integer     > Port to connect to
    DIRECTORY:  String      > Directory to use
    VERBOSE:    Boolean     > Print debugging information 
'''

class HTTPServerLibrary:

    def __init__(self): 
        # A dictonary that maps a thread to a unique client request
        self.threadMap = {}

    def startServer(self, PORT, DIRECTORY = "Data", VERBOSE = False):
        if not DIRECTORY: 
            DIRECTORY = "Data"
       
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
            server_socket.bind(('localhost', PORT))
            
            while True:
                # Note: sender will always be the router, so it is useless
                data, sender = server_socket.recvfrom(1024)
                
                packet = Packet.from_bytes(data)
                sourceAddress = str(packet.peer_ip_addr) + ':' + str(packet.peer_port)

                # Create a thread for this new connection
                if sourceAddress not in self.threadMap:
                    new_thread = UDPRequest(DIRECTORY, server_socket, packet.peer_ip_addr, packet.peer_port, VERBOSE)
                    self.threadMap[sourceAddress] = new_thread
                    new_thread.start()

                # Push data for this new connection
                self.threadMap[sourceAddress].queue.put(packet)
                
            


class UDPRequest(threading.Thread):
    def __init__(self, directory, connection_socket, clientIPAddress, clientPort, verbose):
        threading.Thread.__init__(self)

        self.queue = queue.Queue()
        self.fileHandler = FileHandler()
        self.curr_seq_num = 0
        self.router_addr = 'localhost'
        self.router_port = 3000
        self.queueTimeout = 2.0  # In seconds

        self.verbose = verbose
        self.connection_socket = connection_socket
        self.clientIPAddress = clientIPAddress
        self.clientPort = clientPort

        self.fileHandler.setDefaultDirectory(directory)

    def run(self):

        while True:
            packet = self.queue.get()
            packetType = PacketType(packet.packet_type)

            if packetType == PacketType.SYN:
                self.__handleHandshake()

            if packetType == PacketType.DATA:
                print("\nRequest Data received")
                request = packet.payload.decode("utf-8")

                # Send back ACK that data has been received
                packet = Packet(packet_type = PacketType.ACK.value,
                                seq_num = 1,
                                peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(self.clientIPAddress)),
                                peer_port = self.clientPort,
                                payload = "")

                self.connection_socket.sendto(packet.to_bytes(), (self.router_addr, self.router_port))
                print("ACK sent for request Data\n")


                '''If requestBody does not exists'''
                if request.count('\r\n\r\n') < 1:
                    responseHeader, responseBody = request, ""
                
                else:
                    responseHeader, responseBody = request.split('\r\n\r\n', 1)
                

                responseData = self.__handleRequest(responseHeader, responseBody)
                self.__sendResponse(responseData)
                return



    def __handleHandshake(self):
            # SYN
            print("SYN request received")
            
            # SYN-ACK
            print("Sending SYN-ACK...")
            packet = Packet(packet_type = PacketType.SYN.value,
                            seq_num = 0,
                            peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(self.clientIPAddress)),
                            peer_port = self.clientPort,
                            payload = "")

            self.connection_socket.sendto(packet.to_bytes(), (self.router_addr, self.router_port))


    def __handleRequest(self, requestHeader, requestBody):
        if self.verbose:
            print('Request from: ', self.clientIPAddress, self.clientPort)
            print('Request Data: ', requestHeader.strip(), requestBody.strip())
            print('\n')

        # Mimicking slow response
        # time.sleep(10)

        filehandlerResponse = self.__processRequest(requestHeader, requestBody)
        response = self.__prepareResponse(filehandlerResponse)

        if self.verbose:
            print('Response Data: ', response)
            print('\n')
        
        return response


    '''
        Processes a incoming request.
        1) Parses the HTTPHeader and extracts the METHOD and PATH
        2) Call the respective fileHandler method depending on the METHOD and PATH
    '''
    def __processRequest(self, requestHeader, requestBody):

        HEADERS = requestHeader.split('\r\n')
        HTTP_META_INFORMATION = HEADERS[0].split(' ')

        METHOD = HTTP_META_INFORMATION[0].strip()
        PATH = HTTP_META_INFORMATION[1].strip()

        if METHOD != 'GET' and METHOD != 'POST':
            return {
                'statusCode': 405,
                'data': 'HTTP Method not supported: ' + METHOD
            }
        
        if METHOD == 'GET':
            if PATH == '/':
                return self.fileHandler.getNamesOfAllFiles()
            
            else:
                return self.fileHandler.getFileContent(PATH[1:])
        
        else:
            if PATH == '/':
                return {
                    'statusCode': 400,
                    'data': 'FileName is null'
                }
            
            else:
                return self.fileHandler.writeToFile(PATH[1:], requestBody)


    def __prepareResponse(self, RESPONSEDATA):

        STATUS_CODE = RESPONSEDATA.get('statusCode')
        HEADERS = RESPONSEDATA.get('headers', [])
        BODY = RESPONSEDATA.get('data', "")

        request = ''

        request += 'HTTP/1.0 '
        request += str(STATUS_CODE) + ' ' + responses[STATUS_CODE]
        
        for HEADER in HEADERS:
            request += '\r\n' + HEADER

        request += '\r\n\r\n'
        request += BODY

        request += '\r\n'

        return request.encode()


    '''
        Internal Method:
            Takes in the application level payload and transform it into a 1024 byte UDP datagram
            The first 11 bytes of the datagram are UDP headers
            The remaining 1013 bytes is for the application level payload
    '''
    def __sendResponse(self, requestData):
        print("Sending Response Data")
            
        packet = Packet(packet_type = PacketType.DATA.value,
                        seq_num = 1,
                        peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(self.clientIPAddress)),
                        peer_port = self.clientPort,
                        payload = requestData)

        self.connection_socket.sendto(packet.to_bytes(), (self.router_addr, self.router_port))

        # wait for ACK and responseData
        while True: 
            try:  
                packet = self.queue.get(True, self.queueTimeout)
                packetType = PacketType(packet.packet_type)
                
                # Packet received, either the Packet is
                # SYN: This packet is a duplicate one due to delays, ignore it
                # ACK: Response reached client => return
                # Data: The request-received-ACK didn't reach the client, so send ACK again

                if packetType == PacketType.SYN:
                    continue

                if packetType == PacketType.ACK:
                    if packet.seq_num == 0:
                        print("Received ACK for the 3 way handshake")
                        print("Handshake completed")
                    else:
                        print("ACK for Response Data received\n")
                        return

                if packetType == PacketType.DATA:
                    print("Received request data again, send ACK again")

                    # Send back ACK
                    packet = Packet(packet_type = PacketType.ACK.value,
                                    seq_num = 1,
                                    peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(self.clientIPAddress)),
                                    peer_port = self.clientPort,
                                    payload = "")

                    self.connection_socket.sendto(packet.to_bytes(), (self.router_addr, self.router_port))
                    print("ACK sent for Request again")

              
            except queue.Empty:
                print("ACK timeout. Resending Response Data...")
                self.__sendResponse(requestData)
                return

