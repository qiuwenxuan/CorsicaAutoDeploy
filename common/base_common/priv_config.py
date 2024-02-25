import base64
MY_CREDET_PASS = ''
MY_HOST_CREDET_PASS = ''

def my_encode(inputStr):
    inputBytes = base64.b64encode(inputStr.encode('utf-8'))
    return inputBytes.decode()


def my_decode(inputCret):
    base64_decrypt = base64.b64decode(inputCret.encode('utf-8'))
    return base64_decrypt.decode()


MY_PASSWOR = my_decode(MY_CREDET_PASS)
MY_HOST_PASSWOR = my_decode(MY_HOST_CREDET_PASS)


if __name__ == '__main__':
    enCr = my_encode(MY_HOST_PASSWOR)
    print(enCr)
    deCr = my_decode(enCr)
    print(deCr)
