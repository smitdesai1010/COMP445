import socket
import ipaddress
from urllib.parse import urlparse
from packet import Packet
from packetType import PacketType

class HTTPClientLibrary:

    def __init__(self): 
        self.curr_seq_num = 0
        self.router_addr = 'localhost'
        self.router_port = 3000
        self.connectionTimeout = 2.0  # In seconds
        
    '''
    Description: Send a HTTP request via a TCP socket

    Method Parameters
        HOST: The host to send the request to. Should not include the protocol, only the domain names
        HTTP_METHOD
        PATH: String
        HEADERS: An array of strings formatted as 'k:v'. Example: ['Content-Length: 17', 'User-Agent: Concordia-HTTP/1.0']
        BODY_DATA
        VERBOSE: Boolean
        OUTPUT_FILE
    '''
    def sendHTTPRequest(self, HOST, HTTP_METHOD, PATH = "/", HEADERS = [], BODY_DATA = None, VERBOSE = False, OUTPUT_FILE = None):
            if PATH == "":
                PATH = "/"
            
            '''Contains PORT number'''
            if HOST.count(":") == 1:
                HOST, PORT = HOST.split(":")
                PORT = int(PORT)
            else:
                PORT = 80

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:

                self.__handshake(client_socket, HOST, PORT)

                requestData = self.__prepareRequest(HOST, HTTP_METHOD, PATH, HEADERS, BODY_DATA)    
                responseHeader, responseBody = self.__sendRequestData(client_socket, requestData, HOST, PORT)

                '''Check if the response is 302: redirect'''
                if (self.__responseHeaderContainsRedirection(responseHeader)):
                    redirectURL = self.__findRedirectURL(responseHeader)

                    if redirectURL == "":
                        print("Received 302 response code but didn't find the redirection URL")
                        return 

                    '''
                    The redirectURL will of form http://example.com:PORT/path
                    So need to parse out the Domain + Port and the Path + QueryParams
                    '''
                    parsedRedirectURL = urlparse(redirectURL)
                    self.sendHTTPRequest(parsedRedirectURL.netloc, HTTP_METHOD, parsedRedirectURL.path, HEADERS, BODY_DATA, VERBOSE, OUTPUT_FILE)

                else:
                    if VERBOSE:
                        print(responseHeader)

                    if OUTPUT_FILE is not None:
                        file = open(OUTPUT_FILE, "w")
                        file.write(responseBody)
                        file.close()
                    
                    else:
                        print(responseBody)


                # To handle duplicate responses
                self.__handleDuplicateResponse(client_socket, HOST, PORT)

    '''
        Internal Method
        Description: Prepares the HTTP request data to sent from the socket
        Returns: String containing the requestHeader and requestBody encoded into bytes

        Note: 
                - Each line must be seperated by the '\r\n' delimiter
                - Body must be seperated by an extra '\r\n' delimiter
                - Body requires the Content-length Header
                - The request must end with an extra '\r\n' delimiter
    '''
    def __prepareRequest(self, HOST, HTTP_METHOD, PATH, HEADERS, BODY_DATA):
        request = ''
        
        request += HTTP_METHOD + " " + PATH + " HTTP/1.1\r\n"
        request += "Host: " + HOST + "\r\n"

        for HEADER in HEADERS:
            request += HEADER + "\r\n"

        if BODY_DATA is not None:
            request += "Content-Length: " + str(len(BODY_DATA)) + "\r\n"
            request += "\r\n"
            request += BODY_DATA + "\r\n"

        request += "\r\n"
        return request.encode()


    def __responseHeaderContainsRedirection(self, responseHeaderString):
        HEADERS = responseHeaderString.split('\r\n')
        return '302' in HEADERS[0]


    def __findRedirectURL(self, responseHeaderString):
        HEADERS = responseHeaderString.split('\r\n')

        '''Find the Location header and get the redirect URL'''
        for HEADER in HEADERS:
            if 'location' in HEADER.lower():
                key, value = HEADER.split(':', 1)                
                return value.strip()
                
        return ""


    def __handshake(self, connection_socket, server_addr, server_port):
        print("Initiating handshake....")

        # SYN
        packet = Packet(packet_type = PacketType.SYN.value,
                        seq_num = 0,
                        peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(server_addr)),
                        peer_port = server_port,
                        payload = "")
        
        connection_socket.sendto(packet.to_bytes(), (self.router_addr, self.router_port))
        print("SYN sent")

        # SYN-ACK
        try:
            # Set timeout, if not received within timeout, send hanshake again
            connection_socket.settimeout(self.connectionTimeout)
            byteData, sender = connection_socket.recvfrom(1024)
            packet = Packet.from_bytes(byteData)

            connection_socket.settimeout(None)
            print("SYN-ACK received")
        
        except socket.timeout:
            print("SYN-ACK timeout. Restarting handshake...")
            self.__handshake(connection_socket, server_addr, server_port)
            return


        # ACK
        packet = Packet(packet_type = PacketType.ACK.value,
                        seq_num = 0,
                        peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(server_addr)),
                        peer_port = server_port,
                        payload = "")

        connection_socket.sendto(packet.to_bytes(), (self.router_addr, self.router_port))
        print("ACK sent")

        print("Handshake complete\n")


    '''
        Internal Method:
            Takes in the application level payload and transform it into a 1024 byte UDP datagram
            The first 11 bytes of the datagram are UDP headers
            The remaining 1013 bytes is for the application level payload
    '''
    def __sendRequestData(self, connection_socket, requestData, server_addr, server_port):
        print("Sending Request Data")

        packet = Packet(packet_type = PacketType.DATA.value,
                        seq_num = 1,
                        peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(server_addr)),
                        peer_port = server_port,
                        payload = requestData)

        
        connection_socket.sendto(packet.to_bytes(), (self.router_addr, self.router_port))

        # Set timeout, if not received within timeout, send the packet again
        connection_socket.settimeout(self.connectionTimeout)

        # wait for ACK and responseData
        while True: 
            try:  
                byteData, sender = connection_socket.recvfrom(1024)
                packet = Packet.from_bytes(byteData)
                packetType = PacketType(packet.packet_type)
                
                
                # Packet received, either the Packet is
                # SYN-ACK: This packet is a duplicate one due to delays, ignore it
                # ACK: So request reaached server, turn off timeout and wait for response
                # Data: This means the request reached server, so no need to wait for ACK

                if packetType == PacketType.SYN_ACK:
                    continue

                if packetType == PacketType.ACK:
                    connection_socket.settimeout(None)
                    print("ACK for Request Data received\n")

                if packetType == PacketType.DATA:
                    connection_socket.settimeout(None)
                    print("Response Data received\n")

                    # Send back ACK that data has been received
                    ACKpacket = Packet(packet_type = PacketType.ACK.value,
                                    seq_num = 1,
                                    peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(server_addr)),
                                    peer_port = server_port,
                                    payload = "")

                    connection_socket.sendto(ACKpacket.to_bytes(), (self.router_addr, self.router_port))
                    print("ACK for Resposne Data sent")

                    print("Parsing HTTP response data\n")
                    response = packet.payload.decode("utf-8")

                    '''If responseBody does not exists'''
                    if response.count('\r\n\r\n') < 1:
                        return response, ""
                    
                    else:
                        responseHeader, responseBody = response.split('\r\n\r\n', 1)
                        return responseHeader, responseBody
                    
            except socket.timeout:
                print("ACK timeout. Resending Request Data...")
                return self.__sendRequestData(connection_socket, requestData, server_addr, server_port)



    '''
        Internal Method:
            This method is invoked once the response is received.
            The purpose of this method is to handle duplicate responses cause of the following scenario:
                Client receives an response, sends ACK and exits
                This ACK is dropped
                The server timeouts and resends the response again
                So, need to handle this duplicate response
    '''
    def __handleDuplicateResponse(self, connection_socket,  server_addr, server_port):
        while True:
            byteData, sender = connection_socket.recvfrom(1024)
            packet = Packet.from_bytes(byteData)
            # connection_socket.settimeout(None)

            print("Received duplicate response data, sending ACK again")

            # Send back ACK that data has been received
            ACKpacket = Packet(packet_type = PacketType.ACK.value,
                                seq_num = 1,
                                peer_ip_addr = ipaddress.ip_address(socket.gethostbyname(server_addr)),
                                peer_port = server_port,
                                payload = "")

            connection_socket.sendto(ACKpacket.to_bytes(), (self.router_addr, self.router_port))
            print("ACK for Resposne Data sent again")