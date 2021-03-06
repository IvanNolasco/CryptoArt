import base64
import os

from io import BytesIO
from datetime import datetime

from app.models import PaintingRequest
from app.obfuscated import decrypt_key, encrypt_key

import random
from datetime import timedelta

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA384
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from django.shortcuts import render, render_to_response
from django.conf import settings
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.http import HttpRequest
from django.contrib import messages
from django.views.generic import View
from django.template import RequestContext

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils.datastructures import MultiValueDictKeyError


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath("views.py")))


"""==============================="""
"""         Systems Views         """
"""==============================="""

class HomeView(View):
    template_name = 'app/home.html'
    context_name = 'Home Page'

    def get(self, request, format=None):
        """Renders the home page"""
        assert isinstance(request, HttpRequest)
        return render(
            request,
            self.template_name,
            {
                'title':self.context_name,
                })

"""==============================="""
"""       Crypto Functions        """
"""==============================="""

def signing_process(user_id, order_id):
    """sign the order_confirmation"""
    order_file = open(BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_OrderConfirmation.txt', 'r')
    order = order_file.read().encode()  #encode cast string to bytes
    private_key = RSA.import_key(open(BASE_DIR+'\\CryptoProject\\keys\\users\\'+str(user_id)+'_private.pem').read())
    h = SHA384.new(order)
    signature = pkcs1_15.new(private_key).sign(h)
    writeBinFile(signature, BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_signature.bin')

def writeBinFile(file_bytes, file_name):
    """write a binary file in base64"""
    file = open(file_name, 'wb')
    file.write(base64.b64encode(file_bytes)) 
    file.close()
    
def readBinFile(file_name):
    """read a binary file in base64"""
    file = open(file_name, 'rb')
    file_bytes = file.read()
    file.close()
    return base64.b64decode(file_bytes)

def get_image_bytes(image_file_name):
    """get the bytes of an image file in base64"""
    image_file = open(image_file_name,'rb')
    image_bytes = image_file.read()
    return image_bytes

def generate_key(id):
    """generate a random key of 128 bits and store it in a file in base64"""
    key = get_random_bytes(16)
    o_key = encrypt_key(key)
    writeBinFile(o_key, BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_key.bin')
    
def generate_iv(id):
    """generate a random iv of 128 bits and store it in a file in base64"""
    iv = get_random_bytes(16)
    writeBinFile(iv, BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_iv.bin')

def generate_RSA_keys(id):
    """generate a RSA key pair and stored in .pem files"""
    key = RSA.generate(1024)
    private_key = key.export_key()
    prikey_file = open(BASE_DIR + '\\CryptoProject\\keys\\users\\' + id + '_private.pem', 'wb')
    prikey_file.write(private_key)
    public_key = key.publickey().export_key()
    pubkey_file = open(BASE_DIR+'\\CryptoProject\\keys\\users\\'+id+'_public.pem', 'wb')
    pubkey_file.write(public_key)

def verifying_process(user_id, order_id):
    """verifying"""
    public_key = RSA.import_key(open(BASE_DIR+'\\CryptoProject\\keys\\users\\'+str(user_id)+'_public.pem').read())
    order_file = open(BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_OrderConfirmation.txt', 'r')
    order = order_file.read().encode() #encode cast string to bytes
    signature = readBinFile(BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_signature.bin')
    h = SHA384.new(order)
    try:
        pkcs1_15.new(public_key).verify(h, signature)
        return True
    except (ValueError, TypeError):
        return False

def encrypt_image(id, image_file_name, directory):
    """encrypt and store the client photo"""
    image_bytes = get_image_bytes(image_file_name)
    o_key = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_key.bin')
    key = decrypt_key(o_key)
    iv = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_iv.bin')
    
    #build an AES cipher using OFB mode
    cipher = AES.new(key, AES.MODE_OFB, iv)
    #encrypt the images bytes
    cipher_image_bytes = cipher.encrypt(image_bytes)
    writeBinFile(cipher_image_bytes, BASE_DIR + '\\CryptoProject\\app\\static\\images\\'+directory+'\\' + str(id) + '.bin')

def decrypt_image(id, extension, directory):
    """read and decrypt the client photo"""
    cipher_image = readBinFile(BASE_DIR + '\\CryptoProject\\app\\static\\images\\'+directory+'\\' + str(id) + '.bin')
    o_key = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_key.bin')
    key = decrypt_key(o_key)
    iv = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_iv.bin')
    
    #build an AES cipher using OFB mode
    cipher = AES.new(key, AES.MODE_OFB, iv)
    #decrypt the cipher images bytes
    plain_image_bytes = cipher.decrypt(cipher_image)
    return plain_image_bytes

def error_404_view(request,exception):
    data = {"name": "ThePythonDjango.com"}
    return render(request,'app/404.html', data)

def error_500_view(request):
    context = RequestContext(request)
    response = render_to_response('app/500.html', context)
    response.status_code = 500
    return response

def error_400_view(request, exception):
    data = {"name": "ThePythonDjango.com"}
    return render(request,'app/400.html', data)

def error_403_view(request,exception):
    data = {"name": "ThePythonDjango.com"}
    return render(request,'app/403.html', data)



