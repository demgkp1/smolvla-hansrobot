#!/usr/bin/env python
# _*_ coding:utf-8 _*_

import time
import xmlrpc.client
import socket
import os
import struct
from enum import IntEnum

class RbtFSM(IntEnum):
    enCPSState_UnInitialize=0
    enCPSState_Initialize=1 #1 初始化
    #电箱状态机
    enCPSState_ElectricBoxDisconnect=2 #2 与电箱控制板断开
    enCPSState_ElectricBoxConnecting=3 #3 连接电箱控制板
    enCPSState_EmergencyStopHandling=4 #4 急停处理
    enCPSState_EmergencyStop=5 #5 急停
    enCPSState_Blackouting48V=6 #6 正在切断本体供电
    enCPSState_Blackout48V=7 #7 本体供电已切断
    enCPSState_Electrifying48V=8 #8 正在准备给本体供电
    enCPSState_SafetyGuardErrorHandling=9 #9.安全光幕ErrorHanding
    enCPSState_SafetyGuardError=10 #10.安全光幕Error
    enCPSState_SafetyGuardHandling=11 #11 安全光幕处理
    enCPSState_SafetyGuard=12 #12 安全光幕
    #controller状态机
    enCPSState_ControllerDisconnecting=13 #13 正在反初始化控制器
    enCPSState_ControllerDisconnect=14 #14 控制器已处理于未初始化状态
    enCPSState_ControllerConnecting=15 #15 正在初始化控制器
    enCPSState_ControllerVersionError=16 #16 控制器版本过低错误
    enCPSState_EtherCATError=17 #17 EtherCAT错误
    enCPSState_ControllerChecking=18 #18 控制器初始化后检查状态
    #Robot状态机
    enCPSState_Reseting=19 #19 复位机器人
    enCPSState_RobotOutofSafeSpace=20 #20 机器人超出安全空间
    enCPSState_RobotCollisionStop=21 #21 机器人安全碰撞停车
    enCPSState_Error=22 #22 机器人错误
    enCPSState_Enabling=23 #23 机器人使能中
    enCPSState_Disable=24 #24 机器人去使能
    enCPSState_Moving=25 #25 机器人运动中
    enCPSState_LongJogMoving=26 #26 机器人长点动运动中
    enCPSState_RobotStopping=27 #27 机器人停止运动中
    enCPSState_Disabling=28 #28 机器人去使能中
    enCPSState_RobotOpeningFreeDriver=29 #29 机器人正在开启零力示教
    enCPSState_RobotClosingFreeDriver=30 #30 机器人正在关闭零力示教
    enCPSState_FreeDriver=31 #31 机器人处于零力示教
    enCPSState_RobotHolding=32 #32 机器人暂停
    enCPSState_Standy=33 #33 机器人就绪
    #script状态机
    enCPSState_ScriptRunning=34 #34 脚本运行中
    enCPSState_ScriptHoldHandling=35 #35 脚本暂停处理中
    enCPSState_ScriptHolding=36 #36 脚本暂停
    enCPSState_ScriptStopping=37 #37 脚本停止中
    enCPSState_ScriptStopped=38 #38 脚本已停止
    #HRApp
    enCPSState_HRAppDisconnected=39 #39 HRApp部件断开
    enCPSState_HRAppError=40 #40 HRApp部件错误
    #负载辨识
    enCPSState_RobotLoadIdentify=41 #41 负载辨识
    #brake
    enCPSState_Braking=42 #42 开关抱闸中
    enCPSState_TemperatureTooLow=43 #43 温度过低
    #FT
    enCPSState_FTOpeningFreeDriver=44 #44 机器人正在开启力控零力示教
    enCPSState_FTClosingFreeDriver=45 #45 机器人正在关闭力控零力示教
    enCPSState_FTFreeDriver=46 #46 机器人处于力控零力示教

def ReadFloat(*args,reverse=False):
    for n,m in args:
        n,m = '%04x'%n,'%04x'%m
    if reverse:
        v = n + m
    else:
        v = m + n
    y_bytes = bytes.fromhex(v)
    y = struct.unpack('!f',y_bytes)[0]
    y = round(y,6)
    return y

def WriteFloat(value,reverse=False):
    print(WriteFloat)
    y_bytes = struct.pack('!f',value)
    print(y_bytes)
    y_hex = ''.join(['%02x' % i for i in y_bytes])
    print(y_hex)
    n,m = y_hex[:-4],y_hex[-4:]
    n,m = int(n,16),int(m,16)
    if reverse:
        v = [n,m]
    else:
        v = [m,n]
    return v

def ReadDint(*args,reverse=False):
    for n,m in args:
        n,m = '%04x'%n,'%04x'%m
    if reverse:
        v = n + m
    else:
        v = m + n
    y_bytes = bytes.fromhex(v)
    y = struct.unpack('!i',y_bytes)[0]
    return y

def WriteDint(value,reverse=False):
    y_bytes = struct.pack('!i',value)
    # y_hex = bytes.hex(y_bytes)
    y_hex = ''.join(['%02x' % i for i in y_bytes])
    n,m = y_hex[:-4],y_hex[-4:]
    n,m = int(n,16),int(m,16)
    if reverse:
        v = [n,m]
    else:
        v = [m,n]
    return v

class CPSClient(object):
    clientIP = '127.0.0.1'
    clientPort = 10003
    xmlrpcAddr='http://127.0.0.1:20000'
    params=[]
    
    #def connectTCPSocket(self,IP):        
    #    return self.tcp.connect((clientIP, self.clientPort))
        
    #def closeTCPSocket(self):
    #    return self.tcp.close()

    def __init__(self,IP):
        self.clientIP=IP
        self.xmlrpcAddr='http://'
        self.xmlrpcAddr+=self.clientIP
        self.xmlrpcAddr+=':20000'
        print(self.xmlrpcAddr)
        self.rpcClient = xmlrpc.client.ServerProxy(self.xmlrpcAddr)
        self.tcp = socket.socket()
        self.tcp.connect((self.clientIP, self.clientPort))
        return
    
    def _waitMotion(self,isblending):
        motionIndex=1
        if isblending:
           motionIndex=12
        
        time.sleep(0.02)
        nDisableCNT=0
        while True:
            if (nDisableCNT>=5):
                time.sleep(0.01)
                os._exit(0)
            ret = self.HRIF_ReadRobotState()
            #print(ret)
            # [errorcode, movingState-1, EnableState-2, errorState-3, errorCode-4, errorAxis-5, 
            #  Breaking-6, Pause-7, emergency-8, SafeGraud-9, Electfify-10, sysboradConnect-11,blendingDone-12,Inpos-13]
            
            # disable or error or emergency or BlackOut or sysBorad disconnect
            # in this case, CC will be send Stop cmd to py in anther threading
            # so it just need waiting in here
            if (ret[2] == '0'):
                nDisableCNT+=1
                log = ('[script]EnableState['+ret[2]+'],count['+str(nDisableCNT)+'] error')
                #print(log)
                #self.sendHRLog(2,'[script]EnableState['+ret[3]+'],count['+str(nDisableCNT)+'] error')
                continue
            else:
                nDisableCNT=0
            
            if (ret[3] == '1' or ret[8] == '1' or ret[10] == '0' or ret[11] == '0' ):
                log = ('[script]errorState['+ret[3]+'],emergency['+ret[8]+'],Electfify['+ret[10]+']')
                #self.sendHRLog(2,str(log))
                print(log)
                time.sleep(0.1)
                os._exit(0)
            # SafeGraud
            # if it is stop , CC will be send Stop cmd in anther threading
            # if it is puase, CC will be send Pause in anther threading, and this thread will pause in "is_need_loop_here()"
            # so it just need continue in here;            
            elif ret[9] == '1':
                # print 'ret[10]=='+ret[10]
                time.sleep(0.01)
                continue

            # pause
            # also continue 
            elif ret[7] == '1':
                # print 'ret[8]=='+ret[8]
                time.sleep(0.01)
                continue

            # blending over
            elif ret[motionIndex] == '1':
                log = ('[script]ret['+str(motionIndex)+']=='+ret[motionIndex])
                #print(log)
                #self.sendHRLog(3,str(log))
                break

            # blending 
            elif ret[motionIndex] == '0':
                log = ('ret['+str(motionIndex)+']=='+ret[motionIndex])
                time.sleep(0.01)
                continue


            # unknow status  maybe exit is more safe                
            else: 
                log = ('[script]waitBlendingDone unknow status exit')
                print(log)
                #self.sendHRLog(3,str(log))
                os._exit(0)
        return
       
    #moveC
    def waitMoveDone(self):
        self._waitMotion(False)
    
    '''
    *	@index : 
    *	@param brief:等待运动停止
    '''
    def waitBlendingDone(self):
        self._waitMotion(True)
    
    def waitFSM(self,targetFSM,wait_timeout):
        curFSM=self.HRIF_ReadCurFSM()
        start = time.perf_counter()
        end = time.perf_counter()
        while int(curFSM[1])!=targetFSM:
            end = time.perf_counter()
            if (end-start)>=wait_timeout:
                break
            time.sleep(0.1)
            curFSM=self.HRIF_ReadCurFSM()
        return int(curFSM[1])
        
    def HRIF_FinishInitialize(self):
        command = 'FinishInitialize,;'
        return self.sendAndRecv(command)
    #
    # part 1 初始化
    #
    
    '''
    *	@index : 6
    *	@param brief:机器人上电
    '''
    def HRIF_Electrify(self):
        command = 'Electrify,;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 7
    *	@param brief:机器人断电
    '''
    def HRIF_BlackOut(self):
        command = 'BlackOut,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 8
    *	@param brief:连接控制器，连接过程中会启动主站，初始化从站，配置参数，检查配置，完成后跳转到去使能状态
    
    '''
    def HRIF_Connect2Controller(self):
        command = 'StartMaster,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 9
    *	@param brief:是否为模拟机器人
    *	@param ret[1]: 1:是模拟机器人 2:不是模拟机器人
    '''
    def HRIF_IsSimulateRobot(self):
        command = 'IsSimulation,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 10
    *	@param brief:控制器是否启动完成
    *	@param ret[1]: 1:已完成 2:未完成
    '''
    def HRIF_IsControllerStarted(self):
        command = 'ReadControllerState,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 11
    *	@param brief:读取控制器版本号
    *	@param ret[0]: 错误码
    *	@param ret[1]: 整体版本号
    *	@param ret[2]: CPS 版本 
    *	@param ret[3]: 控制器版本
    *	@param ret[4]: 电箱版本 
    *	@param ret[5]: id控制板固件版本
    *	@param ret[6]: 控制板固件版本
    *	@param ret[7]: 算法版本 
    *	@param ret[8]: 固件版本 
    '''
    def HRIF_ReadVersion(self):
        command = 'ReadVersion,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 12
    *	@param brief:读取机器人类型
    *	@param ret[0]: 错误码
    *	@param ret[1]: 机器人类型
    '''
    def HRIF_ReadRobotModel(self):
        command = 'ReadRobotModel,;'
        return self.sendAndRecv(command)

    #
    # part 2 轴控制指令
    #

    '''
    *	@index : 1
    *	@param brief:机器人使能
    '''
    def HRIF_GrpEnable(self):
        command = 'GrpPowerOn,0,;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 2
    *	@param brief:机器人去使能
    '''
    def HRIF_GrpDisable(self):
        command = 'GrpPowerOff,0,;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 3
    *	@param brief:机器人复位
    '''
    def HRIF_GrpReset(self):
        command = 'GrpReset,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief: 停止命令
    '''
    def HRIF_GrpStop(self):
        return self.sendAndRecv('GrpStop,0,;')
    
    '''
    *	@index : 5
    *	@param brief:暂停运动命令
    '''
    def HRIF_GrpInterrupt(self):
        return self.sendAndRecv('GrpInterrupt,0,;')

    '''
    *	@index : 6
    *	@param brief:继续运动命令
    '''
    def HRIF_GrpContinue(self):
        return self.sendAndRecv('GrpContinue,0,;')

    '''
    *	@index : 7
    *	@param brief:机器人关闭零力示教
    '''
    def HRIF_GrpCloseFreeDriver(self):
        command = 'GrpCloseFreeDriver,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 8
    *	@param brief:机器人打开零力示教
    '''
    def HRIF_GrpOpenFreeDriver(self):
        command = 'GrpOpenFreeDriver,0,;'
        return self.sendAndRecv(command)
    
    #
    # part 3 脚本控制指令
    #

    '''
    *	@index : 1
    *	@param brief:运行指定脚本函数
    *	@param strFuncName : 指定脚本函数名称
    *	@param param : 参数
    '''
    def HRIF_RunFunc(self, funcName, params):
        command = 'RunFunc,'
        command = funcName + ','
        for param in params:
            command += str(param) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 2
    *	@param brief:开始运行脚本
    '''
    def HRIF_StartScript(self):
        command = 'StartScript,0,;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 3
    *	@param brief:停止运行脚本
    '''
    def HRIF_StopScript(self):
        command = 'StopScript,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief:暂停运行脚本
    '''
    def HRIF_PauseScript(self):
        command = 'PauseScript,0,;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 5
    *	@param brief:继续运行脚本
    '''
    def HRIF_ContinueScript(self):
        command = 'ContinueScript,0,;'
        return self.sendAndRecv(command)
    
    #
    # part 4 电箱控制指令
    #

    '''
    *	@index : 1
    *	@param brief:读取电箱信息
    *	@param retData[1] : 电箱连接状态
    *	@param retData[2] : 48V电压状态
    *	@param retData[3] : 48V输出电压值
    *	@param retData[4] : 48V输出电流值
    *	@param retData[5] : 远程急停状态
    *	@param retData[6] : 三段按钮状态
    '''
    def HRIF_ReadBoxInfo(self):
        command = 'ReadBoxInfo,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 2
    *	@param brief:读取电箱控制数字输入状态
    *	@param bit : 控制数字输入位
    *	@param retData[1]: 数字输入状态
    '''
    def HRIF_ReadBoxCI(self, bit):
        command = 'ReadBoxCI,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 3
    *	@param brief:读取通用数字输入状态
    *	@param bit : 通用数字输入位
    *	@param retData[1]: 通用数字输入状态
    '''
    def HRIF_ReadBoxDI(self, bit):
        command = 'ReadBoxDI,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief:读取控制器数字输出状态
    *	@param bit : 控制器数字输出位
    *	@param retData[1]: 数字输出状态
    '''
    def HRIF_ReadBoxCO(self, bit):
        command = 'ReadBoxCO,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 5
    *	@param brief:读取通用数字输出状态
    *	@param bit : 通用数字输出位
    *	@param retData[1]: 通用数字输出状态
    '''
    def HRIF_ReadBoxDO(self, bit):
        command = 'ReadBoxDO,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 6
    *	@param brief:读取模拟量输入值
    *	@param bit : 模拟量输入位
    *	@param retData[1] : 模拟量输入值
    '''
    def HRIF_ReadBoxAI(self, bit):
        command = 'ReadBoxAI,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 7
    *	@param brief:读取模拟量输出值
    *	@param bit : 模拟量输出位
    *	@param retData[1] : 模拟量输出状态 1:电压 2:电流
    *	@param retData[2] : 模拟量输出值
    '''
    def HRIF_ReadBoxAO(self, bit):
        command = 'ReadBoxAO,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 8
    *	@param brief:设置控制数字输出状态
    *	@param bit : 控制数字输出位
    *	@param state : 设置的控股数字输出状态
    '''
    def HRIF_SetBoxCO(self, bit, state):
        command = 'SetBoxCO,' + str(bit) + ',' + str(state) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 9
    *	@param brief:设置通用数字输出状态
    *	@param bit : 通用数字输出位
    *	@param state : 设置的通用数字输出状态
    '''
    def HRIF_SetBoxDO(self, bit, state):
        command = 'SetBoxDO,' + str(bit) + ',' + str(state) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 10
    *	@param brief:设置模拟量模式
    *	@param bit : 模拟量输出位
    *	@param pattern : 模拟量输出模式,1:电压,2:电流
    '''
    def HRIF_SetBoxAOMode(self,index,pattern):
        command = 'SetBoxAOMode,' + str(index) + ',' + str(pattern) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 11
    *	@param brief:设置模拟量输出值和模式
    *	@param bit : 模拟量输出位
    *	@param value : 模拟量输出值
    *	@param pattern : 模拟量输出模式,1:电压,2:电流
    '''
    def HRIF_SetBoxAOVal(self,index,value,pattern):
        command = 'SetBoxAO,' + str(index) + ',' + str(value) + ',' + str(pattern) + ',;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 12
    *	@param brief:设置末端数字输出状态
    *	@param bit : 末端数字输出位
    *	@param state : 末端数字输出值
    '''
    def HRIF_SetEndDO(self, bit, state):
        command = 'SetEndDO,0,' + str(bit) + ',' + str(state) + ',;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 13
    *	@param brief:读取末端数字输入状态
    *	@param bit : 末端输入位
    *	@param retData[1] : 末端输入值
    '''
    def HRIF_ReadEndDI(self, bit):
        command = 'ReadEI,0,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 14
    *	@param brief:读取末端数字输出状态
    *	@param bit : 末端数字输出位
    *	@param retData[1] : 末端数字输出值
    '''
    def HRIF_ReadEndDO(self, bit):
        command = 'ReadEO,0,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 15
    *	@param brief:读取末端模拟量输入状态
    *	@param bit : 末端模拟量输入位
    *	@param retData[1] : 末端模拟量输入值
    '''
    def HRIF_ReadEndAI(self, bit):
        command = 'ReadEAI,0,' + str(bit) + ',;'
        return self.sendAndRecv(command)

    #
    # part 5 状态读取与设置指令 
    #

    '''
    *	@index : 1
    *	@param brief:设置速度百分比
    *	@param vel:速度百分比
    '''
    def HRIF_SetOverride(self, vel):
        command = 'SetOverride,0,' + str(vel) + ',;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 2
    *	@param brief:开启或关闭 Tool 坐标系运动模式
    *	@param state:状态 (0:开启 1:关闭)
    '''
    def HRIF_SetTCPMotion(self, state):
        command = 'SetTCPMotion,0,' + str(state) + ',;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 3
    *	@param brief:设置当前负载参数
    *	@param Mass：质量
    *	@param Center_X：质心X方向偏移
    *	@param Center_Y：质心Y方向偏移
    *	@param Center_Z：质心Z方向偏移
    '''
    def HRIF_SetPayload(self, Mass,Center_X,Center_Y,Center_Z):
        command = 'SetPayload,0,'
        command += str(Mass)
        command += ','
        command += str(Center_X)
        command += ','
        command += str(Center_Y)
        command += ','
        command += str(Center_Z)
        command += ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief:设置关节最大运动速度
    *	@param Joint:轴最大速度
    '''
    def HRIF_SetJointMaxVel(self, Joint):
        command = 'SetJointMaxVel,0,'
        for i in range(0,6):
            command += str(Joint[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 5
    *	@param brief:设置关节最大运动加速度
    *	@param Joint:速度百分比
    '''
    def HRIF_SetJointMaxAcc(self, Joint):
        command = 'SetJointMaxAcc,0,'
        for i in range(0,6):
            command += str(Joint[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 6
    *	@param brief:设置直线运动最大速度
    *	@param MaxVel:最大直线速度
    '''
    def HRIF_SetLinearMaxVel(self, MaxVel):
        command = 'SetLinearMaxVel,0,'
        command += str(MaxVel) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 7
    *	@param brief:设置直线运动最大加速度
    *	@param MaxAcc:最大直线速度
    '''
    def HRIF_SetLinearMaxAcc(self, MaxAcc):
        command = 'SetLinearMaxAcc,0,'
        command += str(MaxAcc) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 8
    *	@param brief:设置最大关节运动范围
    *	@param pMax: J1-J6最大范围
    *	@param pMin: J1-J6最小范围
    '''
    def HRIF_SetMaxAcsRange(self, pMax, pMin):
        command = 'SetMaxAcsRange,0,'
        command += str(pMax[0])
        command += ','
        command += str(pMax[1])
        command += ','
        command += str(pMax[2])
        command += ','
        command += str(pMax[3])
        command += ','
        command += str(pMax[4])
        command += ','
        command += str(pMax[5])
        command += ','
        command += str(pMin[0])
        command += ','
        command += str(pMin[1])
        command += ','
        command += str(pMin[2])
        command += ','
        command += str(pMin[3])
        command += ','
        command += str(pMin[4])
        command += ','
        command += str(pMin[5])
        command += ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 9
    *	@param brief:设置空间最大运动范围
    *	@param pMax: X,Y,Z最大范围
    *	@param pMin: X,Y,Z最小范围
    *	@param pUcs: 用户坐标系参数X,Y,Z,RX,RY,RZ
    '''
    def HRIF_SetMaxPcsRange(self, pMax, pMin,pUcs):
        command = 'SetMaxPcsRange,0,'
        command += str(pMax[0])
        command += ','
        command += str(pMax[1])
        command += ','
        command += str(pMax[2])
        command += ','
        command += str(180)
        command += ','
        command += str(180)
        command += ','
        command += str(180)
        command += ','
        command += str(pMin[0])
        command += ','
        command += str(pMin[1])
        command += ','
        command += str(pMin[2])
        command += ','
        command += str(-180)
        command += ','
        command += str(-180)
        command += ','
        command += str(-180)
        command += ','
        for i in range(0, 6):
            command += str(pUcs[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 10
    *	@param brief:读取关节最大运动速度
    *	@param retData[1-6] : 轴最大速度
    '''
    def HRIF_ReadJointMaxVel(self):
        command = 'ReadJointMaxVel,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 11
    *	@param brief:读取关节最大运动加速度
    *	@param retData[1-6] : 轴最大运动加速度
    '''
    def HRIF_ReadJointMaxAcc(self):
        command = 'ReadJointMaxAcc,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 12
    *	@param brief:读取关节最大运动加加速度
    *	@param retData[1-6] : 轴最大加加速度
    '''
    def HRIF_ReadJointMaxJerk(self):
        command = 'ReadJointMaxJerk,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 13
    *	@param brief:读取直线运动最大速度参数
    *	@param retData[1] : 最大直线速度(单位[mm/ s])
    *	@param retData[2] : 最大直线加速度(单位[mm/ s2])
    *	@param retData[3] : 最大直线加加速度(单位[mm/ s3])
    '''
    def HRIF_ReadLinearMaxSpeed(self):
        command = 'ReadLinearMaxVel,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 14
    *	@param brief:读取直线运动最大速度参数
    *	@param retData[1] : 急停错误
    *	@param retData[2] : 急停信号
    *	@param retData[3] : 安全光幕错误
    *	@param retData[4] : 安全光幕信号
    '''
    def HRIF_ReadEmergencyInfo(self):
        command = 'ReadEmegrency,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 15
    *	@param brief: 读取当前机器人状态标志
    *	@param retData[1] : 运动状态
    *   @param retData[2] : 使能状态
    *   @param retData[3] : 错误状态
    *   @param retData[4] : 错误码
    *   @param retData[5] : 错误轴ID
    *   @param retData[6] : 抱闸是否打开状态
    *   @param retData[7] : 暂停状态
    *   @param retData[8] : 急停状态
    *   @param retData[9] : 安全光幕状态
    *   @param retData[10] : 上电状态
    *   @param retData[11] : 连接电箱状态
    *   @param retData[12] : WayPoint运动完成状态
    *   @param retData[13] : 运动命令位置与实际位置是否到位
    '''
    def HRIF_ReadRobotState(self):
        return self.sendAndRecv('ReadRobotState,0,;')

    '''
    *	@index : 16
    *	@param brief:读取 WayPoint 当前运动 ID 号
    *	@param retData[1]:当前 ID
    '''
    def HRIF_ReadCurWaypointID(self):
        command = 'CurWayPointID,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 17
    *	@param brief:读取错误码
    *	@param retData[1-6] : 轴错误码
    '''
    def HRIF_ReadAxisErrorCode(self):
        command = 'ReadAxisErrorCode,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 18
    *	@param brief:读取状态机状态
    *	@param retData[1] : 当前状态机状态,具体描述见接口说明文档
    '''
    def HRIF_ReadCurFSM(self):
        command = 'ReadCurFSM,0,;'
        return self.sendAndRecv(command)

    #
    # part 6 位置,速度,电流读取指令 
    #

    '''
    *	@index : 1
    *	@param brief:读取当前位置信息
    *	@param retData[1-6] : 迪卡尔坐标
    *	@param retData[7-12] : 关节坐标
    *	@param retData[13-18] : TCP坐标
    *	@param retData[19-24] : 用户坐标
    '''
    def HRIF_ReadActPos(self):
        retData = self.sendAndRecv('ReadActPos,0,;')
        return retData

    '''
    *	@index : 2
    *	@param brief:读取关节命令位置
    *	@param retData[1-6] : 关节命令位置
    '''
    def HRIF_ReadCmdJointPos(self):
        retData =  self.sendAndRecv('ReadCmdPos,0,;')
        return retData

    '''
    *	@index : 3
    *	@param brief:读取关节实际位置
    *	@param retData[1-6] : 关节实际位置
    '''
    def HRIF_ReadActJointPos(self):
        retData =  self.sendAndRecv('ReadActACS,0,;')
        return retData

    '''
    *	@index : 4
    *	@param brief:读取命令 TCP 位置
    *	@param retData[1-6] : 命令TCP位置
    '''
    def HRIF_ReadCmdTcpPos(self):
        retData =  self.sendAndRecv('ReadCmdPos,0,;')
        if retData[0] != '0':
            return retData
        del retData[7]
        del retData[7]
        del retData[7]
        del retData[7]
        del retData[7]
        del retData[7]
        return retData


    '''
    *	@index : 5
    *	@param brief: 读取实际 TCP 位置
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : 迪卡尔坐标
    '''
    def HRIF_ReadActTcpPos(self):
        retData = self.HRIF_ReadActPos()
        if retData[0] != '0':
            return retData
        ActTCP = [retData[0], retData[1], retData[2], retData[3], retData[4], retData[5], retData[6]]
        return ActTCP

    '''
    *	@index : 6
    *	@param brief: 读取关节命令速度
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : 关节命令速度
    '''
    def HRIF_ReadCmdJointVel(self):
        retData =  self.sendAndRecv('ReadCmdJointVel,0,;')
        return retData

    '''
    *	@index : 7
    *	@param brief: 读取关节实际速度
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : 关节实际速度
    '''
    def HRIF_ReadActJointVel(self):
        retData =  self.sendAndRecv('ReadActJointVel,0,;')
        return retData

    '''
    *	@index : 8
    *	@param brief: 读取命令 TCP 速度
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : TCP命令速度
    '''
    def HRIF_ReadCmdTcpVel(self):
        retData =  self.sendAndRecv('ReadCmdTcpVel,0,;')
        return retData

    '''
    *	@index : 9
    *	@param brief: 读取实际 TCP 速度
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : TCP实际速度
    '''
    def HRIF_ReadActTcpVel(self):
        retData =  self.sendAndRecv('ReadActTcpVel,0,;')
        return retData

    '''
    *	@index : 10
    *	@param brief: 读取关节命令电流
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : 关节命令电流 
    '''
    def HRIF_ReadCmdJointCur(self):
        retData =  self.sendAndRecv('ReadCmdJointCur,0,;')
        return retData

    '''
    *	@index : 11
    *	@param brief: 读取关节实际电流
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : 关节实际电流
    '''
    def HRIF_ReadActJointCur(self):
        retData =  self.sendAndRecv('ReadActJointCur,0,;')
        return retData

    '''
    *	@index : 12
    *	@param brief: 读取 TCP 末端速度
    *	@param retData[0] : 错误码
    *	@param retData[1] : 命令速度 
    *	@param retData[2] : 实际速度
    '''
    def HRIF_ReadTcpVelocity(self):
        retData =  self.sendAndRecv('ReadEndVel,0,;')
        return retData

    #
    # part 7 坐标转换计算指令  
    #

    '''
    *	@index : 1
    *	@param brief: 四元素转欧拉角
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : 迪卡尔坐标
    HR_Quaternion2RPY 
    '''

    '''
    *	@index : 2
    *	@param brief: 欧拉角转四元素
    *	@param retData[0] : 错误码
    *	@param retData[1-6] : 迪卡尔坐标
    HR_RPY2Quaternion 
    '''

    '''
    *	@index : 3
    *	@param brief:逆解,由指定用户坐标系位置和工具坐标系下的迪卡尔坐标计算对应的关节坐标位置
    *	@param rawPCS : 需要计算逆解的目标迪卡尔位置
    *	@param rawACS : 参考关节坐标,逆解出现多个解时需要根据参考关节坐标选取最终解
    *	@param tcp : 工具坐标
    *	@param ucs : 用户坐标
    *	@return nRer[1-6] : 用户坐标
    '''
    def HRIF_GetInverseKin(self, rawPCS, rawACS, tcp, ucs):
        command = 'PCS2ACS,0,'
        for i in range(0, 6):
            command += str(rawPCS[i]) + ','
        for i in range(0, 6):
            command += str(rawACS[i]) + ','
        for i in range(0, 6):
            command += str(tcp[i]) + ','
        for i in range(0, 6):
            command += str(ucs[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief:正解，由关节坐标位置计算指定用户坐标系和工具坐标系下的迪卡尔坐标位置
    *	@param rawACS : 需要计算正解的关节坐标
    *	@param tcp : 工具坐标
    *	@param ucs : 用户坐标
    *	@return nRet[1-6] : 目标迪卡尔坐标
    '''
    def HRIF_GetForwardKin(self, rawACS, tcp, ucs):
        command = 'ACS2PCS,0,'
        for i in range(0, 6):
            command += str(rawACS[i]) + ','
        for i in range(0, 6):
            command += str(tcp[i]) + ','
        for i in range(0, 6):
            command += str(ucs[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 5
    *	@param brief:由基座坐标系下的坐标位置计算指定用户坐标系和工具坐标系下的迪卡尔坐标位置
    *	@param Base : 基座坐标系下的迪卡尔坐标位置
    *	@param TCP : 工具坐标
    *	@param UCS : 用户坐标
    *	@return nRet[1-6] : 目标迪卡尔坐标
    '''
    def HRIF_Base2UcsTcp(self, Base, TCP, UCS):
        command = 'Base2UcsTcp,0,'
        for i in range(0, 6):
            command += str(Base[i]) + ','
        for i in range(0, 6):
            command += str(TCP[i]) + ','
        for i in range(0, 6):
            command += str(UCS[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 6
    *	@param brief:由指定用户坐标系和工具坐标系下的迪卡尔坐标位置计算基座坐标系下的坐标位置
    *	@param UcsTcp : 指定用户坐标系和工具坐标系下的迪卡尔坐标
    *	@param TCP : 工具坐标
    *	@param UCS : 用户坐标
    *	@return nRet[1-6] : 目标迪卡尔坐标
    '''
    def HRIF_UcsTcp2Base(self, UcsTcp, TCP, UCS):
        command = 'UcsTcp2Base,0,'
        for i in range(0, 6):
            command += str(UcsTcp[i]) + ','
        for i in range(0, 6):
            command += str(TCP[i]) + ','
        for i in range(0, 6):
            command += str(UCS[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 7
    *	@param brief:点位加法计算
    *	@param pos1 : 空间坐标 1 
    *	@param pos2 : 空间坐标 2 
    *	@return nRet[1-6] : 计算结果
    '''
    def HRIF_PoseAdd(self, pos1, pos2):
        command = 'PoseAdd,0,'
        for i in range(0, 6):
            command += str(pos1[i]) + ','
        for i in range(0, 6):
            command += str(pos2[i]) + ','
        command += ';'
        return self.sendAndRecv(command)
		
    '''
    *	@index : 8
    *	@param brief:点位减法计算
    *	@param pos1 : 空间坐标 1 
    *	@param pos2 : 空间坐标 2 
    *	@return nRet[1-6] : 计算结果
    '''
    def HRIF_PoseSub(self, pos1, pos2):
        command = 'PoseSub,0,'
        for i in range(0, 6):
            command += str(pos1[i]) + ','
        for i in range(0, 6):
            command += str(pos2[i]) + ','
        command += ';'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 9
    *	@param brief:坐标变换,
        组合运算 HRIF_PoseTrans(p1,HRIF_PoseInverse(p2))，得到的就是基坐标系下的 p1,在用户坐标系 p2 下的位置
    *	@param pos1 : 空间坐标 1 
    *	@param pos2 : 空间坐标 2 
    *	@return nRet[1-6] : 计算结果
    '''
    def HRIF_PoseTrans(self, pos1, pos2):
        command = 'PoseTrans,0,'
        for i in range(0, 6):
            command += str(pos1[i]) + ','
        for i in range(0, 6):
            command += str(pos2[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 10
    *	@param brief:坐标逆变换
    *	@param pos1 : 空间坐标 1 
    *	@return nRet[1-6] : 计算结果
    '''
    def HRIF_PoseInverse(self, pos1):
        command = 'PoseInverse,0,'
        for i in range(0, 6):
            command += str(pos1[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 11
    *	@param brief:计算点位距离
    *	@param pos1 : 空间坐标 1 
    *	@param pos1 : 空间坐标 2 
    *	@return nRet[1] : 点位距离 
    *	@return nRet[2] : 姿态距离
    '''
    def HRIF_PoseDist(self, pos1, pos2):
        command = 'CalPointDistance,0,'
        for i in range(0, 6):
            command += str(pos1[i]) + ','
        for i in range(0, 6):
            command += str(pos2[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 12
    *	@param brief:空间位置直线插补计算
    *	@param pos1 : 空间坐标 1
    *	@param pos2 : 空间坐标 2
    *	@param alpha : 插补比例 
    *	@return nRet[1-6] : 计算坐标
    '''
    def HRIF_PoseInterpolate(self, pos1, pos2, alpha):
        command = 'PoseInterpolate,0,'
        for i in range(0, 6):
            command += str(pos1[i]) + ','
        for i in range(0, 6):
            command += str(pos2[i]) + ','
        command += str(alpha) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 13
    *	@param brief:空间位置直线插补计算
    *	@param pose1 : 坐标1(X-Z)
    *	@param pose2 : 坐标2(X-Z)
    *	@param pose3 : 坐标1(X-Z)
    *	@param pose4 : 坐标2(X-Z)
    *	@param pose5 : 坐标1(X-Z)
    *	@param pose6 : 坐标2(X-Z)
    *	@return nRet[1-6] : 计算坐标
    '''
    def HRIF_PoseDefdFrame(self, UCS, pos1, pos2, pos3, pos4, pos5, pos6):
        command = 'DefdFrame,0,'
        for i in range(0, 6):
            command += str(UCS[i]) + ','
        for i in range(0, 3):
            command += str(pos1[i]) + ','
        for i in range(0, 3):
            command += str(pos2[i]) + ','
        for i in range(0, 3):
            command += str(pos3[i]) + ','
        for i in range(0, 3):
            command += str(pos4[i]) + ','
        for i in range(0, 3):
            command += str(pos5[i]) + ','
        for i in range(0, 3):
            command += str(pos6[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    # pose_DefdFrame
    def Pose_DefdFrame(self, UCS, pos1, pos2, pos3, pos4, pos5, pos6):
        command = 'DefdFrame,0,'
        for i in range(0, 6):
            command += str(UCS[i]) + ','
        for i in range(0, 3):
            command += str(pos1[i]) + ','
        for i in range(0, 3):
            command += str(pos2[i]) + ','
        for i in range(0, 3):
            command += str(pos3[i]) + ','
        for i in range(0, 3):
            command += str(pos4[i]) + ','
        for i in range(0, 3):
            command += str(pos5[i]) + ','
        for i in range(0, 3):
            command += str(pos6[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    #
    # part 8 工具坐标与用户坐标读写指令
    #

    '''
    *	@index : 1
    *	@param brief:设置当前工具坐标-不写入配置文件，重启后失效
    *	@param TCP: 工具坐标(x,y,z,Rx,Ry,Rz)
    *	@return nRet[0] : 错误码
    '''
    def HRIF_SetTCP(self, TCP):
        command = 'SetCurTCP,0,'
        for i in range(0, 6):
            command += str(TCP[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 2
    *	@param brief:设置当前用户坐标-不写入配置文件，重启后失效
    *	@param UCS: 用户坐标(x,y,z,Rx,Ry,Rz)
    *	@return nRet[0] : 错误码
    '''
    def HRIF_SetUCS(self, UCS):
        command = 'SetCurUCS,0,'
        for i in range(0, 6):
            command += str(UCS[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 3
    *	@param brief:读取当前设置的工具坐标值
    *	@return nRet[1-6] : 工具坐标
    '''
    def HRIF_ReadCurTCP(self):
        command = 'ReadCurTCP,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief:读取当前设置的用户坐标值
    *	@return nRet[1-6] : 用户坐标
    '''
    def HRIF_ReadCurUCS(self):
        command = 'ReadCurUCS,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 5
    *	@param brief:通过名称设置工具坐标列表中的值为当前工具坐标，对应名称为示教器配置页面 TCP 示教的工具名称
    *	@param TcpName: 用户坐标名称
    '''
    def HRIF_SetTCPByName(self, TcpName):
        command = 'SetTCPByName,0,'
        command += str(TcpName) + ',;'
        return self.sendAndRecv(command)  

    '''
    *	@index : 6
    *	@param brief:通过名称设置用户坐标列表中的值为当前用户坐标，对应名称为示教器配置页面用户坐标示教的名称
    *	@param UcsName: 用户坐标名称
    '''
    def HRIF_SetUCSByName(self, UcsName):
        command = 'SetUCSByName,0,'
        command += str(UcsName) + ',;'
        return self.sendAndRecv(command)  

    '''
    *	@index : 7
    *	@param brief:通过名称读取指定 TCP 坐标，对应名称为示教器配置页面 TCP 示教的工具名称
    *	@param TCP: TCP坐标
    *	@return nRet[1-6] : 工具坐标
    '''
    def HRIF_ReadTCPByName(self, TCP):
        command = 'ReadTCPByName,0,'
        command += str(TCP) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 8
    *	@param brief:通过名称读取指定 UCS 坐标，对应名称为示教器配置页面用户坐标示教的用户坐标名称
    *	@param UCS: 用户坐标名称
    *	@return nRet[1-6] : 用户坐标
    '''
    def HRIF_ReadUCSByName(self, UCS):
        command = 'ReadUCSByName,0,'
        command += str(UCS) + ',;'
        return self.sendAndRecv(command)

    #
    # part 9 力控控制指令
    #

    '''
    *	@index : 1
    *	@param brief:设置力传感器状态
    *	@param state : 1(开启),0(关闭)
    '''
    def HRIF_SetForceControlState(self, state):
        command = 'SetForceControlState,0,' + str(state) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 2
    *	@param brief:读取探寻状态
    *	@param retData[1]:  0 未开启力控
                            1 力控探寻中
                            2 力控探寻完成,保持恒力
                            3 力控拖动开启状态
    '''
    def HRIF_ReadForceControlState(self):
        command = 'ReadFTControlState,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 3
    *	@param brief:设置力控坐标系方向为 tool 坐标方向模式
    *	@param mode :0 关闭
                     1 开启
    '''
    def HRIF_SetForceToolCoordinateMotion(self, mode):
        command = 'SetForceToolCoordinateMotion,0,'
        command += str(mode)
        command += ',;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 4
    *	@param brief:暂停力控运动，仅暂停力控功能，不暂停运动和脚本
    '''
    def HRIF_ForceControlInterrupt(self):
        command = 'GrpFCInterrupt,0,;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 5
    *	@param brief:继续力控运动，仅继续力控运动功能，不继续运动和脚本
    '''
    def HRIF_ForceControlContinue(self):
        command = 'GrpFCContinue,0,;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 6
    *	@param brief:力控清零，在原有数据的基础上重新标定力传感器
    '''
    def HRIF_SetForceZero(self):
        command = 'SetForceZero,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 7
    *	@param brief:设置力控探寻的最大速度
    *	@param MaxLinearVelocity : 直线速度
    *	@param MaxAngularVelocity : 姿态角速度
    '''
    def HRIF_SetMaxSearchVelocities(self, MaxLinearVelocity, MaxAngularVelocity):
        command = 'HRSetMaxSearchVelocities,0,'
        command += str(MaxLinearVelocity) + ','
        command += str(MaxAngularVelocity) + ','
        command += ';'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 8
    *	@param brief:设置力控探寻自由度(0关闭,1开启)
    *	@param X:x方向 
    *	@param Y:y方向
    *	@param Z:z方向
    *	@param Rx:Rx方向
    *	@param Ry:Ry方向
    *	@param Rz:Rz方向
    '''
    def HRIF_SetControlFreedom(self, freedom):
        command = 'HRSetControlFreedom,0,'
        for i in range(0, 6):
            command += str(freedom[i]) + ','
        command += ';'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 9
    *	@param brief:设置控制策略
    *	@param recvData[0]: 1:柔顺模式/0:恒力模式
    '''
    def HRIF_SetForceControlStrategy(self, strategy):
        command = 'HRSetForceControlStrategy,0,'
        command += str(strategy)
        command += ',;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 10
    *	@param brief:设置力传感器中心相对于法兰盘的安装位置和姿态
    *	@param position:X,Y,Z,Rx,Ry,Rz
    '''
    def HRIF_SetFreeDrivePositionAndOrientation(self, position):
        command = 'SetFTPosition,0,'
        for i in range(0, 6):
            command += str(position[i]) + ','
        command += ';'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 11
    *	@param brief:设置力控探寻 PID 参数
    *	@param fP: PID 参数 
    *	@param fI: PID 参数 
    *	@param fD: PID 参数 
    *	@param tP: PID 参数 
    *	@param tI: PID 参数 
    *	@param tD: PID 参数 
    '''
    def HRIF_SetPIDControlParams(self, fP, fI, fD, tP, tI, tD):
        command = 'HRSetPIDControlParams,0,'
        command += str(fP)
        command += ','
        command += str(fI)
        command += ','
        command += str(fD)
        command += ','
        command += str(tP)
        command += ','
        command += str(tI)
        command += ','
        command += str(tD)
        command += ',;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 12
    *	@param brief:设置惯量控制参数
    *	@param mass:  惯量控制参数
    '''
    def HRIF_SetMassParams(self, mass):
        command = 'HRSetMassParams,0,'
        for i in range(0, 6):
            command += str(mass[i]) + ','
        command += ';'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 13
    *	@param brief:设置阻尼控制参数
    *	@param damp:  阻尼控制参数
    '''
    def HRIF_SetDampParams(self, damp):
        command = 'HRSetDampParams,0,'
        for i in range(0, 6):
            command += str(damp[i]) + ','
        command += ';'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 14
    *	@param brief:设置刚度(k)控制参数
    *	@param stiff:  刚度控制参数
    '''
    def HRIF_SetStiffParams(self, stiff):
        command = 'HRSetStiffParams,0,'
        for i in range(0, 6):
            command += str(stiff[i]) + ','
        command += ';'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 15
    *	@param brief:设置力控目标力
    *	@param forcegoal:力控目标力
    '''
    def HRIF_SetForceControlGoal(self, forcegoal):
        command = 'HRSetControlGoal,0,'
        for i in range(0, 6):
            command += str(forcegoal[i]) + ','
        command += '0,0,0,0,0,0,;'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 16
    *	@param brief:设置力控目标力和目标距离(力控目标距离暂未启用)
    *	@param forcegoal:力控目标力
    *	@param distance:力控距离
    '''
    def HRIF_SetControlGoal(self, forcegoal, distance):
        command = 'HRSetControlGoal,0,'
        for i in range(0, 6):
            command += str(forcegoal[i]) + ','
        for i in range(0, 6):
            command += str(distance[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 17
    *	@param brief:设置力控限制范围-力传感器超过此范围后控制器断电
    *	@param max:力最大范围
    *	@param min:力最小范围
    '''
    def HRIF_SetForceDataLimit(self, max, min):
        command = 'HRSetForceDataLimit,0,'
        for i in range(0, 6):
            command += str(max[i]) + ','
        for i in range(0, 6):
            command += str(min[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 18
    *	@param brief:设置力控形变范围
    *	@param allowDistance:允许最大距离
    *	@param strengthLevel:位置与边界设置偏离距离的幂次项
    '''
    def HRIF_SetForceDistanceLimit(self, allowDistance, strengthLevel):
        command = 'HRSetForceDistanceLimit,0,'
        command += str(allowDistance) + ','
        command += str(strengthLevel) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 19
    *	@param brief:设置开启或者关闭力控自由驱动模式
    *	@param state :0(关闭),1(开启)
    '''
    def HRIF_SetForceFreeDriveMode(self, state):
        command = ''
        if state == 0:
            command = 'GrpCloseFreeDrive,0,;'
        else:
            command = 'GrpOpenFreeDrive,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 20
    *	@param brief:读取力控标定后数据
    *	@param recvData[1]:x方向力
    *	@param recvData[2]:y方向力
    *	@param recvData[3]:z方向力
    *	@param recvData[4]:Rx方向力
    *	@param recvData[5]:Ry方向力
    *	@param recvData[6]:Rz方向力
    '''
    def HRIF_ReadFTCabData(self):
        command = 'ReadFTCabData,0,;'
        recvData = self.sendAndRecv(command)
        return recvData

    '''
    *	@index : 21
    *	@param brief:读取力控原始数据
    *	@param recvData[1]:x方向力
    *	@param recvData[2]:y方向力
    *	@param recvData[3]:z方向力
    *	@param recvData[4]:Rx方向力
    *	@param recvData[5]:Ry方向力
    *	@param recvData[6]:Rz方向力
    '''
    def HRIF_ReadFTData(self):
        command = 'ReadForceData,0,;'
        recvData = self.sendAndRecv(command)
        return recvData

    '''
    *	@index : 22
    *	@param brief:开启关闭力传感器_脚本带配置
    *	@param state : 设置力传感器状态
    *	@param FTMode : 控制模式
                     0 : 恒力模式
                     1 : 柔顺模式
    *	@param UCS : Tool
    *	@param vel : vel[0]线速度
                     vel[1]角度速度
    *	@param forces : 目标探寻力x、y、z、Rx、Ry、Rz
    *	@param freedom : 力控探寻自由度X, Y, Z, Rx, Ry, Rz
    *	@param PID : fP, fI, fD, tP, tI, tD
    *	@param Mass : 惯量控制参数
    *	@param Damp : 阻尼控制参数
    *	@param Stiff : 刚度参数x、y、z、Rx、Ry、Rz
    '''
    def HRIF_SetScriptForceControlState(self, state, FTMode, UCS, vel, forces, freedom, PID, Mass, Damp, Stiff):
        command = 'SetScriptForceControlState,0,' + str(state) + ','
        command += str(FTMode) + ','
        command += str(UCS) + ','
        for i in range(0, 2):
            command += str(vel[i]) + ','
        for i in range(0, 6):
            command += str(forces[i]) + ','
        for i in range(0, 6):
            command += str(freedom[i]) + ','
        for i in range(0, 6):
            command += str(PID[i]) + ','
        for i in range(0, 6):
            command += str(Mass[i]) + ','
        for i in range(0, 6):
            command += str(Damp[i]) + ','
        for i in range(0, 6):
            command += str(Stiff[i]) + ','
        command += ';'
        retData = self.sendAndRecv(command)
        if retData[1] == 'OK':
            while True:
                command = 'ReadFTControlState,0,;'
                retData = self.sendAndRecv(command)
                if state == 1:
                    if int(retData[2]) == 2:
                        break
                elif state == 0:
                    if int(retData[2]) != 2:
                        time.sleep(0.2)
                        break
                time.sleep(0.2)
        return True

    #
    # part 10 通用运动类控制指令
    #

    '''
    *	@index : 1
    *	@param brief:关节短点动 运动距离 2°，最大速度<10°/s
    *	@param axisId: 关节轴 ID
    *	@param derection: 运动方向(0:负,1:正)
    '''
    def HRIF_ShortJogJ(self, axisId, derection):
        command = 'ShortJogJ,0,'
        command += str(axisId) + ','
        command += str(derection) + ','
        command += ';'
        return self.sendAndRecv(command)  

    '''
    *	@index : 2
    *	@param brief:空间坐标短点动 运动距离 2mm，最大速度<10mm/s
    *	@param pcsId: 坐标系轴 ID
    *	@param derection: 运动方向(0:负,1:正)
    '''
    def HRIF_ShortJogL(self, pcsId, derection):
        command = 'ShortJogL,0,'
        command += str(pcsId) + ','
        command += str(derection) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 3
    *	@param brief:关节长点动，最大运动速度<10°/s
    *	@param axisId: 关节轴 ID
    *	@param derection: 运动方向(0:负,1:正)
    *	@param state: 0:关闭,1:开启
    '''
    def HRIF_LongJogJ(self, axisId, derection, state):
        command = 'LongJogJ,0,'
        command += str(axisId) + ','
        command += str(derection) + ','
        command += str(state) + ','
        command += ';'
        return self.sendAndRecv(command) 

    '''
    *	@index : 4
    *	@param brief:空间长点动,最大运动速度<50mm/s
    *	@param pcsId: 坐标系轴 ID
    *	@param derection: 运动方向(0:负,1:正)
    *	@param state: 0:关闭,1:开启
    '''
    def HRIF_LongJogL(self, pcsId, derection, state):
        command = 'LongJogL,0,'
        command += str(pcsId) + ','
        command += str(derection) + ','
        command += str(state) + ','
        command += ';'
        return self.sendAndRecv(command) 

    ''' 
    *	@index : 5
    *	@param brief:长点动继续指令，当开始长点动之后，要按 500 毫秒或更短时间为时间周期发送一次该指令，否则长点动会停止
    '''
    def HRIF_LongMoveEvent(self):
        command = 'LongMoveEvent,0,;'
        return self.sendAndRecv(command)

    ''' 
    *	@index : 6
    *	@param brief:判断机器人是否处于运动状态
    *	@param retData[1]: 1:运动完成,0：运动未完成
    '''
    def HRIF_IsMotionDone(self):
        ret = self.HRIF_ReadRobotState()
        if ret[0] != '0':
            return ret
        retData = [ret[12] == "1" and ret[1] == "0"]
        return retData

    ''' 
    *	@index : 7
    *	@param brief:判断路点是否运动完成
    *	@param retData[1]: 1:运动完成,2：运动未完成
    '''
    def HRIF_IsBlendingDone(self):
        ret = self.HRIF_ReadRobotState()
        if ret[0] != '0':
            return ret
        retData = [ret[1],ret[13]]
        return retData

    '''
    *	@index : 8
    *	@param brief:执行路点运动(HRIF_WayPointEx 与 HRIF_WayPoint 区别在于 HRIF_WayPointEx 需要设置工具坐标与用户坐标具体的值，而HRIF_WayPoint 使用示教器示教的对应工具坐标与用户坐标名称)
    *	@param type : 运动类型(0:关节运动,1:空间运动)
    *	@param points : 空间目标位置
    *	@param RawACSpoints : 目标关节位置
    *	@param tcp : 工具坐标值
    *	@param ucs : 用户坐标值
    *	@param speed : 运动速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param acc : 运动加速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param radius : 是过渡半径,单位毫米
    *	@param isJoint : 是否使用关节角度作为目标点,如果type==0,则isJointt有起作用
    *	@param isSeek,bit,state:探寻参数,当ieek为1,则开启探寻,这时电箱的DO bit位为state时,就停止运动,否则运动到目标点再停止
    *	@param cmdID:当前路点ID,可以自定义,也可以按顺序设置为“1”,“2”,“3”
    '''
    def WayPointEx(self, type, points, RawACSpoints, tcp, ucs, speed, acc, radius,isJoint, isSeek, bit, state, cmdID):
        command = 'WayPointEx,0,'
        for i in range(0, 6):
            command += str(points[i]) + ','
        for i in range(0, 6):
            command += str(RawACSpoints[i]) + ','
        for i in range(0, 6): 
            command += str(ucs[i]) + ','
        for i in range(0, 6):
            command += str(tcp[i]) + ','
        command += str(speed) + ','
        command += str(acc) + ','
        command += str(radius) + ','
        command += str(type) + ','
        command += str(isJoint) + ','
        command += str(isSeek) + ','
        command += str(bit) + ','
        command += str(state) + ','
        command += str(cmdID) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 9
    *	@param brief:路点运动
    *	@param type : 运动类型(0:关节运动,1:直线运动)
    *	@param points : 目标迪卡尔位置
    *	@param RawACSpoints : 目标关节位置
    *	@param tcp : 工具坐标名称
    *	@param ucs : 用户坐标名称
    *	@param speed : 运动速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param Acc : 运动加速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param radius : 是过渡半径,单位毫米
    *	@param isJoint : 是否使用关节角度作为目标点,如果type==0,则isJoint有起作用
    *	@param isSeek,bit,state:探寻参数,当isSeek为1,则开启探寻,这时电箱的DO bit位为state时,就停止运动,否则运动到目标点再停止
    *	@param cmdID:当前路点ID,可以自定义,也可以按顺序设置为“1”,“2”,“3”
    '''
    def HRIF_WayPoint(self, type, points, RawACSpoints, tcp, ucs, speed, Acc, radius,isJoint, isSeek, bit, state, cmdID):
        command = 'WayPoint,0,'
        for i in range(0, 6):
            command += str(points[i]) + ','
        for i in range(0, 6):
            command += str(RawACSpoints[i]) + ','
        command += str(tcp) + ','
        command += str(ucs) + ','
        command += str(speed) + ','
        command += str(Acc) + ','
        command += str(radius) + ','
        command += str(type) + ','
        command += str(isJoint) + ','
        command += str(isSeek) + ','
        command += str(bit) + ','
        command += str(state) + ','
        command += str(cmdID) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 10
    *	@param brief:路点运动(HRIF_WayPoint2 新增直线与圆弧过渡不减速功能，HRIF_WayPoint 只有直线与直线之间有过渡)
    *	@param type : 运动类型(0:关节运动,1:直线运动,2:圆弧运动)
    *	@param EndPos : 空间目标位置(type=0 并 isJoint=1:无效)
                        (type=0 并 isJoint=0:用此空间坐标作为目标位置,通过逆解计算得到关节坐标为目标关节坐标)
    *	@param AuxPos : 空间目标位置(type=0或1时无效,type=2时做为圆弧的经过位置)
    *	@param AcsPos : 空间目标位置(type=0 并 isJoint=1:使用此关节坐标作为目标关节坐标)
                        (type=0 并 isJoint=0:此关节坐标仅作为计算逆解时选解的参考关节坐标)
                        (type=1 或 2 :无效)

    *	@param Tcp : 工具坐标名称
    *	@param Ucs : 用户坐标名称
    *	@param Vel : 运动速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param Acc : 运动加速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param Radius : 是过渡半径,单位毫米
    *	@param isJoint : 是否使用关节角度作为目标点,如果type==0,则isJoint有起作用
    *	@param isSeek,bit,state:探寻参数,当isSeek为1,则开启探寻,这时电箱的DO bit位为state时,就停止运动,否则运动到目标点再停止
    *	@param cmdID:当前路点ID,可以自定义,也可以按顺序设置为“1”,“2”,“3”
    '''
    def HRIF_WayPoint2(self, EndPos, AuxPos, AcsPos, Tcp, Ucs, Vel, Acc, Radius, type, isJoint, isSeek, bit, state, cmdID):
        command = 'WayPoint2,0,'
        for i in range(0, 6):
            command += str(EndPos[i]) + ','
        for i in range(0, 6):
            command += str(AuxPos[i]) + ','
        for i in range(0, 6):
            command += str(AcsPos[i]) + ','
        command += Tcp + ','
        command += Ucs + ','
        command += str(Vel) + ','
        command += str(Acc) + ','
        command += str(Radius) + ','
        command += str(type) + ','
        command += str(isJoint) + ','
        command += str(isSeek) + ','
        command += str(bit) + ','
        command += str(state) + ','
        command += cmdID + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 11
    *	@param brief:机器人运动到指定的角度坐标位置
    *	@param points : 目标迪卡尔位置
    *	@param RawACSpoints : 目标关节位置
    *	@param tcp : 工具坐标名称
    *	@param ucs : 用户坐标名称
    *	@param speed : 运动速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param Acc : 运动加速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param radius : 是过渡半径,单位毫米
    *	@param isJoint : 是否使用关节角度作为目标点,如果type==0,则isJoint有起作用
    *	@param isSeek,bit,state:探寻参数,当isSeek为1,则开启探寻,这时电箱的DO bit位为state时,就停止运动,否则运动到目标点再停止
    *	@param cmdID:当前路点ID,可以自定义,也可以按顺序设置为“1”,“2”,“3”
    '''
    def HRIF_MoveJ(self, points, RawACSpoints, tcp, ucs, speed, Acc, radius,isJoint, isSeek, bit, state, cmdID):
        command = 'WayPoint,0,'
        for i in range(0, 6):
            command += str(points[i]) + ','
        for i in range(0, 6):
            command += str(RawACSpoints[i]) + ','
        command += str(tcp) + ','
        command += str(ucs) + ','
        command += str(speed) + ','
        command += str(Acc) + ','
        command += str(radius) + ','
        command += '0,'
        command += str(isJoint) + ','
        command += str(isSeek) + ','
        command += str(bit) + ','
        command += str(state) + ','
        command += str(cmdID) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 12
    *	@param brief:机器人直线运动到指定的空间坐标位置
    *	@param points : 目标迪卡尔位置
    *	@param RawACSpoints : 目标关节位置
    *	@param tcp : 工具坐标名称
    *	@param ucs : 用户坐标名称
    *	@param speed : 运动速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param Acc : 运动加速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param radius : 是过渡半径,单位毫米
    *	@param isSeek,bit,state:探寻参数,当isSeek为1,则开启探寻,这时电箱的DO bit位为state时,就停止运动,否则运动到目标点再停止
    *	@param cmdID:当前路点ID,可以自定义,也可以按顺序设置为“1”,“2”,“3”
    '''
    def HRIF_MoveL(self, points, RawACSpoints, tcp, ucs, speed, Acc, radius, isSeek, bit, state, cmdID):
        command = 'WayPoint,0,'
        for i in range(0, 6):
            command += str(points[i]) + ','
        for i in range(0, 6):
            command += str(RawACSpoints[i]) + ','
        command += str(tcp) + ','
        command += str(ucs) + ','
        command += str(speed) + ','
        command += str(Acc) + ','
        command += str(radius) + ','
        command += '1,'
        command += '0,'
        command += str(isSeek) + ','
        command += str(bit) + ','
        command += str(state) + ','
        command += str(cmdID) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 13
    *	@param brief:圆弧轨迹运动
    *	@param StartPoint : 圆弧开始位置
    *	@param AuxPoint : 圆弧经过位置
    *	@param EndPoint : 圆弧结束位置
    *	@param fixedPosure : 0:不使用固定姿态,1:使用固定姿态
    *	@param nMoveCType : 0:圆弧运动,1:整圆运动
    *	@param nRadLen : 当nMoveCType=0时该参数无效,由三个点确定圆弧轨迹
                         当nMoveCType=1时,该参数为整圆的圈数
    *	@param speed : 运动速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param Acc : 运动加速度,速度单位是毫米每秒,度每秒,加速度毫米每秒平方,度每秒平方
    *	@param radius : 是过渡半径,单位毫米
    *	@param tcp : 目标所在的工具坐标名称
    *	@param ucs : 目标所在的用户坐标名称
    *	@param cmdID:当前路点ID,可以自定义,也可以按顺序设置为“1”,“2”,“3”
    '''
    def HRIF_MoveC(self, StartPoint, AuxPoint, EndPoint, fixedPosure, nMoveCType, nRadLen,speed, Acc, radius, tcp, ucs, cmdID):
        command = 'MoveC,0,'
        for i in range(0, 6):
            command += str(StartPoint[i]) + ','
        for i in range(0, 6):
            command += str(AuxPoint[i]) + ','
        for i in range(0, 6):
            command += str(EndPoint[i]) + ','
        command += str(fixedPosure) + ','
        command += str(nMoveCType) + ','
        command += str(nRadLen) + ','
        command += str(speed) + ','
        command += str(Acc) + ','
        command += str(radius) + ','
        command += str(tcp) + ','
        command += str(ucs) + ','
        command += str(cmdID) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 14
    *	@brief: Z型轨迹运动
    *	@param StartPoint : 开始位置
    *	@param EndPoint : 结束位置
    *	@param PlanePoint : 确定平面点位置
    *	@param Speed : 速度
    *	@param Acc : 加速度
    *	@param WIdth : 宽度
    *	@param Density : 密度
    *	@param EnableDensity : 是否使用密度(0:不使用,1:使用)
    *	@param EnablePlane : 是否使用平面点(0:不使用,1:使用)
    *	@param EnableWaiTime : 是否开启转折点等待时间(0:不使用,1:使用)
    *	@param PosiTime : 正向转折点等待时间ms
    *	@param NegaTime : 负向转折点等待时间ms
    *	@param Radius : 过渡半径
    *	@param tcp : 工具坐标名称
    *	@param ucs : 用户坐标名称
    *	@param cmdID : 命令ID
    '''
    def HRIF_MoveZ(self, StartPoint, EndPoint, PlanePoint, Speed, Acc, WIdth, Density, EnableDensity, EnablePlane, EnableWaiTime, PosiTime, NegaTime, Radius, tcp, ucs, cmdID):
        command = 'MoveZ,0,'
        for i in range(0, 6):
            command += str(StartPoint[i]) + ','
        for i in range(0, 6):
            command += str(EndPoint[i]) + ','
        for i in range(0, 6):
            command += str(PlanePoint[i]) + ','
        command += str(Speed) + ','
        command += str(Acc) + ','
        command += str(WIdth) + ','
        command += str(Density) + ','
        command += str(EnableDensity) + ','
        command += str(EnablePlane) + ','
        command += str(EnableWaiTime) + ','
        command += str(PosiTime) + ','
        command += str(NegaTime) + ','
        command += str(Radius) + ','
        command += str(tcp) + ','
        command += str(ucs) + ','
        command += str(cmdID) + ','
        command += ';'
        return self.sendAndRecv(command)
    
    #
    # part 11 连续轨迹运动类控制指令
    #

    '''
    *	@index : 1
    *	@param brief:初始化关节连续轨迹运动
    *	@param trackName : 轨迹名称
    *	@param speedRatio : 运动速度
    *	@param radius : 过渡半径
    '''
    def HRIF_StartPushMovePathJ(self, trackName, speedRatio, radius):
        command = 'StartPushMovePath,0,'
        command += trackName + ','
        command += str(speedRatio) + ','
        command += str(radius) + ','
        command += ';'
        print(command)
        return self.sendAndRecv(command)
    
    '''
    *	@index : 2
    *	@param brief:下发轨迹点位
    *	@param trackName : 轨迹名称
    *	@param paramsJ : 关节点位(6)
    '''
    def HRIF_PushMovePathJ(self, trackName, paramsJ):
        command = 'PushMovePathJ,0,'
        command += trackName
        command += ','
        for i in range(0, 6):
            command += str(paramsJ[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 3
    *	@param brief:轨迹下发完成,开始计算轨迹
			调用pushMovePathJ,一般情况下点位数量需要>4
    *	@param trackName : 轨迹名称
    '''
    def HRIF_EndPushMovePathJ(self, trackName):
        command = 'EndPushMovePath,0,'
        command += trackName + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief:执行轨迹运动
    *	@param trackName : 轨迹名称
    '''
    def HRIF_MovePathJ(self, trajectName):
        command = 'MovePath,0,'
        command += str(trajectName) + ','
        command += ';'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 5
    *	@param brief:读取当前的轨迹状态
    *	@param trackName : 轨迹名称
    *	@param retData[1] :  
                    0 : 轨迹未示教
                    1 : 轨迹示教中
                    2 : 轨迹计算中
                    3 : 轨迹完成计算
                    4 : 轨迹完成示教
                    5 : 轨迹计算错误
    '''
    def HRIF_ReadMovePathJState(self, trackName):
        command = 'ReadMovePathState,0,'
        command += trackName + ','
        command += ';'
        retData = self.sendAndRecv(command)
        return retData

    '''
    *	@index : 6
    *	@param brief:修改轨迹名称
    *	@param trackName : 轨迹名称
    *	@param newName : 新轨迹名称
    '''
    def HRIF_UpdateMovePathJName(self, trackName, newName):
        command = 'UpdateMovePathName,0,'
        command += trackName + ','
        command += newName + ','
        command += ';'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 7
    *	@param brief:删除指定轨迹
    *	@param trackName : 轨迹名称
    '''
    def HRIF_DelMovePathJ(self, trackName):
        command = 'DelMovePath,0,'
        command += trackName + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 8
    *	@param brief:读取当前的轨迹运动进度(此接口仅对MovePathL有效，对MovePathJ无效)
    *   @param retData[1] : 0:未完成轨迹
                            1:已完成轨迹
    *   @param retData[2] : 当前运动到的点位数量
    '''
    def HRIF_ReadTrackProcess(self):
        command = 'ReadSoftMotionProgress,0,;'
        return self.sendAndRecv(command)

    '''
    *	@index : 9
    *	@param brief:初始化空间轨迹运动
    *	@param trackName : 轨迹名称
    *	@param vel : 运动速度
    *	@param acc : 运动加速度
    *	@param jerk : 运动加加速度
    *	@param ucs : 指定轨迹所在的用户坐标系名称
    *	@param tcp : 指定轨迹所在的工具坐标值名称
    '''
    def HRIF_InitMovePathL(self, trackName, vel, acc, jerk, ucs, tcp):
        command = 'InitMovePathL,0,'
        command += trackName + ','
        command += str(vel) + ','
        command += str(acc) + ','
        command += str(jerk) + ','
        command += ucs + ','
        command += tcp + ','
        command += ';'
        print(command)
        return self.sendAndRecv(command)

    '''
    *	@index : 10
    *	@param brief:下发轨迹点位
    *	@param trackName : 轨迹名称
    *	@param pcspos : 空间点位
    '''
    def HRIF_PushMovePathL(self, trackName, pcspos):
        command = 'PushMovePathL,0,'
        command += trackName + ','
        for i in range(0, 6):
            command += str(pcspos[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 11
    *	@param brief:批量下发轨迹点位，调用一次可下发多个点位数据
    *	@param trackName : 轨迹名称
    *	@param moveType : 运动类型-MovePathJ可以共用 0(MovePathJ)/1(MovePathL)
    *	@param pointsSize : 轨迹点位数量
    *	@param points : 轨迹点位
    '''
    def HRIF_PushMovePaths(self, trackName, moveType, pointsSize, points):
        command = 'PushMovePaths,0,'
        command += trackName
        command += ','
        command += str(moveType)
        command += ','
        command += str(pointsSize)
        command += ','
        for pos in points:
            command += str(pos) + ','
        command += ';'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 12
    *	@param brief:执行空间坐标轨迹运动
    *	@param trackName : 轨迹名称
    '''
    def HRIF_EndPushPath(self, trackName):
        command = 'EndPushMovePath,0,'
        command += trackName
        command += ',;'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 12
    *	@param brief:执行空间坐标轨迹运动
    *	@param trackName : 轨迹名称
    '''
    def HRIF_MovePathL(self, trackName):
        command = 'MovePathL,0,'
        command += trackName
        command += ',;'
        return self.sendAndRecv(command)

    #
    # part 12 Servo 运动类控制指令
    #

    '''
    *	@index : 1
    *	@param brief:启动机器人在线控制(servoJ 或 servoP)时,设定位置固定更新的周期和前瞻时间
    *	@param servoTime : 固定更新的周期 s
    *	@param lookaheadTime : 前瞻时间 s
    '''
    def HRIF_StartServo(self, servoTime, lookaheadTime):
        command = 'StartServo,0,'
        command += str(servoTime) + ',' + str(lookaheadTime) + ',;'
        return self.sendAndRecv(command)

    '''
    *	@index : 2
    *	@param brief:在线关节位置命令控制，以 StartServo 设定的固定更新时间发送关节位置，机器人将实时的跟踪关节位置指令
    *	@param pose : 关节点位
    '''
    def HRIF_PushServoJ(self, pose):
        command = 'PushServoJ,0,'
        for i in range(0, 6):
            command += str(pose[i]) + ','
        command += ';'
        return self.sendAndRecv(command)
    
    '''
    *	@index : 3
    *	@param brief:在线末端TCP位置命令控制,以 StartServo 设定的固定更新时间发送 TCP 位置，机器人将实时的跟踪目标 TCP 位置逆运算转换后的关节位置指令
    *	@param pose : 更新的目标迪卡尔坐标位置
    *	@param ucs : 目标位置对应的UCS
    *	@param tcp : 目标位置对应的TCP
    '''
    def HRIF_PushServoP(self, pose, ucs, tcp):
        command = 'PushServoP,0,'
        for i in range(0, 6):
            command += str(pose[i]) + ','
        for i in range(0, 6):
            command += str(ucs[i]) + ','
        for i in range(0, 6):
            command += str(tcp[i]) + ','
        command += ';'
        return self.sendAndRecv(command)
    
    #
    # part 13 相对跟踪运动类控制指令
    #

    '''
    *	@index : 1
    *	@param brief:启动机器人在线控制(servoJ 或 servoP)时,设定位置固定更新的周期和前瞻时间
    *	@param state : 跟踪状态(0:关闭相对跟踪运动 1:开启相对跟踪运动)
    *	@param distance : 相对跟踪运动保持的相对距离
    *	@param vel : 相对跟踪的运动的探寻速度
    '''
    def HRIF_SetMoveTraceParams(self, state, distance, vel1, vel2):
        command = 'SetMoveTraceParams,0,'
        command += str(state) + ','
        command += str(distance) + ','
        command += str(vel1) + ','
        command += str(vel2) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 2
    *	@param brief:设置相对跟踪运动初始化参数
    *	@param dK,dB: 计算公式y = dK * x + dB
    *	@param maxLimit: 激光传感器检测距离最大值
    *	@param minLinit: 激光传感器检测距离最小值
    '''
    def HRIF_SetMoveTraceInitParams(self, dK, dB, maxLimit, minLinit):
        command = 'SetMoveTraceInitParams,0,'
        command += str(dK) + ','
        command += str(dB) + ','
        command += str(maxLimit) + ','
        command += str(minLinit) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 3
    *	@param brief:设置相对跟踪运动的跟踪探寻方向
    *	@param direction: 跟踪探寻方向(x,y,z无效,可设置0)(Rx,Ry,Rz单位[°])
    '''
    def HRIF_SetMoveTraceUcs(self,x,y,z,Rx,Ry,Rz):
        command = 'SetMoveTraceUcs,0,'
        command += str(x) + ','
        command += str(y) + ','
        command += str(z) + ','
        command += str(Rx) + ','
        command += str(Ry) + ','
        command += str(Rz) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 4
    *	@param brief: 设置传送带跟踪运动状态
    *	@param state: 0:关闭 1:开启
    '''
    def HRIF_SetTrackingState(self, state):
        command = 'SetTrackingState,0,' + str(state) + ',;'
        return self.sendAndRecv(command)
    
    # '''
    # *	@index : 
    # *	@param brief:传送带类型
    # *	@param type : 0:直线 1:圆弧
    # '''
    # def setConveyorType(self, type):
    #     command = 'SetConveyorType,0,'
    #     command += str(type) + ','
    #     command += ';'
    #     return self.sendAndRecv(command)
    
    # '''
    # *	@index : 
    # *	@param brief:传送带方向
    # *	@param direction : 0:负方向 1:正方向
    # '''
    # def setConveyorDirection(self, direction):
    #     command = 'SetConveyorDirection,0,'
    #     command += str(direction) + ','
    #     command += ';'
    #     return self.sendAndRecv(command)
    
    # '''
    # *	@index : 
    # *	@param brief:设置传送带转换比率
    # *	@param mm : 
    # *	@param count : 
    # '''
    # def setConveyorScale(self, mm, count):
    #     command = 'SetConveyorScale,0,'
    #     command += str(mm) + ','
    #     command += str(count) + ','
    #     command += ';'
    #     return self.sendAndRecv(command)
    
    # '''
    # *	@index : 
    # *	@param brief:设定传送带速度
    # *	@param state : 0:关闭模拟速度 1:开启模拟速度
    # *	@param vel : 速度 mm/s
    # '''
    # def setConveyorVel(self, state, vel):
    #     command = 'SetConveyorVel,0,'
    #     command += str(state) + ','
    #     command += str(vel) + ','
    #     command += ';'
    #     return self.sendAndRecv(command)

    # '''
    # *	@index : 
    # *	@param brief:标定传送带
    # *	@param pos1 : 标定坐标1
    # *	@param encoder1 : coder_1
    # *	@param pos2 : 标定坐标2
    # *	@param encoder2 : coder_2
    # '''
    # def setCalibrationConveyor(self, pos1, encoder1, pos2, encoder2):
    #     command = 'SetCalibrationConveyor,0,'
    #     command += str(encoder1) + ','
    #     command += str(encoder2) + ','
    #     for i in range(0, 6):
    #         command += str(pos1[i]) + ','
    #     for i in range(0, 6):
    #         command += str(pos2[i]) + ','
    #     command += ';'
    #     return self.sendAndRecv(command)
    
    # '''
    # *	@index : 
    # *	@param brief:读取传送带类型
    # *	@param ret : 0:直线 1:圆弧
    # '''
    # def readConveyorType(self):
    #     command = 'ReadConveyorType,0,;'
    #     retData = self.sendAndRecv(command)
    #     return retData
    
    # '''
    # *	@index : 
    # *	@param brief:读取传送带方向
    # *	@param type : 0:负方向 1:正方向
    # '''
    # def readConveyorDirection(self):
    #     command = 'ReadConveyorDirection,0,;'
    #     retData = self.sendAndRecv(command)
    #     return retData
    
    # '''
    # *	@index : 
    # *	@param brief:读取传送带转换比率
    # *	@param state : 
    # *	@param vel : 
    # '''
    # def readConveyorScale(self):
    #     command = 'ReadConveyorScale,0,;'
    #     retData = self.sendAndRecv(command)
    #     return retData
    
    # '''
    # *	@index : 
    # *	@param brief:读取传送带速度
    # *	@param retData[2] : 0:关闭模拟速度 1:打开模拟速度
    # *	@param retData[3] : 传送带速度 mm/s
    # '''
    # def readConveyorVel(self, state, vel):
    #     command = 'ReadConveyorVel,0,;'
    #     retData = self.sendAndRecv(command)
    #     return retData

    #
    # part 14 其他指令
    #

    '''
    *	@index : 1
    *	@param brief:执行插件 app 命令
    *	@param name :插件名称
    *	@param param:插件指令及参数
    '''
    def HRApp(self,name,param):
        command = 'HRAppCmd,'
        command += str(name) + ','
        command += str(param) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 2
    *	@param brief:写末端连接的 modbus 从站寄存器
    *	@param nSlaveID : 从站ID
    *	@param nFunction : 功能码
    *	@param nRegAddr : 寄存器地址
    *	@param nRegCount : 寄存器数量
    *	@param data : 寄存器数据
    '''
    def HRIF_WriteEndHoldingRegisters(self, nSlaveID, nFunction, nRegAddr, nRegCount, data):
        command = 'WriteHoldingRegisters,0,'
        command += str(nSlaveID) + ','
        command += str(nFunction) + ','
        command += str(nRegAddr) + ','
        command += str(nRegCount) + ','
        if nRegCount != len(data):
            return ['-1']
        for i in nRegCount:
            command += str(data[i]) + ','
        command += ';'
        return self.sendAndRecv(command)

    '''
    *	@index : 
    *	@param brief:读取末端Modbus寄存器
    *	@param nSlaveID : 从站ID
    *	@param nFunction : 功能码(0x01-读线圈寄存器
                                0x02-读线离散输入寄存器
                                0x03-读保持寄存器
                                0x04-读输入寄存器
                                0x05-写单个线圈寄存器
                                0x06-写单个保持寄存器
                                0x0f-写多个线圈寄存器
                                0x10-写多个保持寄存器)
    *	@param nRegAddr : 寄存器地址
    *	@param nRegCount : 寄存器数量
    *	@param retData[1-n] : 寄存器数据 
    '''
    def HRIF_ReadEndHoldingRegisters(self, nSlaveID, nFunction, nRegAddr, nRegCount):
        command = 'ReadHoldingRegisters,0,'
        command += str(nSlaveID) + ','
        command += str(nFunction) + ','
        command += str(nRegAddr) + ','
        command += str(nRegCount) + ',;'
        retData = self.sendAndRecv(command)
        return retData
    
    # # modbus 
    # def setModbus(self,deviceName,varName,value):
    #     command = 'SetExDeviceData,' + deviceName + ',' + varName + ',' + str(value) + ',;'
    #     return self.sendAndRecv(command)

    # def getModbus(self,deviceName,varName):
    #     command = 'ReadExDeviceData,' + deviceName + ',' + varName + ',;'
    #     retData = self.sendAndRecv(command)
    #     #time.sleep(self.readSleep)
    #     return int(retData[2])

    # '''
    # *	@index : 
    # *	@param brief:通过名称修改TCP
    # *	@param name: TCP名称
    # *	@param TCP: TCP坐标参数X,Y,Z,RX,RY,RZ
    # '''
    # def ConfigTCP(self,name,TCP):
    #     command = 'ConfigTCP,'
    #     command += str(name)
    #     command += ','
    #     for i in range(0, 6):
    #         command += str(TCP[i]) + ','
    #     command += ';'
    #     return self.sendAndRecv(command)  

    

    # '''
    # *	@index : 
    # *	@param brief:通过名称修改用户坐标系
    # *	@param name: 用户坐标名称
    # *	@param UCS: 用户坐标系参数X,Y,Z,RX,RY,RZ
    # '''
    # def ConfigUCS(self,name,UCS):
    #     command = 'ConfigUCS,'
    #     command += str(name)
    #     command += ','
    #     for i in range(0, 6):
    #         command += str(UCS[i]) + ','
    #     command += ';'
    #     return self.sendAndRecv(command)
    
    '''
    *	@index : 
    *	@param brief:等待机器人运动停止
    '''
    def waitMovementDone(self):
        while True:
            command = 'ReadCurFSM,0,;'
            retData = self.sendAndRecv(command)
            if int(retData[1]) == 25:
                time.sleep(0.1)
                continue
            else:
                break
        return 0
    
    

    '''
    *	@index : 
    *	@param brief:执行路点运动
    *	@param type : 运动类型
                        0:MoveJ
                        1:MoveL
                        2:MoveC
    '''
    def WayPointRel(self, type, usePointList, Point_PCS, Point_ACS, relMoveType, nAxisMask, Axis0,Axis1,Axis2,Axis3,Axis4,Axis5, tcp, ucs, speed, Acc, radius,isJoint, isSeek, bit, state, cmdID):
        command = 'WayPointRel,0,'
        command += str(type) + ','
        command += str(usePointList) + ','
        for i in range(0, 6):
            command += str(Point_PCS[i]) + ','
        for i in range(0, 6):
            command += str(Point_ACS[i]) + ','
        command += str(relMoveType) + ','
        for i in range(0, 6):
            command += str(nAxisMask[i]) + ','
        command += str(Axis0) + ','
        command += str(Axis1) + ','
        command += str(Axis2) + ','
        command += str(Axis3) + ','
        command += str(Axis4) + ','
        command += str(Axis5) + ','
        command += str(tcp) + ','
        command += str(ucs) + ','
        command += str(speed) + ','
        command += str(Acc) + ','
        command += str(radius) + ','
        command += str(isJoint) + ','
        command += str(isSeek) + ','
        command += str(bit) + ','
        command += str(state) + ','
        command += str(cmdID) + ','
        command += ';'
        return self.sendAndRecv(command)
        
    def CheckTemperatureUnderLow(self):
        return self.sendAndRecv('CheckTemperatureUnderLow,;')

    '''
    *	@index : 
    *	@param brief:读取点位信息
    *	@param retData[2-7] : 关节坐标
    *	@param retData[8-13] : 迪卡尔坐标
    *	@param retData[14-19] : TCP坐标
    *	@param retData[20-25] : 用户坐标
    '''
    def ReadPointList(self,point_name):
        command = 'ReadPointList,'+ str(point_name) + ',;'
        return self.sendAndRecv(command)

    # sendCmdID
    # No output 
    def sendCmdID(self, CmdID,ThreadID):
        self.rpcClient.SetCurCmdID(str(CmdID),str(ThreadID))
        #command = 'SendCmdID,0,' + str(CmdID) + ',' + str(ThreadID)  + ',;'
        # retData = self.sendAndRecv(command)
        # return retData
    
    # send the finish code 
    # if py has running finish 
    # py should send a finish message to CC
    # No output 
    def sendScriptFinish(self,errorcode):
        command = 'SendScriptFinish,0,'+ str(errorcode) + ',;'
        self.tcp.send(command.encode())
        self.tcp.recv(self.clientPort).decode("utf-8","ignore")
        
    def sendScriptError(self,msg):
        self.rpcClient.SendScriptError(str(msg),str(""))
    
    #
    def sendHRLog(self,nLevel,msg):
        self.rpcClient.HRLog(int(nLevel),str(msg))

    # sendVarValue
    # No output 
    def sendVarValue(self, VarName, Value):
        if isinstance(Value,list):
            ValueStr='['
            for i in range(0, 6):
                ValueStr += str(Value[i])
                if i!=5:
                    ValueStr += ','
            ValueStr += ']'
            #command = 'SendVarValue,0,' + str(VarName) + ','
            #for i in range(0, 6):
            #    command += str(Value[i]) + ','
            #command += ';'
        else:
            ValueStr=str(Value)
        #gVar = globals()
        #gVar[VarName]=Value
        self.rpcClient.SendVarValue(str(VarName),ValueStr)
        # return retData  
    
    def cdsSetIO(self, nEndDOMask,nEndDOVal,nBoxDOMask,nBoxDOVal,nBoxCOMask,nBoxCOVal,nBoxAOCH0_Mask,nBoxAOCH0_Mode,nBoxAOCH1_Mask,nBoxAOCH1_Mode,dbBoxAOCH0_Val,dbBoxAOCH1_Val):
        command = 'cdsSetIO,'
        command += str(nEndDOMask) + ','
        command += str(nEndDOVal) + ','
        command += str(nBoxDOMask) + ','
        command += str(nBoxDOVal) + ','
        command += str(nBoxCOMask) + ','
        command += str(nBoxCOVal) + ','
        command += str(nBoxAOCH0_Mask) + ','
        command += str(nBoxAOCH0_Mode) + ','
        command += str(nBoxAOCH1_Mask) + ','
        command += str(nBoxAOCH1_Mode) + ','
        command += str(dbBoxAOCH0_Val) + ','
        command += str(dbBoxAOCH1_Val) + ','
        command += ';'
        return self.sendAndRecv(command)


    ###################################################################################################
    def MBSlave_ReadCoils(self,addr,nb):
        #time.sleep(self.readSleep)
        return MBMaster.Modbus_Master.execute(1, cst.READ_COILS, addr, nb)

    def MBSlave_ReadInputCoils(self,addr,nb):
        #time.sleep(self.readSleep)
        return MBMaster.Modbus_Master.execute(1, cst.READ_DISCRETE_INPUTS, addr, nb)

    def MBSlave_ReadHoldingRegisters(self,addr,nb):
        #time.sleep(self.readSleep)
        return MBMaster.Modbus_Master.execute(1, cst.READ_HOLDING_REGISTERS, addr, nb)

    def MBSlave_ReadInputRegisters(self,addr,nb):
        #time.sleep(self.readSleep)
        return MBMaster.Modbus_Master.execute(1, cst.READ_INPUT_REGISTERS, addr, nb)
    ###################################################################################################
    def MBSlave_WriteCoils(self,addr,val):
        return MBMaster.Modbus_Master.execute(1, cst.WRITE_MULTIPLE_COILS, addr, output_value=val)

    def MBSlave_WriteCoil(self,addr,val):
        return MBMaster.Modbus_Master.execute(1, cst.WRITE_SINGLE_COIL, addr, output_value=val)
    ###################################################################################################
    def MBSlave_WriteHoldingRegisters(self,addr,val):
        return MBMaster.Modbus_Master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, addr, output_value=val)

    def MBSlave_WriteHoldingRegister(self,addr,val):
        return MBMaster.Modbus_Master.execute(1, cst.WRITE_SINGLE_REGISTER, addr, output_value=val)
    ###################################################################################################
    def MBSlave_WriteHoldingRegisters_Float(self,addr,val):
        valsend=[]
        for item in val:
         valsend.extend(WriteFloat(item))
        return self.MBSlave_WriteHoldingRegisters(addr,valsend)

    def MBSlave_ReadHoldingRegisters_Float(self,addr,nb):
        #time.sleep(self.readSleep)
        valsend=[]
        for item in range(0,nb):
         nval=ReadFloat(self.MBSlave_ReadHoldingRegisters(item*2+addr,2))
         # print(nval)
         valsend.append(nval)
        return valsend
    ###################################################################################################
    def MBSlave_WriteHoldingRegisters_Int(self,addr,val):
        valsend=[]
        for item in val:
         valsend.extend(WriteDint(item))
        return self.MBSlave_WriteHoldingRegisters(addr,valsend)

    def MBSlave_ReadHoldingRegisters_Int(self,addr,nb):
        #time.sleep(self.readSleep)
        valsend=[]
        for item in range(0,nb):
         nval=ReadDint(self.MBSlave_ReadHoldingRegisters(item*2+addr,2))
         # print(nval)
         valsend.append(nval)
        return valsend
    ###################################################################################################
    def MBSlave_ReadInputRegisters_Float(self,addr,nb):
        #time.sleep(self.readSleep)
        valsend=[]
        for item in range(0,nb):
         nval=ReadFloat(self.MBSlave_ReadInputRegisters(item*2+addr,2))
         # print(nval)
         valsend.append(nval)
        return valsend

    def MBSlave_ReadInputRegisters_Int(self,addr,nb):
        #time.sleep(self.readSleep)
        valsend=[]
        for item in range(0,nb):
         nval=ReadDint(self.MBSlave_ReadInputRegisters(item*2+addr,2))
         # print(nval)
         valsend.append(nval)
        return valsend
    ###################################################################################################
    def sendAndRecv(self, cmd):
        #print(cmd)
        self.tcp.send(cmd.encode())
        # print cmd
        ret = self.tcp.recv(self.clientPort).decode("utf-8","ignore")
        retData = ret.split(',')
        #print(retData)
        logmsg='[script]sendAndRecv:'+cmd
        if len(retData) < 3:
            logmsg=logmsg+' exit with ServerReturnError'
            self.sendHRLog(2,logmsg)
            #self.sendScriptFinish(ScriptDefine.ErCode.ServerReturnError)
            #self.closeTCPSocket()
            os._exit(0)

        if retData[0] == "errorcmd":
            logmsg=logmsg+' exit with errorcmd'
            self.sendHRLog(2,logmsg)
            os._exit(0)

        if retData[1] == "Fail":
            logmsg=logmsg+'exit with Fail['+retData[2]+']'
            self.sendHRLog(2,logmsg)
            errorData = [retData[2]]
            return errorData
            #os._exit(0)
        
        del retData[0]
        if retData[0] == 'OK':
           retData[0] = '0'
        else:
           del retData[0]
        retData.pop()
        #print(retData)
        return retData

    

    

    
