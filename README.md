# Secure Auction Game

## Introduction
This is a secure auction protocol demo using secure multiparty compuation and Shamir's secret share.   
This is also the source code part of my graduation thesis of bachelor's degree.  
The design of the protocol draws on the techniques described in paper of Muhammed Faith Balli et.al.  
*Distributed Multi-Unit Privacy Assured Bidding (PAB) for Smart Grid Demand Response Programs.*   
The implementation of the algorithm is based on MPyC Lib source code by Berry Schoenmakers at  
[https://github.com/lschoe/mpyc](https://github.com/lschoe/mpyc)


## Usage
Mutiprocess running. Tested on Unix/Linux OS. Require Python 3.6 or higher.

**python setup.py**  
**python main.py [-M] [-I] [--ssl] n m**  

**-M**   the number of parties involved in the auction  
**-I**   specified the party identifier of the process in the auction  
**--ssl**  if communication via ssl  
**n**   the total number of price a buyer can choose from  
**m**   the total unit of goods


***
@CopyRight Li Jiawei  
All rights reserved.

