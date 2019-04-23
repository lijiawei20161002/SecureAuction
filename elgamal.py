'''
Simple ElGamal Encrytion
Thanks to Ryan Riddle's module at https://github.com/RyanRiddle/elgamal
'''
import random


def gcd(a, b):
    while b != 0:
        c = a%b
        a = b
        b = c
    return a


def jacobi(a, n):
    if a == 0:
        if n == 1:
            return 1
        else:
            return 0
    elif a == -1:
        if n % 2 == 0:
            return 1
        else:
            return -1
    elif a == 1:
        return 1
    elif a == 2:
        if n % 8 ==1 or n % 8 == 7:
            return 1
        elif n % 8 ==3 or n % 8 == 5:
            return -1
    elif a >= n:
        return jacobi(a%n, n)
    elif a%2 == 0:
        return jacobi(2, n)*jacobi(a//2, n)
    else:
        if a%4 == 3 and n%4 == 3:
            return -1*jacobi(n, a)
        else:
            return jacobi(n, a)


def SS(num, iConfidence):
    for i in range(iConfidence):
        a = random.randint(1, num-1)
        if gcd(a, num) > 1:
            return False
        if not jacobi(a, num) % num == pow(a, (num-1)//2, num):
            return False
    return True


def find_prime(iNumBits, iConfidence):
    while 1:
        p = random.randint(2**(iNumBits-2), 2**(iNumBits-1))
        while p%2 == 0:
            p = random.randint(2**(iNumBits-2), 2**(iNumBits-1))
            while p% 2 ==0:
                p = random.randint(2**(iNumBits-2), 2**(iNumBits-1))
            while not SS(p, iConfidence):
                p = random.randint( 2**(iNumBits-2), 2**(iNumBits-1))
                while p%2 == 0:
                    p = random.randint(2**(iNumBits-2), 2**(iNumBits-1))
            p = p*2 + 1
            if SS(p, iConfidence):
                return p


def find_primitive_root(p):
    if p == 2:
        return 1
    p1 = 2
    p2 = (p-1)//p1
    while 1:
        g = random.randint(2, p-1)
        if not (pow(g, (p-1)//p1, p)==1):
            if not (pow(g, (p-1)//p2, p)==1):
                return g

def generate_keys(iNumBits=256, iConfidence=32):
    p = find_prime(iNumBits, iConfidence)
    g = find_primitive_root(p)
    g = pow(g, 2, p)
    x = random.randint(1, (p-1)//2)
    h = pow(g, x, p)
    publicKey = (p, g, h)
    privateKey = (p, g, x)
    return {'privateKey': privateKey, 'publicKey': publicKey}

