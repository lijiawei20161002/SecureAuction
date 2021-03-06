"""A secure auction design using secure multiparty computation.

The scene describes many buyers want to bid for a fixed total amount of goods.
The auctioneer determine the winners by solving a LP using a greedy algorithm according to the total unit of goods.
The buyers bid for the goods in a secret way and learn the result of his own by joint computation of a function with the auctioneer.
The algorithm doesn't disclose any additional information except for the bidder's own result.

The design of the algorithm draws on the techniques described in paper of Muhammed Faith Balli et.al.
Distributed Multi-Unit Privacy Assured Bidding (PAB) for Smart Grid Demand Response Programs
The implementation of the algorithm uses MPyC Lib source code by Berry Schoenmakers at
https://github.com/lschoe/mpyc

@CopyRight Li Jiawei
All rights reserved.
"""

"""Secure auction."""
import random
import sys
from elgamal import generate_keys, encrypt, decrypt
from mpyc.runtime import mpc
from complaint import complain


if not isinstance(int(sys.argv[1]), int) or not isinstance(int(sys.argv[2]), int):
    print('Please enter the price number (int) and the total unit of goods (int) .')
    print('usage: python xx.py -M(parties) -I(pc) (prices) (total_unit)')
    sys.exit()

sec_num = mpc.SecInt()  # using secure multiparty computation and Shamir's secret share
pid = mpc.pid  # indicate the identity of party(process)

MAX_NUM = 100
m = len(mpc.parties)  # number of total parties involved in the auction
n = int(sys.argv[1])  # how many prices can a buyer choose
total_unit = int(sys.argv[2])  # total unit of goods we have
bids = [[None] * (n + 1)] * MAX_NUM  # buyer's bids, random generation
Key = dict()  # elgamal keys

async def main():

    '''offline phase, bid generation'''
    for i in range(m):
        Key[i] = {'privateKey': [None] * 3, 'publicKey': [None] * 3}
    Key[pid] = generate_keys(5, 100)
    privateKey = Key[pid]['privateKey']
    publicKey = Key[pid]['publicKey']
    if pid == 0:
        print('You are the auctioneer.')
        print('The parties involved in the auction are:')
    else:
        unit = random.randint(1, total_unit)
        price = random.randint(1, n)
        bids[pid] = generate_bid(unit, price)  # random generation of bids
        print(f'You are buyer {pid} holding bid {bids[pid]}.')
    for i in range(m):
        print(mpc.parties[i])

    '''online phase, winner determination and result information'''
    await mpc.start()

    s = [0] * (n + 1)  # accumulation of bids
    c = [None] * (n + 1)  # mask vector
    for i in range(1, m):
        x = mpc.input(vector_sec(bids[i]), i)  # encryption of the bid as input of computation
        y = await mpc.output(x, 0)  # send the encrypted bid to auctioneer
        if y != [None] * (n+1):
            s = vector_add(s, y)  # auctioneer can only see the accumulation of all encrypted bids

    if pid == 0:
        win = winner_deter(s)  # computation of the winning price
        print('winning price is: ', win)
        c = generate_mask(win)  # generate mask vector according to the winning price
        print(c)

    for i in range(1, m):
        x = mpc.input(vector_sec(vector_enc(c, publicKey)), 0)  # auctioneer provide mask vector
        ui = matrix_sub(matrix_upper(n+1), matrix_identity(n+1))
        ub = in_prod(ui, bids[i])
        y = mpc.input(vector_sec(vector_enc(ub, publicKey)), i)
        z = await mpc.output(mpc.vector_add(x, y), i)  # joint computation of the function
        z = vector_dec(z, privateKey)
        result = in_prod(matrix_random(n+1), z)

        if result != [None] * (n+1):
            print('secure calculation result: ', result)
            if zero_count(result) == 1:  # winner's result contains one and only one 'zero'
                print('Bidder', pid, 'You are the winner!')
            else:
                print('Bidder', pid, 'Sorry, you are the loser.')  # loser's result are all random ints (non zero)

    await ZK(privateKey[1], privateKey[2], privateKey[0])

    if pid > 0:
        await ZK2(price, find_price(bids[pid]))
    else:
        await ZK2(win, find_win(c))

    await mpc.shutdown()



# buyer's bid, random generation
def generate_bid(u, p):
    b = [0] * (n+1)
    b[p] = u
    return b


# mask generation
def generate_mask(p):
    b = [1] * (n+1)
    b[p] = 0
    return b


def vector_add(x1, x2):
    l = len(x1)
    x = [None] * l
    if len(x2) != l:
        return x
    for i in range(l):
        x[i] = x1[i] + x2[i]
    return x


def vector_sec(v):
    l = len(v)
    x = [None] * l
    for i in range(l):
        x[i] = sec_num(v[i])
    return x


def matrix_identity(k):
    x = [[0] * k for _ in range(k)]
    for i in range(k):
        x[i][i] = 1
    return x


def matrix_upper(k):
    x = [[0] * k for _ in range(k)]
    for i in range(k):
        for j in range(i, k):
            x[i][j] = 1
    return x


def matrix_random(k):
    x = [[0] * k for _ in range(k)]
    for i in range(k):
        x[i][i] = random.randint(1, n)
    return x


def matrix_sub(x1, x2):
    k = len(x1)
    x = [[None] * k for _ in range(k)]
    if len(x2) != k:
        return x
    for i in range(k):
        for j in range(k):
            x[i][j] = x1[i][j] - x2[i][j]
    return x


def in_prod(x1, x2):
    l1, l2, l3 = 1, 1, 1
    if isinstance(x1, list):
        l1 = len(x1)
    if isinstance(x2, list):
        l2 = len(x2)
    if isinstance(x2[0], list):
        l3 = len(x2[0])
    x = [None for _ in range(l1)]
    if x1[0][0] == None or x2[0] == None:
        return x
    if (l2 == 1 and isinstance(x1[0], list)) or (l2 > 1 and l2 != len(x1[0])):
        return x
    for i in range(l1):
        for k in range(l3):
            sum = 0
            for j in range(l2):
                sum += x1[i][j] * x2[j]
            x[i] = sum
    return x


def find_price(x):
    l = len(x)
    for i in range(l):
        if x[i] > 0:
            return i
    return 0


def find_win(x):
    l = len(x)
    for i in range(l):
        if x[i] == 0:
            return i
    return 0


def zero_count(x):
    cnt = 0
    l = len(x)
    for i in range(l):
        if x[i] == 0:
            cnt += 1
    return cnt


# ElGamal Encryption
def vector_enc(v, key):
    l = len(v)
    x = [None] * l * 2
    j = 0
    if not key[0]:
        return x
    if not v[0]:
        return x
    for i in range(l):
        x[j] = encrypt(key, v[i])[0]
        x[j+1] = encrypt(key, v[i])[1]
        j = j+2
    return x


def vector_dec(v, key):
    l = len(v)
    x = [None] * int(l/2)
    i = 0
    if not key[0]:
        return x
    for j in range(int(l/2)):
        if v[i]:
            x[j] = decrypt(key, [v[i], v[i+1]])
            i = i+2
    return x

# computation of the winning price
def winner_deter(s):
    x = total_unit
    for i in range(1, n+1):
        x -= s[i]
        if int(x) < 0:
            return i-1
    return n


'''Zero Knowledge Proof'''
async def ZK(g, x, p):
    y = Key[pid]['publicKey'][2]  # as verifier
    z = random.randint(1, p-1)  # as verifier
    zz = mpc.input(sec_num(z))
    c = random.randint(1, p - 1)  # as verifier
    cc = mpc.input(sec_num(c))
    # as prover
    for i in range(1, m):
        # as prover
        zzz = await mpc.output(zz)
        ccc = await mpc.output(cc)
        r = int(zzz[i]) + x * (int(ccc[i]))
        rr = mpc.input(sec_num(r))
        # as verifier
        rrr = await mpc.output(rr)
        if (pow(g, int(rrr[pid]), p)) != (pow(int(y), int(ccc[i]), p)*pow(g, int(zzz[i]), p) % p):
            print("Found cheater, player ", pid)
            return False
    return True


async def ZK2(x1, x2):
    ya1 = mpc.input(sec_num(x1))
    ya2 = mpc.input(sec_num(x2))
    for i in range(1, m):
        yb1 = await mpc.output(ya1)
        yb2 = await mpc.output(ya2)
        if yb1[i] != yb2[i]:
            print("Found cheater, player ", i)
            return False
    return True

if __name__ == '__main__':
    mpc.run(main())
