# -*- coding: utf-8 -*-
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
import logging
from twisted.internet import reactor
logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_client_protocol')
import struct
#import random

class c2wUdpChatClientProtocol(DatagramProtocol):

    def __init__(self, serverAddress, serverPort, clientProxy, lossPr):
        """
        :param serverAddress: The IP address (or the name) of the c2w server,
            given by the user.
        :param serverPort: The port number used by the c2w server,
            given by the user.
        :param clientProxy: The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        Class implementing the UDP version of the client protocol.

        .. note::
            You must write the implementation of this class.

        Each instance must have at least the following attributes:

        .. attribute:: serverAddress

            The IP address of the c2w server.

        .. attribute:: serverPort

            The port number of the c2w server.

        .. attribute:: clientProxy

            The clientProxy, which the protocol must use
            to interact with the Graphical User Interface.

        .. attribute:: lossPr

            The packet loss probability for outgoing packets.  Do
            not modify this value!  (It is used by startProtocol.)

        .. note::
            You must add attributes and methods to this class in order
            to have a working and complete implementation of the c2w
            protocol.
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
        """
        DO NOT MODIFY THE FIRST TWO LINES OF THIS METHOD!!

        If in doubt, do not add anything to this method.  Just ignore it.
        It is used to randomly drop outgoing packets if the -l
        command line option is used.
        """
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport

    def sendMsg(self,msg,host_port):
        print(msg)
        self.transport.write(msg,host_port)

    def sendLoginRequestOIE(self, userName):
        """
        :param string userName: The user name that the user has typed.

        The client proxy calls this function when the user clicks on
        the login button.
        """
        moduleLogger.debug('loginRequest called with username=%s', userName)
        
        #Demande de connexion
        version=0b1<<28             # respect de la spec
        typ1=0b1<<24
        self.sessionToken=0
        hybrid= version + typ1 + self.sessionToken
        #print(bin(hybrid))
        payloadS=len(userName.encode('utf-8'))+4
        USER=userName.encode('utf-8')
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        payload =  struct.pack('!HH'+str(len(USER))+'s',self.userID,len(USER),USER)
        packet = header + payload
        #packet=struct.pack('!IIHH' + str(len(userName)) + 's',hybrid,seqNum,payloadS,ID,USER)
        #print(packet)
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,(self.serverAddress,self.serverPort))
        self.seqNumSent+=1
        #demande de connexion envoyée
      #  self.seqNum+=1  #un message déjà envoyé donc on a un message de plus
        
    def roomStateRequest(self):
        #Demande des salles
        version=0b1<<28
        typ=0b11<<24
        self.type_sent=3
        hybrid=version + typ + self.sessionToken
        payloadS=0
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        packet=header
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,(self.serverAddress,self.serverPort))  #demande de connexion envoyée
        self.seqNumSent+=1
      #  self.seqNum+=1  #un message déjà envoyé donc on a un message de plus

   ## def goToRoom(self,idRoom):
#        version=0b1<<28
#        typ=0b101<<24
#        hybrid=version + typ + self.sessionToken
#        payloadS=2
#        header = struct.pack('!IHH',hybrid,self.seqNum,payloadS)
#        payload=struct.pack('H',idRoom)
#        packet=header+payload
#        self.transport.write(packet, (self.serverAddress,self.serverPort))
        
        
        
        
        
        

    def sendChatMessageOIE(self, message):
        """
        :param message: The text of the chat message.
        :type message: string

        Called by the client proxy  when the user has decided to send
        a chat message

        .. note::
           This is the only function handling chat messages, irrespective
           of the room where the user is.  Therefore it is up to the
           c2wChatClientProctocol or to the server to make sure that this
           message is handled properly, i.e., it is shown only by the
           client(s) who are in the same room.
        """
        self.message_sent.append(message)
        version=0b1<<28
        typ=0b110<<24
        self.type_sent=6
        hybrid=version + typ + self.sessionToken
        payloadS=len(message) + 2
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        MSG=message.encode('utf-8')
        payload =  struct.pack('!HH'+str(len(MSG))+'s',self.userID,len(MSG),MSG)
        packet=header+payload
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,(self.serverAddress,self.serverPort))
        self.seqNumSent+=1

    def sendJoinRoomRequestOIE(self, roomName):
        """
        :param roomName: The room name (or movie title.)

        Called by the client proxy  when the user
        has clicked on the watch button or the leave button,
        indicating that she/he wants to change room.

        .. warning:
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
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,(self.serverAddress,self.serverPort))
        self.seqNumSent+=1

    def sendLeaveSystemRequestOIE(self):
        """
        Called by the client proxy  when the user
        has clicked on the leave button in the main room.
        """
        version=0b1<<28
        typ=0b111<<24
        self.type_sent=7
        hybrid=version + typ + self.sessionToken
        payloadS=0
        header = struct.pack('!IHH',hybrid,self.seqNumSent,payloadS)
        packet=header
        self.sendMsg(packet, (self.serverAddress,self.serverPort))
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,(self.serverAddress,self.serverPort))
        self.seqNumSent+=1

    def datagramReceived(self, datagram, host_port):
        """
        :param string datagram: the payload of the UDP packet.
        :param host_port: a touple containing the source IP address and port.

        Called **by Twisted** when the client has received a UDP
        packet.
        """
        hybrid, seqNum, payloadS = struct.unpack_from('!IHH',datagram,0)
        datagram_version=(hybrid & 0b1111<<28) >>28
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
            

