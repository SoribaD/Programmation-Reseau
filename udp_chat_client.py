# -*- coding: utf-8 -*-
import struct
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import logging
from twisted.internet import reactor
logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_client_protocol')


class c2wUdpChatClientProtocol(DatagramProtocol):

    def __init__(self, serverAddress, serverPort, clientProxy, lossPr):
        """
        Class implementing the UDP version of the client protocol.
        
        Parameters
        ----------
        serverAddress : The IP address (or the name) of the c2w server, given 
        by the user.
            
        serverPort : The port number used by the c2w server, given by the user.
            
        clientProxy : The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.


        Attributes
        ----------
        serverAddress : The IP address of the c2w server.

        serverPort : The port number of the c2w server.

        clientProxy : The clientProxy, which the protocol must use to interact
        with the Graphical User Interface.

        lossPr : The packet loss probability for outgoing packets. Do not 
        modify this value!  (It is used by startProtocol.)            
        """

        #: The IP address of the c2w server.
        self.serverAddress = serverAddress
        #: The port number of the c2w server.
        self.serverPort = serverPort
        #: The clientProxy, which the protocol must use
        #: to interact with the Graphical User Interface.
        self.clientProxy = clientProxy
        self.lossPr = lossPr
        self.seqNumSent=0
        self.sessionToken=0
        self.timer=0
        self.userID=0
        self.roomRequested=[]
        self.roomStructure={}

    def startProtocol(self):
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport

    def sendMsg(self,msg,host_port):
        print(msg)
        self.transport.write(msg,host_port)

    def sendLoginRequestOIE(self, userName):
        """
        The client proxy calls this function when the user clicks on the login
        button.
        
        Parameters
        ----------
        userName: string
            The user name that the user has typed.
        """
        moduleLogger.debug('loginRequest called with username=%s', userName)
        
        #connection request
        version=0b1<<28             
        typ1=0b1<<24
        self.sessionToken=0
        hybrid= version + typ1 + self.sessionToken
        payloadS=len(userName.encode('utf-8'))+4
        USER=userName.encode('utf-8')
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        payload =  struct.pack('!HH'+str(len(USER))+'s',self.userID,len(USER),
                               USER)
        packet = header + payload
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,
                                     (self.serverAddress,self.serverPort))
        self.seqNumSent+=1

        
    def roomStateRequest(self):
        #request for rooms
        version=0b1<<28
        typ=0b11<<24
        self.type_sent=3
        hybrid=version + typ + self.sessionToken
        payloadS=0
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        packet=header
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,
                                     (self.serverAddress,self.serverPort))  
        self.seqNumSent+=1


    def sendChatMessageOIE(self, message):
        """
        Called by the client proxy  when the user has decided to send a chat
        message

        Parameters
        ----------
        message : string
            The text of the chat message.
      

        
        Note
        ----
        This is the only function handling chat messages, irrespective of the 
        room where the user is.  Therefore it is up to the 
        c2wChatClientProctocol or to the server to make sure that this message 
        is handled properly, i.e., it is shown only by the client(s) who are in
        the same room.
        """
        self.message_sent.append(message)
        version=0b1<<28
        typ=0b110<<24
        self.type_sent=6
        hybrid=version + typ + self.sessionToken
        payloadS=len(message) + 2
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        MSG=message.encode('utf-8')
        payload = struct.pack('!HH'+str(len(MSG))+'s',self.userID,len(MSG)
        ,MSG)
        packet=header+payload
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,
                                     (self.serverAddress,self.serverPort))
        self.seqNumSent+=1

    
    def sendJoinRoomRequestOIE(self, roomName):
        """
        Called by the client proxy  when the user has clicked on the watch 
        button or the leave button, indicating that she/he wants to change room.
        
        Parameters
        ----------
        roomName: string
            The room name (or movie title.)

        Note
        -----
        The controller sets roomName to
        c2w.main.constants.ROOM_IDS.MAIN_ROOM when the user
        wants to go back to the main room.
        """
        self.roomRequested.append(roomName)
        version=0b1<<28
        typ=0b101<<24
        self.type_sent=5
        hybrid=version + typ + self.sessionToken
        payloadS=2
        idRoom=self.roomStructures[roomName]
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        payload=struct.pack('H',idRoom)
        packet=header+payload
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,
                                     (self.serverAddress,self.serverPort))
        self.seqNumSent+=1

    
    def sendLeaveSystemRequestOIE(self):
        """
        Called by the client proxy  when the user has clicked on the leave 
        button in the main room.
        """
        version=0b1<<28
        typ=0b111<<24
        self.type_sent=7
        hybrid=version + typ + self.sessionToken
        payloadS=0
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        packet=header
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,
                                     (self.serverAddress,self.serverPort))
        self.seqNumSent+=1

   
    def datagramReceived(self, datagram, host_port):
        """
        Called by Twisted when the client has received a UDP packet.
        
        Parameters
        ----------
        datagram : string
            the payload of the UDP packet.
            
        host_port: tuple
            a tuple containing the source IP address and port.
        """
        hybrid, seqNum, payloadS = struct.unpack_from('!IHH',datagram,0)
        datagram_typ=(hybrid & 0b1111<<24) >>24
        datagram_sessionToken=hybrid & 0b111111111111111111111111
        self.sessionToken=datagram_sessionToken
        if datagram_typ==0:
            if seqNum==self.seqNumSent - 1:
                self.timer.cancel()
        elif datagram_typ==2:
            self.acquittement(seqNum,host_port)
                
   
    def acquittement(self,seqNum,host_port):
        version=0b1<<28
        typ=0b0<<24
        hybrid=version+typ+ self.sessionToken
        packet=struct.pack('!IHH',hybrid,seqNum,0)
        self.sendMsg(packet, host_port)