from mpyc.runtime import mpc
from elgamal import generate_keys, encrypt, decrypt

sec_num = mpc.SecInt()
key = generate_keys(50, 100)
enc = encrypt(key['privateKey'], 1)


async def attack():

    await mpc.start()

    await mpc.output(mpc.input(sec_num(1)))

    await mpc.shutdown()

mpc.run(attack())
print("私钥/公钥", key, encrypt(key['privateKey'], 1))
