# -*- coding: utf-8 -*-
import struct
import random
from twisted.internet.protocol import DatagramProtocol
from c2w.main.lossy_transport import LossyTransport
from twisted.internet import reactor
import logging
logging.basicConfig()
moduleLogger = logging.getLogger('c2w.protocol.udp_chat_server_protocol')
import ipaddress
from c2w.main.constants import ROOM_IDS

class c2wUdpChatServerProtocol(DatagramProtocol):

    def __init__(self, serverProxy, lossPr):
        """
        Class implementing the UDP version of the client protocol.
        
        Parameters
        ----------
        serverProxy : The serverProxy the protocol must use
            to interact with the user and movie store (i.e., the list of users
            and movies) in the server.
            
        lossPr : The packet loss probability for outgoing packets.  Do
            not modify this value!
        """
        self.serverProxy = serverProxy
        self.lossPr = lossPr
        self.timer=0
        self.roomTitleID={}
        self.user_room={}
        self.sessionTokens={}
        self.sessionTokens[0]=0
        self.seqNumSent={}
        self.seqNumSent[0]=0
	
		
    def startProtocol(self):
        self.transport = LossyTransport(self.transport, self.lossPr)
        DatagramProtocol.transport = self.transport
	
	
    def datagramReceived(self, datagram, host_port):
        """
        :param string datagram: the payload of the UDP packet.
        :param host_port: a touple containing the source IP address and port.
        
        Twisted calls this method when the server has received a UDP
        packet.  You cannot change the signature of this method.
        """		
        hybrid, seqNum, payloadS = struct.unpack_from('!IHH',datagram,0)        
        datagram_typ=(hybrid & 0b1111<<24) >>24   
        datagram_sessionToken=hybrid & 0b111111111111111111111111
        if not(self.serverProxy.getUserByAddress(host_port)) :
            ID=0
        else:
            if self.serverProxy.getUserByAddress(host_port).userId== None:
                ID=0
            else:
                ID=self.serverProxy.getUserByAddress(host_port).userId

        if datagram_typ==0:
            if seqNum==self.seqNumSent[ID] -1:
                self.timer.cancel()
                reactor.run()
                if seqNum==0:
                    if datagram_sessionToken!=0:
                        self.roomState(ID,host_port)        

        elif datagram_typ==1:
            self.acquittement(seqNum,ID,host_port)
            self.loginResponse(datagram,host_port)

          
    def sendMsg(self,msg,host_port):
        print(msg)
        self.transport.write(msg,host_port)
        
    
    def loginResponse(self,datagram, host_port):
        version=0b1<<28
        typ=0b10<<24
        seqNum=0
        payloadS_datagram= struct.unpack_from('!IHH',datagram,0)[2]
        l=payloadS_datagram-4
        uid, userNameLen, userNameBin = struct.unpack_from('!HH' + str(l) +'s',
                                                           datagram,
                                                           8)
        userName = userNameBin.decode('utf-8')
        print("username :", userName)
        status=self.serverProxy.userExists(userName)
        #successful
        if status==False: 
            response=0
            ID=self.serverProxy.addUser(userName,
                                        ROOM_IDS.MAIN_ROOM, 
                                        userChatInstance=None, 
                                        userAddress=host_port)
            #We store the rooms of the users
            self.user_room[userName]="Main Room"  
            seToken=random.getrandbits(24)
            self.sessionTokens[ID]=seToken
            self.seqNumSent[ID]=0
            self.sessionTokens[seToken]=ID
            hybrid1=version+typ+self.sessionTokens[ID]
            payloadS1=l+5
        else:
            sessionToken=0
            response=3
            hybrid1=version+typ+sessionToken
            ID=0
            payloadS1=l+12
        header = struct.pack('!IHH',hybrid1,seqNum,payloadS1)
        payload =  struct.pack('!BHH'+str(len(userName.encode('utf-8')))+'s',
                               response,
                               ID,
                               len(userName.encode('utf-8')),
                               userName.encode('utf-8'))
        packet= header + payload
        self.sendMsg(packet, host_port)
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,host_port)
        reactor.run()
        self.seqNumSent[ID]+=1
  
      
    def roomState(self,ID,host_port):
        """
        Send the current state of the room
        """
        version=0b1<<28
        typ=0b100<<24
        sessionToken=self.sessionTokens[ID]
        hybrid= version + typ + sessionToken
        payloadS=0
        userName=self.serverProxy.getUserById(ID).userName
        #we recover the position of the user in the dict 
        roomName=self.user_room[userName] 
        #list of all the users                       
        userListAll=self.serverProxy.getUserList()
        #if the user is in the main room             
        if roomName== "Main Room":                              
            roomId=1
            movieIp=0
            moviePort=0
            payloadS+=8
            payloadS+= (len(roomName.encode('utf-8')) +2 )
            payload=struct.pack('!HH'+str(len(roomName.encode('utf-8')))+'sIH',
                                roomId,
                                len(roomName.encode('utf-8')),
                                roomName.encode('utf-8'),
                                movieIp,
                                moviePort)
            userList=[]
            for u in userListAll:
                print("mec al :" ,u.userName)
                print("userchatRoom",u.userChatRoom )
                if self.user_room[u.userName]==roomName:
                    userList.append(u)
                print("tout user :" ,userListAll)
                print("userRoom = " ,self.user_room)
                print("userList :", userList)
            if len(userList)==0:
                payloadS+=2
                payload+=struct.pack('!H', 0)
            else:
                payloadS+=2
                payload+=struct.pack('!H', len(userList))
                for u in userList:
                    payloadS+=2
                    payload+=struct.pack('!H', u.userId)
                    l=len(u.userName.encode('utf-8'))
                    payloadS+=l+2
                    payload+= struct.pack('!H' + str(l) + 's',
                                          l,
                                          u.userName.encode('utf-8'))		
            roomList=self.serverProxy.getMovieList()
            lenght_r=len(roomList)
            payloadS+=2
            payload+=struct.pack('!H', lenght_r)
            for room in roomList:
                payloadS+=2
                payload+=struct.pack('!H',room.movieId)
                print('Movie id: ',room.movieId)
                l=len(room.movieTitle.encode('utf-8'))
                payloadS+=l+2
                payload+=struct.pack('!H' + str(l) + 's',
                                     l,
                                     room.movieTitle.encode('utf-8'))
                payloadS+=4
                IP=room.movieIpAddress
                ip=int(ipaddress.ip_address(IP))
                print("IP :" ,ip)
                payload+= struct.pack('!I', ip)
                payloadS+=2
                payload+=struct.pack('!H',room.moviePort)
                userList=[]
                for u in userListAll:
                    if u.userChatRoom==roomName:
                        userList.append(u)
                if len(userList)==0:
                   payloadS+=2
                   payload+=struct.pack('!H', len(userList))
                else:
                    for u in userList:
                        payloadS+=2
                        payload+=struct.pack('!H', u.userID)
                        l=len(userList.userName.encode('utf-8'))
                        payloadS+=l+2
                        payload+= struct.pack('!H' + str(l) + 's',
                                              l,
                                              u.userName.encode('utf-8'))
                payloadS+=2
                payload+=struct.pack('!H', 0)
        else:
            roomList=self.serverProxy.getMovieList()
            lenght_r=len(roomList)
            payloadS+=2
            payload+=struct.pack('!H', lenght_r)
            for room in roomList:
                payloadS+=2
                payload+=struct.pack('!H',room.movieID)
                l=len(room.movieTitle.encode('utf-8'))
                payloadS+=l+2
                payload+=struct.pack('!H' + str(l) + 's',
                                     l,
                                     room.movieTitle.encode('utf-8'))
                payloadS+=4
               
                IP=room.movieIpAddress
                ip=int(ipaddress.ip_address(IP))              
                payload+= struct.pack('!I', ip)                  
                payloadS+=2
                payload+=struct.pack('!H',room.moviePort)
                userList=[]
                for u in userListAll:
                    if u.userChatRoom==roomName:
                        userList.append(u)
                if len(userList)==0:
                   payloadS+=2
                   payload+=struct.pack('!H', len(userList))
                else:
                    for u in userList:
                        payloadS+=2
                        payload+=struct.pack('!H', u.userID)
                        l=len(userList.userName.encode('utf-8'))
                        payloadS+=l+2
                        payload+= struct.pack('!H' + str(l) + 's',
                                              l,
                                              u.userName.encode('utf-8'))
                payloadS+=2
                payload+=struct.pack('!H', 0)
			
        header = struct.pack('!IHH',hybrid,self.seqNumSent[ID],payloadS)
        packet= header + payload
        self.sendMsg(packet, host_port)
        self.timer=reactor.callLater(1.0,self.sendMsg,packet,host_port)
        self.seqNumSent[ID]+=1
           
		   
    def acquittement(self,seqNum,ID,host_port):
        version=0b1<<28
        typ=0b0<<24
        sessionToken=self.sessionTokens[ID] 
        hybrid=version+typ+sessionToken
        packet=struct.pack('!IHH',hybrid,seqNum,0)
        self.sendMsg(packet, host_port)
    