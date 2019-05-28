import hashlib
import random
import numpy as np
from mpyc.runtime import mpc


m = len(mpc.parties)
sec_num = mpc.SecInt()


def vector_sec(v):
    l = len(v)
    x = [None] * l
    for i in range(l):
        x[i] = sec_num(v[i])
    return x


#split secret s into k parts
def split(s, k):
    board_set = set()
    while len(board_set) < k - 1:
        board_set.add(random.randrange(1, s))
    board_list = list(board_set)
    board_list.append(0)
    board_list.append(s)
    board_list.sort()
    return [board_list[i+1] - board_list[i] for i in range(k)]


#hash coefficients
def hash(x):
    sha256 = hashlib.sha256()
    sha256.update(chr(x % 256).encode('utf-8'))
    return sha256.hexdigest()


def vector_hash(v):
    l = len(v)
    x = [None] * l
    for i in range(l):
        x[i] = hash(v[i])
    return x

s = random.randrange(1, 100)
#k = random.randrange(1, min(s+1, 10))
k = 3
z = split(s, k)
c = np.poly(z)
cc = []
for i in c:
    cc.append(int(round(i)))
h = vector_hash(cc)
f = np.poly1d(cc)

with open('board.txt', 'a+') as file:
    file.write(str(mpc.pid)+'\t')
    for i in h:
        file.write(i+'\t')
    file.write('\n')

async def complain():
    await mpc.start()

    x = mpc.input(vector_sec(z), mpc.pid)
    y = await mpc.output(x)
    cheat = False
    for i in y:
        if f(i) != 0:
            cheat = True
            print(str(mpc.pid)+" cheated!")
    if not cheat:
        if sum(z) != s:
            print(str(mpc.pid)+" cheated!")
        else:
            print(str(mpc.pid)+" is innocent!")

    await mpc.shutdown()


mpc.run(complain())
